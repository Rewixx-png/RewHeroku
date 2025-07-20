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

import uuid
import logging
import asyncio

import herokutl
from herokutl.extensions.html import CUSTOM_EMOJIS
from herokutl.tl.types import Message
from herokutl.sessions import StringSession

from .. import loader, main, utils, version
from ..inline.types import InlineCall
from ..tl_cache import CustomTelegramClient
from .._internal import restart
from ..states.user_states import AddSessionState # <<< НОВЫЙ ИМПОРТ
import random

logger = logging.getLogger(__name__)


@loader.tds
class CoreMod(loader.Module):
    """Control core userbot settings"""

    strings = {"name": "Settings"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "allow_nonstandart_prefixes",
                False,
                "Allow non-standard prefixes like premium emojis or multi-symbol prefixes",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "alias_emoji",
                "<emoji document_id=4974259868996207180>▪️</emoji>",
                "just emoji in .aliases",
            ),
            loader.ConfigValue(
                "allow_external_access",
                False,
                (
                    "Allow codrago.t.me to control the actions of your userbot"
                    " externally. Do not turn this option on unless it's requested by"
                    " the developer."
                ),
                validator=loader.validators.Boolean(),
                on_change=self._process_config_changes,
            ),
        )

    async def client_ready(self):
        self._markup = utils.chunks(
            [
                {
                    "text": self.strings(platform),
                    "callback": self._inline__choose__installation,
                    "args": (platform,),
                }
                for platform in ["vds", "userland", "jamhost", "rewhost"]
            ],
            2,
        )

    def _process_config_changes(self):
        if (
            self.config["allow_external_access"]
            and 1714120111 not in self._client.dispatcher.security.owner
        ):
            self._client.dispatcher.security.owner.append(1714120111)
            self._nonick.append(1714120111)
        elif (
            not self.config["allow_external_access"]
            and 1714120111 in self._client.dispatcher.security.owner
        ):
            self._client.dispatcher.security.owner.remove(1714120111)
            self._nonick.remove(1714120111)

    async def blacklistcommon(self, message: Message):
        args = utils.get_args(message)

        if len(args) > 2:
            await utils.answer(message, self.strings("too_many_args"))
            return

        chatid = None
        module = None

        if args:
            try:
                chatid = int(args[0])
            except ValueError:
                module = args[0]

        if len(args) == 2:
            module = args[1]

        if chatid is None:
            chatid = utils.get_chat_id(message)

        module = self.allmodules.get_classname(module)
        return f"{str(chatid)}.{module}" if module else chatid

    @loader.command(
        ru_doc="Информация о Хероку",
        en_doc="Information of Heroku",
        ua_doc="Інформація про Хероку",
        de_doc="Informationen über Heroku",
    )
    async def herokucmd(self, message: Message):
        await utils.answer(
            message,
            self.strings("heroku").format(
                (
                    utils.get_platform_emoji()
                    if self._client.heroku_me.premium and CUSTOM_EMOJIS
                    else "🪐 <b>Heroku userbot</b>"
                ),
                *version.__version__,
                utils.get_commit_url(),
                f"{herokutl.__version__} #{herokutl.tl.alltlobjects.LAYER}",
            )
            + (
                ""
                if version.branch == "master"
                else self.strings("unstable").format(version.branch)
            ),
            file="https://raw.githubusercontent.com/coddrago/assets/refs/heads/main/heroku/heroku_cmd.png",
            reply_to=getattr(message, "reply_to_msg_id", None),
        )

    @loader.command()
    async def blacklist(self, message: Message):
        chatid = await self.blacklistcommon(message)
        self._db.set(
            main.__name__,
            "blacklist_chats",
            self._db.get(main.__name__, "blacklist_chats", []) + [chatid],
        )
        await utils.answer(message, self.strings("blacklisted").format(chatid))

    @loader.command()
    async def unblacklist(self, message: Message):
        chatid = await self.blacklistcommon(message)
        self._db.set(
            main.__name__,
            "blacklist_chats",
            list(set(self._db.get(main.__name__, "blacklist_chats", [])) - {chatid}),
        )
        await utils.answer(message, self.strings("unblacklisted").format(chatid))

    async def getuser(self, message: Message):
        try:
            return int(utils.get_args(message)[0])
        except (ValueError, IndexError):
            if reply := await message.get_reply_message():
                return reply.sender_id
            return message.to_id.user_id if message.is_private else False

    @loader.command()
    async def blacklistuser(self, message: Message):
        if not (user := await self.getuser(message)):
            await utils.answer(message, self.strings("who_to_blacklist"))
            return
        self._db.set(
            main.__name__,
            "blacklist_users",
            self._db.get(main.__name__, "blacklist_users", []) + [user],
        )
        await utils.answer(message, self.strings("user_blacklisted").format(user))

    @loader.command()
    async def unblacklistuser(self, message: Message):
        if not (user := await self.getuser(message)):
            await utils.answer(message, self.strings("who_to_unblacklist"))
            return
        self._db.set(
            main.__name__,
            "blacklist_users",
            list(set(self._db.get(main.__name__, "blacklist_users", [])) - {user}),
        )
        await utils.answer(
            message,
            self.strings("user_unblacklisted").format(user),
        )

    @loader.command()
    async def setprefix(self, message: Message):
        if not (args := utils.get_args_raw(message)):
            await utils.answer(message, self.strings("what_prefix"))
            return
        if len(args) != 1 and not self.config.get("allow_nonstandart_prefixes"):
            await utils.answer(message, self.strings("prefix_incorrect"))
            return
        if args == "s":
            await utils.answer(message, self.strings("prefix_incorrect"))
            return
        oldprefix = utils.escape_html(self.get_prefix())
        self._db.set(main.__name__, "command_prefix", args)
        await utils.answer(
            message,
            self.strings("prefix_set").format(
                "<emoji document_id=5197474765387864959>👍</emoji>",
                newprefix=utils.escape_html(args),
                oldprefix=utils.escape_html(oldprefix),
            ),
        )

    @loader.command()
    async def aliases(self, message: Message):
        await utils.answer(
            message,
            self.strings("aliases")
            + "<blockquote expandable>"
            + "\n".join(
                [
                    (self.config["alias_emoji"] + f" <code>{i}</code> <- {y}")
                    for i, y in self.allmodules.aliases.items()
                ]
            )
            + "</blockquote>",
        )

    @loader.command()
    async def addalias(self, message: Message):
        if len(args := utils.get_args(message)) != 2:
            await utils.answer(message, self.strings("alias_args"))
            return
        alias, cmd = args
        if self.allmodules.add_alias(alias, cmd):
            self.set("aliases", {**self.get("aliases", {}), alias: cmd})
            await utils.answer(
                message, self.strings("alias_created").format(utils.escape_html(alias))
            )
        else:
            await utils.answer(
                message, self.strings("no_command").format(utils.escape_html(cmd))
            )

    @loader.command()
    async def delalias(self, message: Message):
        args = utils.get_args(message)
        if len(args) != 1:
            await utils.answer(message, self.strings("delalias_args"))
            return
        alias = args[0]
        if not self.allmodules.remove_alias(alias):
            await utils.answer(
                message, self.strings("no_alias").format(utils.escape_html(alias))
            )
            return
        current = self.get("aliases", {})
        del current[alias]
        self.set("aliases", current)
        await utils.answer(
            message, self.strings("alias_removed").format(utils.escape_html(alias))
        )

    @loader.command()
    async def cleardb(self, message: Message):
        await self.inline.form(
            self.strings("confirm_cleardb"),
            message,
            reply_markup=[
                {"text": self.strings("cleardb_confirm"), "callback": self._inline__cleardb},
                {"text": self.strings("cancel"), "action": "close"},
            ],
        )

    async def _inline__cleardb(self, call: InlineCall):
        self._db.clear()
        self._db.save()
        await utils.answer(call, self.strings("db_cleared"))

    async def installationcmd(self, message: Message):
        """| Guide of installation"""
        args = utils.get_args_raw(message)
        if (not args or args not in {"-v", "-r", "-jh", "-ms", "-u"}) and not (
            await self.inline.form(
                self.strings("choose_installation"),
                message,
                reply_markup=self._markup,
                photo="https://raw.githubusercontent.com/coddrago/assets/refs/heads/main/heroku/heroku_installation.png",
                disable_security=True,
            )
        ):
            await self.client.send_file(
                message.peer_id,
                "https://raw.githubusercontent.com/coddrago/assets/refs/heads/main/heroku/heroku_installation.png",
                caption=self.strings["installation"],
                reply_to=getattr(message, "reply_to_msg_id", None),
            )
        elif "-v" in args:
            await utils.answer(message, self.strings["vds_install"])
        elif "-jh" in args:
            await utils.answer(message, self.strings["jamhost_install"])
        elif "-u" in args:
            await utils.answer(message, self.strings["userland_install"])
        elif "-rh" in args:
            await utils.answer(message, self.strings["rewhost_install"])

    async def _inline__choose__installation(self, call: InlineCall, platform: str):
        await call.edit(
            text=self.strings(f"{platform}_install"), reply_markup=self._markup
        )

    @loader.command()
    async def addsession(self, message: Message):
        """<reply to session string> - Add new account"""
        state = self.inline._dp.current_state(
            chat=message.chat_id, user=message.sender_id
        )
        reply = await message.get_reply_message()
        if not reply or not reply.raw_text:
            await utils.answer(message, "Ответьте на сообщение с сессионной строкой.")
            return

        session_string = reply.raw_text

        temp_client = CustomTelegramClient(
            StringSession(session_string),
            main.heroku.api_token.ID,
            main.heroku.api_token.HASH,
        )
        try:
            await temp_client.connect()
            new_user = await temp_client.get_me()
            if not new_user:
                raise Exception("Could not get user info from session.")
        except Exception as e:
            await utils.answer(
                message, f"<b>Invalid session string.</b>\n\n<pre>{e}</pre>"
            )
            return
        finally:
            await temp_client.disconnect()

        await state.set_state(AddSessionState.confirming)
        await state.update_data(session_string=session_string)

        text = (
            "<b>Confirm Account Addition</b>\n\n"
            "You are about to add the account:"
            f" <code>{new_user.first_name} (ID: {new_user.id})</code>.\n\n"
            "Are you sure?"
        )

        await self.inline.form(
            message=message,
            text=text,
            reply_markup=[
                {"text": "✅ Approve", "callback": self._approve_add_session},
                {"text": "❌ Deny", "callback": self._deny_add_session},
            ],
        )

    @loader.callback_handler(state=AddSessionState.confirming)
    async def _approve_add_session(self, call: InlineCall):
        state = self.inline._dp.current_state(
            chat=call.chat_id, user=call.from_user.id
        )
        data = await state.get_data()
        session_string = data.get("session_string")

        if not session_string:
            await call.edit(
                "<b>Error:</b> Session data lost. Please try again."
            )
            await state.finish()
            return

        self.allmodules.autosaver_paused = True
        logging.warning("Database autosaver paused for new account registration.")

        try:
            await call.edit(
                "<b>✅ Аккаунт подтвержден.\n\nСохраняю сессию и готовлюсь к"
                " перезагрузке...\nЭто может занять несколько минут.</b>"
            )
            logging.info("Creating temporary client to save session...")
            temp_client = CustomTelegramClient(
                StringSession(session_string),
                main.heroku.api_token.ID,
                main.heroku.api_token.HASH,
            )
            await temp_client.connect()

            logging.info("Saving new session to file...")
            await main.heroku.save_client_session(temp_client, delay_restart=True)
            await temp_client.disconnect()
            logging.info("Temporary client disconnected.")

            await call.edit(
                "<b>✅ Аккаунт успешно добавлен!</b>\n\n"
                "Чтобы изменения вступили в силу, юзербот необходимо перезагрузить.\n\n"
                "<i>Если перезагрузка не начнется в течение 10 секунд, нажмите кнопку"
                " ниже.</i>",
                reply_markup=[
                    {
                        "text": "🔄 Перезагрузить юзербот",
                        "callback": self.restart_from_callback,
                    }
                ],
            )
            asyncio.ensure_future(self.delayed_restart(call))
        except Exception as e:
            logger.exception("Failed to add account")
            await call.edit(
                "<b>Произошла ошибка при добавлении"
                f" аккаунта:</b>\n\n<pre>{e}</pre>"
            )
        finally:
            self.allmodules.autosaver_paused = False
            logging.warning("Database autosaver resumed.")
            await state.finish()

    @loader.callback_handler(state=AddSessionState.confirming)
    async def _deny_add_session(self, call: InlineCall):
        state = self.inline._dp.current_state(
            chat=call.chat_id, user=call.from_user.id
        )
        await state.finish()
        await call.edit("<b>Добавление аккаунта отклонено.</b>")

    async def delayed_restart(self, call: InlineCall):
        await asyncio.sleep(2)
        logging.info("Restarting userbot to apply new account...")
        try:
            restart()
            await asyncio.sleep(3600)
        except Exception:
            await call.edit(
                "<b>🔴 Автоматическая перезагрузка не удалась!</b>\n\n"
                "Нажмите кнопку ниже, чтобы попробовать снова.",
                reply_markup=[
                    {
                        "text": "🔄 Перезагрузить юзербот",
                        "callback": self.restart_from_callback,
                    }
                ],
            )

    async def restart_from_callback(self, call: InlineCall):
        await call.edit("<b>🔄 Перезагружаюсь...</b>")
        logging.info("Restarting userbot from callback button...")
        try:
            restart()
            await asyncio.sleep(3600)
        except Exception:
            await call.edit(
                "<b>🔴 Ошибка перезагрузки. Пожалуйста, перезагрузите вручную.</b>"
            )
