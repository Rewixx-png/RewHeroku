"""Loads and registers modules"""

# ©️ Dan Gazizullin, 2021-2023
# This file is a part of Hikka Userbot
# 🌐 https://github.com/hikariatama/Hikka
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

# ©️ Codrago, 2024-2025
# This file is a part of Heroku Userbot
# 🌐 https://github.com/coddrago/Heroku
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

import asyncio
import contextlib
import importlib
import importlib.machinery
import importlib.util
import inspect
import logging
import os
import re
import sys
import typing
from pathlib import Path

import requests
from herokutl.tl.types import Message

from .. import loader, main, utils
from ..inline.types import InlineCall
from ..types import (
    LoadError,
    SelfSuspend,
    SelfUnload,
)

logger = logging.getLogger(__name__)


@loader.tds
class LoaderMod(loader.Module):
    """Loads modules"""

    strings = {"name": "Loader"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "repo_url",
                "https://mods.codrago.life/",
                lambda: self.strings("repo_config_doc"),
                validator=loader.validators.Link(),
            ),
            loader.ConfigValue(
                "additional_repos",
                [],
                lambda: self.strings("add_repo_config_doc"),
                validator=loader.validators.Series(
                    validator=loader.validators.Link(),
                ),
            ),
            loader.ConfigValue(
                "share_link",
                True,
                lambda: self.strings("share_link_doc"),
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "basic_auth",
                {},
                lambda: self.strings("basic_auth_doc"),
                validator=loader.validators.Hidden(loader.validators.Series()),
            ),
        )
        logger.info("LoaderMod has been initialized.") # Добавлено логгирование

    async def client_ready(self):
        logger.info("LoaderMod client_ready hook started.") # Добавлено логгирование
        self.allmodules.add_aliases(self.get("aliases", {}))
        # asyncio.ensure_future(self._update_repos()) # ПРОБЛЕМНАЯ СТРОКА ОТКЛЮЧЕНА
        logger.info("LoaderMod client_ready hook finished successfully.") # Добавлено логгирование

    async def find_module(self, args: str) -> typing.Tuple[str, str, str]:
        for repo in [self.config["repo_url"]] + self.config["additional_repos"]:
            try:
                if not repo.endswith("/"):
                    repo += "/"

                async with self.client.session.get(f"{repo}modules.json") as resp:
                    modules = await resp.json()

                for mod, url in modules.items():
                    if mod.lower() == args.lower():
                        return mod, url, repo
            except Exception:
                logger.debug("Can't fetch repo %s", repo, exc_info=True)
                continue

        return None, None, None

    async def _confirm_fs(
        self,
        message: Message,
        code: str,
        name: str,
        _is_update: bool = False,
    ) -> bool:
        permanent = self._db.get(main.__name__, "permanent_modules_fs", False)
        disable = self._db.get(main.__name__, "disable_modules_fs", False)

        if permanent or not self.inline.init_complete or disable:
            return permanent

        try:
            msg = await self.inline.form(
                self.strings("module_fs"),
                message=message,
                reply_markup=[
                    {"text": self.strings("save"), "data": "save"},
                    {"text": self.strings("no_save"), "data": "no_save"},
                    {"text": self.strings("save_for_all"), "data": "save_for_all"},
                    {"text": self.strings("never_save"), "data": "never_save"},
                ],
                photo="https://img.icons8.com/fluency/512/hdd.png",
                silent=True,
            )
        except Exception:
            return False

        save = await msg.wait_for_click(20)

        if save:
            data = save.data
            if data == "save_for_all":
                self._db.set(main.__name__, "permanent_modules_fs", True)
                await save.answer("Saved")
                await msg.delete()
                return True

            if data == "never_save":
                self._db.set(main.__name__, "disable_modules_fs", True)
                await save.answer("Saved")
                await msg.delete()
                return False

            await msg.delete()
            return data == "save"

    async def _update_repos(self):
        repos = (
            [self.config["repo_url"]]
            + self.config["additional_repos"]
            + list(self._db.get("Loader", "custom_repos", {}).values())
        )

        for repo in repos:
            try:
                if not repo.endswith("/"):
                    repo += "/"

                async with self.client.session.get(f"{repo}modules.json") as resp:
                    modules = await resp.json()
            except Exception:
                logger.debug("Can't fetch repo %s", repo, exc_info=True)
                continue

            for mod in self.allmodules.modules:
                if mod.__origin__.startswith("<core") or not (
                    url := getattr(mod, "heroku_source_url", None)
                ):
                    continue

                if url.rsplit("/", 1)[0] + "/" != repo:
                    continue

                class_name = mod.__class__.__name__

                if class_name not in modules or modules[class_name] != url:
                    continue

                if not hasattr(mod, "__version__") or not (
                    version_tag := await self._fetch_version_tag(url)
                ):
                    continue

                if mod.__version__ >= version_tag:
                    continue

                logger.debug("Auto-updating %s from %s", class_name, url)

                message = await self.inline.bot.send_message(
                    self.tg_id,
                    (
                        "💫 <b>Module</b>"
                        f" <code>{utils.escape_html(class_name)}</code> <b>is"
                        " being auto-updated...</b>"
                    ),
                )

                await self.download_and_install(
                    url,
                    message,
                    is_update=True,
                )

                logger.debug("Auto-update of %s complete", class_name)

    async def download_and_install(
        self,
        url: str,
        message: Message,
        is_update: bool = False,
    ):
        try:
            code = await self.allmodules.inline._local_storage.fetch(url)  # skipcq: PYL-W0212
            if not code.strip():
                raise
        except Exception:
            message = await utils.answer(
                message,
                self.strings("finding_module_in_repos"),
            )
            try:
                auth = None
                for key, value in self.config["basic_auth"].items():
                    if url.startswith(key):
                        auth = value
                        break

                code = (
                    await self.allmodules.inline._local_storage.fetch(  # skipcq: PYL-W0212
                        url,
                        auth=auth,
                    )
                )
            except Exception:
                await utils.answer(message, self.strings("no_file"))
                return

        return await self.load_module(
            code,
            message,
            url,
            save_fs=await self._confirm_fs(message, code, None, is_update),
        )

    @loader.command(aliases=["ml", "loadmod"])
    async def lmcmd(self, message: Message):
        """<reply to file> - Load module from file"""
        if not (reply := await message.get_reply_message()) or not getattr(
            reply,
            "document",
            False,
        ):
            await utils.answer(message, self.strings("no_file"))
            return

        file = await self.client.download_file(reply.document)
        
        message = await utils.answer(
            message, self.strings("loading_module_via_file")
        )

        with contextlib.suppress(UnicodeDecodeError):
            return await self.load_module(
                file.decode("utf-8"),
                message,
                save_fs=await self._confirm_fs(message, file.decode("utf-8"), None),
            )

        await utils.answer(message, self.strings("bad_unicode"))

    async def load_module(
        self,
        code: str,
        message: Message,
        source: typing.Optional[str] = None,
        save_fs: bool = False,
    ):
        
        module_name = f"heroku.modules.{utils.rand(20)}"
        origin = f"<string {source}>" if source else "<string>"

        spec = importlib.machinery.ModuleSpec(
            module_name,
            loader.StringLoader(code, origin),
            origin=origin,
        )

        try:
            instance = await self.allmodules.register_module(
                spec,
                module_name,
                origin,
                save_fs,
            )

            instance.heroku_source_url = source

            self.allmodules.send_config_one(instance)
            await self.allmodules.send_ready_one(instance, from_dlmod=True)

            loaded_modules = self.get("loaded_modules", {})
            loaded_modules[instance.__class__.__name__] = source
            self.set("loaded_modules", loaded_modules)
            logger.info(f"Loaded external module {instance.__class__.__name__} from {source or 'file'}")

        except loader.SelfSuspend as e:
            await utils.answer(
                message,
                self.strings("loaded").format(
                    utils.escape_html(instance.strings["name"]),
                    (
                        f' (v{instance.__version__[0]}.{instance.__version__[1]}.{instance.__version__[2]})'
                        if hasattr(instance, "__version__")
                        else ""
                    ),
                    self.strings("by").format(
                        (
                            f'<a href="https://t.me/{instance.heroku_meta_author.strip("@")}">'
                            f"<i>{instance.heroku_meta_author}</i></a>"
                        )
                        if hasattr(instance, "heroku_meta_author")
                        else "Anonymous"
                    ),
                    "\n\n<b>Suspended:</b>",
                    f"\n<i>{e}</i>",
                    "",
                    "",
                    "",
                    "",
                    "",
                ),
            )
        except Exception as e:
            logger.exception("Loading failed")
            await utils.answer(message, self.strings("load_failed"))
            with contextlib.suppress(Exception):
                await self.allmodules.unload_module(instance.__class__.__name__)
            return

        await self._db.remote_force_save()
        return instance

    async def _approve(
        self,
        call: InlineCall,
        channel: "herokutl.tl.types.Channel",  # type: ignore # noqa: F821
        event: asyncio.Event,
    ):
        await self.client(functions.channels.JoinChannelRequest(channel))
        event.status = True
        event.set()
        await call.edit(
            (
                "✅ <b>Joined <a"
                f' href="https://t.me/{channel.username}">{utils.escape_html(channel.title)}</a></b>'
            ),
            photo="https://raw.githubusercontent.com/coddrago/assets/refs/heads/main/heroku/approved_jr.png",
        )

    def approve_internal(self, *args, **kwargs):
        # Prevent users from abusing this method
        caller = inspect.stack()[1].function
        if caller != "send_ready_one":
            return

        return self._approve(*args, **kwargs)

    @loader.command()
    async def addrepo(self, message: Message):
        if not (args := utils.get_args_raw(message)):
            await utils.answer(message, self.strings("no_repo"))
            return

        if args in (
            repos := self._db.get("Loader", "custom_repos", {})
        ) or args in self.config["additional_repos"]:
            await utils.answer(
                message, self.strings("repo_exists").format(utils.escape_html(args))
            )
            return

        repos[utils.rand(16)] = args
        self._db.set("Loader", "custom_repos", repos)
        await utils.answer(
            message, self.strings("repo_added").format(utils.escape_html(args))
        )

    @loader.command()
    async def delrepo(self, message: Message):
        if not (args := utils.get_args_raw(message)):
            await utils.answer(message, self.strings("no_repo"))
            return

        if not any(
            repo == args for repo in self._db.get("Loader", "custom_repos", {}).values()
        ) and not any(repo == args for repo in self.config["additional_repos"]):
            await utils.answer(
                message, self.strings("repo_not_exists").format(utils.escape_html(args))
            )
            return

        self._db.set(
            "Loader",
            "custom_repos",
            {
                key: value
                for key, value in self._db.get("Loader", "custom_repos", {}).items()
                if value != args
            },
        )
        await utils.answer(
            message, self.strings("repo_deleted").format(utils.escape_html(args))
        )