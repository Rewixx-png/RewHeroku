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
import subprocess
import collections
import string
import re
import time

import aiohttp_jinja2
import jinja2
from aiohttp import web
# <<< ИСПРАВЛЕНИЕ: ДОБАВЛЕН ЭТОТ ИМПОРТ >>>
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
# <<< КОНЕЦ ИСПРАВЛЕНИЯ >>>
from herokutl.errors import (
    FloodWaitError,
    PasswordHashInvalidError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
    YouBlockedUserError,
)
from herokutl.password import compute_check
from herokutl.sessions import MemorySession, SQLiteSession
from herokutl.tl.functions.account import GetPasswordRequest
from herokutl.tl.functions.auth import CheckPasswordRequest
from herokutl.tl.functions.contacts import UnblockRequest
from herokutl.utils import parse_phone

from ..database import Database
from ..loader import Modules
from ..tl_cache import CustomTelegramClient
from . import proxypass, root
from .. import main, utils, version
from .._internal import restart
from ..version import __version__

DATA_DIR = (
    "/data"
    if "DOCKER" in os.environ
    else os.path.normpath(os.path.join(utils.get_base_dir(), ".."))
)

logger = logging.getLogger(__name__)


class Web(root.Web):
    def __init__(self, **kwargs):
        self.runner = None
        self.port = None
        self.running = asyncio.Event()
        self.ready = asyncio.Event()
        self.client_data = {}
        self.app = web.Application()
        self.proxypasser = None
        aiohttp_jinja2.setup(
            self.app,
            filters={"getdoc": inspect.getdoc, "ascii": ascii},
            loader=jinja2.FileSystemLoader("web-resources"),
        )
        self.app["static_root_url"] = "/static"

        super().__init__(**kwargs)
        self.app.router.add_get("/favicon.ico", self.favicon)
        self.app.router.add_static("/static/", "web-resources/static")

    async def start_if_ready(
        self,
        total_count: int,
        port: int,
        proxy_pass: bool = False,
    ):
        if total_count <= len(self.client_data):
            if not self.running.is_set():
                await self.start(port, proxy_pass=proxy_pass)

            self.ready.set()

    async def get_url(self, proxy_pass: bool) -> str:
        url = None

        if all(option in os.environ for option in {"LAVHOST", "USER", "SERVER"}):
            return f"https://{os.environ['USER']}.{os.environ['SERVER']}.lavhost.ml"

        if proxy_pass:
            with contextlib.suppress(Exception):
                url = await self.proxypasser.get_url(timeout=10)

        if not url:
            ip = (
                "127.0.0.1"
                if "DOCKER" not in os.environ
                else subprocess.run(
                    ["hostname", "-i"],
                    stdout=subprocess.PIPE,
                    check=True,
                )
                .stdout.decode("utf-8")
                .strip()
            )

            url = f"http://{ip}:{self.port}"

        self.url = url
        return url

    async def start(self, port: int, proxy_pass: bool = False):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.port = os.environ.get("PORT", port)
        site = web.TCPSite(self.runner, None, self.port)
        self.proxypasser = proxypass.ProxyPasser(port=self.port)
        await site.start()

        await self.get_url(proxy_pass)

        self.running.set()
        print(f"Heroku Userbot Web Interface running on {self.port}")

    async def stop(self):
        await self.runner.shutdown()
        await self.runner.cleanup()
        self.running.clear()
        self.ready.clear()

    async def add_loader(
        self,
        client: CustomTelegramClient,
        loader: Modules,
        db: Database,
    ):
        self.client_data[client.tg_id] = (loader, client, db)

    @staticmethod
    async def favicon(_):
        return web.Response(
            status=301,
            headers={"Location": "https://i.imgur.com/IRAiWBo.jpeg"},
        )

    async def set_tg_api(self, request: web.Request) -> web.Response:
        if not self._check_session(request):
            return web.Response(status=401, body="Authorization required")

        text = await request.text()

        if not text:
            api_id = "20045757"
            api_hash = "7d3ea0c0d4725498789bd51a9ee02421"
        else:
            if len(text) < 36:
                return web.Response(
                    status=400,
                    body="API ID and HASH pair has invalid length",
                )

            api_hash = text[:32]
            api_id = text[32:]

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

    async def check_session(self, request: web.Request) -> web.Response:
        return web.Response(body=("1" if self._check_session(request) else "0"))

    def wait_for_api_token_setup(self):
        return self.api_set.wait()

    def wait_for_clients_setup(self):
        return self.clients_set.wait()

    def _check_session(self, request: web.Request) -> bool:
        return (
            request.cookies.get("session", None) in self._sessions
            if main.heroku.clients
            else True
        )

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
            
            # <<< ИЗМЕНЕНИЕ: Не вызываем save_client_session напрямую >>>
            return web.Response(status=200, body="SUCCESS_NO_2FA")

        if self._qr_login is None:
            await self.init_qr_login(request)

        if self._qr_login is None:
            return web.Response(
                status=500,
                body="Internal Server Error: Unable to initialize QR login",
            )

        return web.Response(status=201, body=self._qr_login.url)

    def _get_client(self) -> CustomTelegramClient:
        client = CustomTelegramClient(
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
        client.is_web = True
        return client

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
            return web.Response(status=208, body="Already pending")

        text = await request.text()
        phone = parse_phone(text)

        if not phone:
            return web.Response(status=400, body="Invalid phone number")

        client = self._get_client()
        self._pending_client = client

        await self._pending_client.connect()
        try:
            await self._pending_client.send_code_request(phone)
        except FloodWaitError as e:
            return web.Response(status=429, body=self._render_fw_error(e))

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

    # <<< НАЧАЛО ИЗМЕНЕНИЙ: Новая изолированная функция сохранения >>>
    async def _save_new_session(self, client: CustomTelegramClient):
        """Saves a new session without interfering with the main client"""
        try:
            me = await client.get_me()
            if not me:
                raise ValueError("Could not get user info from new session")

            session_filename = f"heroku-{me.id}.session"
            destination_path = os.path.join(main.BASE_DIR, session_filename)
            
            if os.path.exists(destination_path):
                logging.warning(f"Session file {destination_path} already exists. Overwriting.")

            sqlite_session = SQLiteSession(destination_path)
            sqlite_session.set_dc(
                client.session.dc_id,
                client.session.server_address,
                client.session.port,
            )
            sqlite_session.auth_key = client.session.auth_key
            sqlite_session.save()
            sqlite_session._conn.close()
            logging.info(f"Successfully saved new session to {destination_path}")
        except Exception:
            logging.exception("Failed to save new session file")
            raise

    async def qr_2fa(self, request: web.Request) -> web.Response:
        if not self._check_session(request):
            return web.Response(status=401)

        text = await request.text()
        logger.debug("2FA code received for QR login: %s", text)

        try:
            await self._pending_client.connect()
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
        except Exception as e:
            logging.error("2FA failed", exc_info=True)
            body = "Invalid 2FA password" if isinstance(e, PasswordHashInvalidError) else self._render_fw_error(e) if isinstance(e, FloodWaitError) else str(e)
            return web.Response(status=403, body=body)

        logger.debug("2FA code accepted, logging in")
        await self._save_new_session(self._pending_client)
        return web.Response(status=200, body="SUCCESS")

    async def tg_code(self, request: web.Request) -> web.Response:
        if not self._check_session(request):
            return web.Response(status=401)

        text = await request.text()
        if len(text) < 6: return web.Response(status=400)
        
        split = text.split("\n", 2)
        if len(split) not in (2, 3): return web.Response(status=400)

        code, phone = split[0], parse_phone(split[1])
        password = split[2] if len(split) > 2 else None

        if (len(code) != 5 and not password) or any(c not in string.digits for c in code) or not phone:
            return web.Response(status=400)

        await self._pending_client.connect()

        try:
            if not password:
                await self._pending_client.sign_in(phone, code=code)
            else:
                await self._pending_client.sign_in(phone, password=password)
        except SessionPasswordNeededError:
            return web.Response(status=401, body="2FA Password required")
        except (PhoneCodeExpiredError, PhoneCodeInvalidError, PasswordHashInvalidError) as e:
            body = "Code expired" if isinstance(e, PhoneCodeExpiredError) else "Invalid code" if isinstance(e, PhoneCodeInvalidError) else "Invalid 2FA password"
            return web.Response(status=403, body=body)
        except FloodWaitError as e:
            return web.Response(status=421, body=self._render_fw_error(e))
        except Exception as e:
            logging.error("Sign in failed", exc_info=True)
            return web.Response(status=500, body=str(e))

        await self._save_new_session(self._pending_client)
        return web.Response(status=200, body="SUCCESS")
    # <<< КОНЕЦ ИЗМЕНЕНИЙ >>>


    async def finish_login(self, request: web.Request) -> web.Response:
        if not self._check_session(request):
            return web.Response(status=401)

        if not self._pending_client:
            # This can happen if the user reloads the page after a successful login
            # before the restart completes. It's safe to just restart.
            if not main.heroku.clients: # Only restart if it's the very first login
                logging.info("Restarting after page reload...")
                restart()
            return web.Response(body="OK, already processing")

        first_session = not bool(main.heroku.clients)

        main.heroku.clients = list(set(main.heroku.clients + [self._pending_client]))
        self._pending_client = None

        self.clients_set.set()
        
        if not first_session:
            logging.info("New account added, restarting...")
            await asyncio.sleep(1)
            restart()

        return web.Response()

    async def web_auth(self, request: web.Request) -> web.Response:
        if self._check_session(request):
            return web.Response(body=request.cookies.get("session", "unauthorized"))

        token = utils.rand(8)

        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔓 Authorize user",
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

            if (
                len(
                    list(
                        filter(lambda x: time.time() - x < 3 * 60, self._ratelimit[ip])
                    )
                )
                >= 3
            ):
                return web.Response(status=429)

            self._ratelimit[ip] = list(
                filter(lambda x: time.time() - x < 3 * 60, self._ratelimit[ip])
            )

            self._ratelimit[ip] += [time.time()]
            try:
                res = (
                    await utils.run_sync(
                        requests.get,
                        f"https://freegeoip.app/json/{ip}",
                    )
                ).json()
                cities += [
                    f"<i>{utils.get_lang_flag(res['country_code'])} {res['country_name']} {res['region_name']} {res['city']} {res['zip_code']}</i>"
                ]
            except Exception:
                pass

        cities = (
            ("<b>🏢 Possible cities:</b>\n\n" + "\n".join(cities) + "\n")
            if cities
            else ""
        )

        ops = []

        for user in self.client_data.values():
            try:
                bot = user[0].inline.bot
                msg = await bot.send_message(
                    chat_id=user[1].tg_id,
                    text=(
                        "🪐🔐 <b>Click button below to confirm web application"
                        f" ops</b>\n\n<b>Client IP</b>: {ips}\n{cities}\n<i>If you did"
                        " not request any codes, simply ignore this message</i>"
                    ),
                    disable_web_page_preview=True,
                    reply_markup=markup,
                )
                ops += [
                    functools.partial(
                        bot.delete_message,
                        chat_id=msg.chat.id,
                        message_id=msg.message_id,
                    )
                ]
            except Exception:
                pass

        session = f"heroku_{utils.rand(16)}"

        if not ops:
            return web.Response(body=session)

        if not await main.heroku.wait_for_web_auth(token):
            for op in ops:
                await op()
            return web.Response(body="TIMEOUT")

        for op in ops:
            await op()

        self._sessions += [session]

        return web.Response(body=session)
