"""Responsible for web init and mandatory ops"""

#    Friendly Telegram (telegram userbot)
#    Copyright (C) 2018-2021 The Authors

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.

#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

# ©️ Dan Gazizullin, 2021-2023
# This file is a part of Hikka Userbot
# 🌐 https://github.com/hikariatama/Hikka
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

import asyncio
import contextlib
import inspect
import logging
import os
import re
import string
import time

import aiohttp_jinja2
import jinja2
import requests
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiohttp import web
from herokutl.errors import (
    FloodWaitError,
    PasswordHashInvalidError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
    YouBlockedUserError,
)
from herokutl.password import compute_check
from herokutl.sessions import MemorySession
from herokutl.tl.functions.account import GetPasswordRequest
from herokutl.tl.functions.auth import CheckPasswordRequest
from herokutl.tl.functions.contacts import UnblockRequest
from herokutl.utils import parse_phone

from .. import database, main, utils
from .._internal import restart
from ..tl_cache import CustomTelegramClient
from ..version import __version__

try:
    from . import root
except ImportError:
    from . import web as root

DATA_DIR = (
    "/data"
    if "DOCKER" in os.environ
    else os.path.normpath(os.path.join(utils.get_base_dir(), ".."))
)

logger = logging.getLogger(__name__)


class Web(root.Web):
    def __init__(self, **kwargs):
        self.sign_in_clients = {}
        self._pending_client = None
        self._qr_login = None
        self._qr_task = None
        self._2fa_needed = None
        self._sessions = []
        self._ratelimit = {}
        self.api_token = kwargs.pop("api_token")
        self.data_root = kwargs.pop("data_root")
        self.connection = kwargs.pop("connection")
        self.proxy = kwargs.pop("proxy")

        self.app.router.add_get("/", self.root)
        self.app.router.add_put("/set_api", self.set_tg_api)
        self.app.router.add_post("/send_tg_code", self.send_tg_code)
        self.app.router.add_post("/check_session", self.check_session)
        self.app.router.add_post("/web_auth", self.web_auth)
        self.app.router.add_post("/tg_code", self.tg_code)
        self.app.router.add_post("/finish_login", self.finish_login)
        self.app.router.add_post("/custom_bot", self.custom_bot)
        self.app.router.add_post("/init_qr_login", self.init_qr_login)
        self.app.router.add_post("/get_qr_url", self.get_qr_url)
        self.app.router.add_post("/qr_2fa", self.qr_2fa)
        self.app.router.add_post("/can_add", self.can_add)
        self.api_set = asyncio.Event()
        self.clients_set = asyncio.Event()

    @property
    def _platform_emoji(self) -> str:
        return {
            "vds": "https://github.com/hikariatama/assets/raw/master/waning-crescent-moon_1f318.png",
            "lavhost": "https://github.com/hikariatama/assets/raw/master/victory-hand_270c-fe0f.png",
            "termux": "https://github.com/hikariatama/assets/raw/master/smiling-face-with-sunglasses_1f60e.png",
            "docker": "https://github.com/hikariatama/assets/raw/master/spouting-whale_1f433.png",
        }[(
            "lavhost"
            if "LAVHOST" in os.environ
            else (
                "termux"
                if "com.termux" in os.environ.get("PREFIX", "")
                else "docker" if "DOCKER" in os.environ else "vds"
            )
        )]

    @aiohttp_jinja2.template("root.jinja2")
    async def root(self, _):
        return {
            "skip_creds": self.api_token is not None,
            "tg_done": bool(self.client_data),
            "lavhost": "LAVHOST" in os.environ,
            "platform_emoji": self._platform_emoji,
        }

    async def check_session(self, request: web.Request) -> web.Response:
        return web.Response(body=("1" if self._check_session(request) else "0"))

    def wait_for_api_token_setup(self):
        return self.api_set.wait()

    def wait_for_clients_setup(self):
        return self.clients_set.wait()

    def _check_session(self, request: web.Request) -> bool:
        if not main.heroku.clients:
            return True
        
        return request.cookies.get("session", None) in self._sessions

    async def _check_bot(
        self,
        client: CustomTelegramClient,
        username: str,
    ) -> bool:
        async with client.conversation("@BotFather", exclusive=False) as conv:
            try:
                m = await conv.send_message("/token")
            except YouBlockedUserError:
                await client(UnblockRequest(id="@BotFather"))
                m = await conv.send_message("/token")

            r = await conv.get_response()

            await m.delete()
            await r.delete()

            if not hasattr(r, "reply_markup") or not hasattr(r.reply_markup, "rows"):
                return False

            for row in r.reply_markup.rows:
                for button in row.buttons:
                    if username != button.text.strip("@"):
                        continue

                    m = await conv.send_message("/cancel")
                    r = await conv.get_response()

                    await m.delete()
                    await r.delete()

                    return True

    async def custom_bot(self, request: web.Request) -> web.Response:
        if not self._check_session(request):
            return web.Response(status=401)

        text = await request.text()
        client = self._pending_client
        db = database.Database(client)
        await db.init()

        text = text.strip("@")

        if any(
            litera not in (string.ascii_letters + string.digits + "_")
            for litera in text
        ) or not text.lower().endswith("bot"):
            return web.Response(body="OCCUPIED")

        try:
            await client.get_entity(f"@{text}")
        except ValueError:
            pass
        else:
            if not await self._check_bot(client, text):
                return web.Response(body="OCCUPIED")

        db.set("heroku.inline", "custom_bot", text)
        return web.Response(body="OK")

    async def set_tg_api(self, request: web.Request) -> web.Response:
        if not self._check_session(request):
            return web.Response(status=401, body="Authorization required")

        text = await request.text()

        if len(text) < 36:
            return web.Response(
                status=400,
                body="API ID and HASH pair has invalid length",
            )

        api_id = text[32:]
        api_hash = text[:32]

        if any(c not in string.hexdigits for c in api_hash) or any(
            c not in string.digits for c in api_id
        ):
            return web.Response(
                status=400,
                body="You specified invalid API ID and/or API HASH",
            )

        main.save_config_key("api_id", int(api_id))
        main.save_config_key("api_hash", api_hash)

        self.api_token = collections.namedtuple("api_token", ("ID", "HASH"))(
            api_id,
            api_hash,
        )

        self.api_set.set()
        return web.Response(body="ok")

    async def _qr_login_poll(self):
        logged_in = False
        self._2fa_needed = False
        logger.debug("Waiting for QR login to complete")
        while not logged_in:
            try:
                logged_in = await self._qr_login.wait(10)
            except asyncio.TimeoutError:
                logger.debug("Recreating QR login")
                try:
                    await self._qr_login.recreate()
                except SessionPasswordNeededError:
                    self._2fa_needed = True
                    return
            except SessionPasswordNeededError:
                self._2fa_needed = True
                break

        logger.debug("QR login completed. 2FA needed: %s", self._2fa_needed)
        self._qr_login = True

    async def init_qr_login(self, request: web.Request) -> web.Response:
        if self.client_data and "LAVHOST" in os.environ:
            return web.Response(status=403, body="Forbidden by LavHost EULA")

        if not self._check_session(request):
            return web.Response(status=401)

        if self._pending_client is not None:
            self._pending_client = None
            self._qr_login = None
            if self._qr_task:
                self._qr_task.cancel()
                self._qr_task = None

            self._2fa_needed = False
            logger.debug("QR login cancelled, new session created")

        client = self._get_client()
        self._pending_client = client

        await client.connect()
        self._qr_login = await client.qr_login()
        self._qr_task = asyncio.ensure_future(self._qr_login_poll())

        return web.Response(body=self._qr_login.url)

    async def get_qr_url(self, request: web.Request) -> web.Response:
        if not self._check_session(request):
            return web.Response(status=401)

        if self._qr_login is True:
            if self._2fa_needed:
                return web.Response(status=403, body="2FA")
            
            if self._pending_client:
                await main.heroku.save_client_session(self._pending_client, delay_restart=True)
                self._pending_client.is_web = True
            
            return web.Response(status=200, body="SUCCESS")

        if self._qr_login is None:
            await self.init_qr_login(request)

        if self._qr_login is None:
            return web.Response(
                status=500,
                body="Internal Server Error: Unable to initialize QR login",
            )

        return web.Response(status=201, body=self._qr_login.url)

    def _get_client(self) -> CustomTelegramClient:
        return CustomTelegramClient(
            MemorySession(),
            self.api_token.ID,
            self.api_token.HASH,
            connection=self.connection,
            proxy=self.proxy,
            connection_retries=None,
            device_model=main.get_app_name(),
            system_version="Windows 10",
            app_version=".".join(map(str, __version__)) + " x64",
            lang_code="en",
            system_lang_code="en-US",
        )

    async def can_add(self, request: web.Request) -> web.Response:
        if self.client_data and "LAVHOST" in os.environ:
            return web.Response(status=403, body="Forbidden by host EULA")

        return web.Response(status=200, body="Yes")

    async def send_tg_code(self, request: web.Request) -> web.Response:
        if not self._check_session(request):
            return web.Response(status=401, body="Authorization required")

        if self.client_data and "LAVHOST" in os.environ:
            return web.Response(status=403, body="Forbidden by host EULA")

        if self._pending_client:
            if getattr(self._pending_client, "is_web", False):
                logger.warning("Code request attempted, but user is already logged in. Prompting to finish.")
                return web.Response(status=208, body="ALREADY_LOGGED_IN")
            
            logger.warning("Cancelling previous pending login session.")
            try:
                await self._pending_client.disconnect()
            except Exception:
                pass
            self._pending_client = None


        text = await request.text()
        phone = parse_phone(text)

        if not phone:
            return web.Response(status=400, body="Invalid phone number")

        client = self._get_client()
        self._pending_client = client

        # <<< ИЗМЕНЕНИЕ ЗДЕСЬ >>>
        # Вручную устанавливаем адрес дата-центра перед подключением
        await client.session.set_dc(4, "149.154.167.51", 443)
        # <<< КОНЕЦ ИЗМЕНЕНИЯ >>>

        await client.connect()
        try:
            await client.send_code_request(phone)
        except FloodWaitError as e:
            self._pending_client = None
            return web.Response(status=429, body=self._render_fw_error(e))
        except Exception as e:
            logger.error("Failed to send code request: %s", e)
            self._pending_client = None
            return web.Response(status=500, body=f"Error: {e}")

        return web.Response(body="ok")

    @staticmethod
    def _render_fw_error(e: FloodWaitError) -> str:
        seconds, minutes, hours = (
            e.seconds % 3600 % 60,
            e.seconds % 3600 // 60,
            e.seconds // 3600,
        )
        seconds, minutes, hours = (
            f"{seconds} second(-s)",
            f"{minutes} minute(-s) " if minutes else "",
            f"{hours} hour(-s) " if hours else "",
        )
        return (
            f"You got FloodWait for {hours}{minutes}{seconds}. Wait the specified"
            " amount of time and try again."
        )

    async def qr_2fa(self, request: web.Request) -> web.Response:
        if not self._check_session(request):
            return web.Response(status=401)

        text = await request.text()
        logger.debug("2FA code received for QR login: %s", text)

        try:
            await self._pending_client._on_login(
                (
                    await self._pending_client(
                        CheckPasswordRequest(
                            compute_check(
                                await self._pending_client(GetPasswordRequest()),
                                text.strip(),
                            )
                        )
                    )
                ).user
            )
        except PasswordHashInvalidError:
            logger.debug("Invalid 2FA code")
            return web.Response(status=403, body="Invalid 2FA password")
        except FloodWaitError as e:
            logger.debug("FloodWait for 2FA code")
            return web.Response(status=421, body=self._render_fw_error(e))

        logger.debug("2FA code accepted, logging in")
        await main.heroku.save_client_session(self._pending_client, delay_restart=True)
        self._pending_client.is_web = True
        return web.Response(status=200, body="SUCCESS")

    async def tg_code(self, request: web.Request) -> web.Response:
        if not self._check_session(request):
            return web.Response(status=401)

        if not self._pending_client:
            logger.error("tg_code called but no pending client session.")
            return web.Response(status=400, body="No pending session. Please enter phone number again.")

        text = await request.text()
        if len(text) < 6:
            return web.Response(status=400)

        split = text.split("\n", 2)
        if len(split) < 2:
            return web.Response(status=400)

        code = split[0]
        phone = parse_phone(split[1])
        password = split[2] if len(split) > 2 else None

        if not code or any(c not in string.digits for c in code) or not phone:
            return web.Response(status=400)

        try:
            if not password:
                await self._pending_client.sign_in(phone, code=code)
            else:
                await self._pending_client.sign_in(phone, password=password)
        except SessionPasswordNeededError:
            return web.Response(status=401, body="2FA Password required")
        except (PhoneCodeExpiredError, PhoneCodeInvalidError):
            return web.Response(status=403, body="Invalid code")
        except PasswordHashInvalidError:
            return web.Response(status=403, body="Invalid 2FA password")
        except FloodWaitError as e:
            return web.Response(status=421, body=self._render_fw_error(e))

        await main.heroku.save_client_session(self._pending_client, delay_restart=True)
        self._pending_client.is_web = True
        return web.Response(status=200, body="SUCCESS")

    async def finish_login(self, request: web.Request) -> web.Response:
        if not self._check_session(request):
            return web.Response(status=401)
        
        if not self._pending_client or not getattr(self._pending_client, "is_web", False):
            return web.Response(status=200)

        first_session = not bool(main.heroku.clients)
        
        main.heroku.clients.append(self._pending_client)
        self._pending_client = None
        self.clients_set.set()
        
        if not first_session:
            await asyncio.sleep(1)
            restart()

        return web.Response()

    async def web_auth(self, request: web.Request) -> web.Response:
        if self._check_session(request):
            return web.Response(body=request.cookies.get("session", "unauthorized"))

        session = f"heroku_{utils.rand(16)}"

        if not main.heroku.clients:
            logger.info("First login attempt. Granting session without confirmation.")
            self._sessions.append(session)
            return web.Response(body=session)

        logger.info("Secondary login attempt. Requesting confirmation from owner.")
        token = utils.rand(8)

        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔓 Authorize Web Login",
                        callback_data=f"authorize_web_{token}",
                    )
                ]
            ]
        )

        ips = request.headers.get("X-FORWARDED-FOR", None) or request.remote
        cities = []

        for ip in re.findall(r"[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}", ips):
            if ip not in self._ratelimit:
                self._ratelimit[ip] = []

            if len(list(filter(lambda x: time.time() - x < 3 * 60, self._ratelimit[ip]))) >= 3:
                return web.Response(status=429)

            self._ratelimit[ip] = list(filter(lambda x: time.time() - x < 3 * 60, self._ratelimit[ip]))
            self._ratelimit[ip] += [time.time()]

            try:
                res = (await utils.run_sync(requests.get, f"https://freegeoip.app/json/{ip}")).json()
                cities += [f"<i>{utils.get_lang_flag(res['country_code'])} {res['country_name']} {res['region_name']} {res['city']} {res['zip_code']}</i>"]
            except Exception:
                pass

        cities_text = ("<b>🏢 Possible cities:</b>\n\n" + "\n".join(cities) + "\n") if cities else ""

        ops = []
        for user in self.client_data.values():
            try:
                bot = user[0].inline.bot
                msg = await bot.send_message(
                    chat_id=user[1].tg_id,
                    text=(
                        "🪐🔐 <b>Click button below to confirm web application"
                        f" ops</b>\n\n<b>Client IP</b>: {ips}\n{cities_text}\n<i>If you did"
                        " not request any codes, simply ignore this message</i>"
                    ),
                    disable_web_page_preview=True,
                    reply_markup=markup,
                )
                ops.append(functools.partial(bot.delete_message, chat_id=msg.chat.id, message_id=msg.message_id))
            except Exception:
                pass

        if not ops:
            return web.Response(body="CONFIRMATION_FAILED")

        if not await main.heroku.wait_for_web_auth(token):
            for op in ops:
                await op()
            return web.Response(body="TIMEOUT")

        for op in ops:
            await op()

        self._sessions.append(session)

        return web.Response(body=session)
