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


from ..database import Database
from ..loader import Modules
from ..tl_cache import CustomTelegramClient
from . import proxypass, root
from .. import main, utils, version


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
                    f"<i>{utils.get_lang_flag(res['country_code'])} {res['country_name']}"
                    f" {res['region_name']} {res['city']} {res['zip_code']}</i>"
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
