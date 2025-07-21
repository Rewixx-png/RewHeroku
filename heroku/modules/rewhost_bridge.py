# --- START OF FILE RewHeroku-master/heroku/modules/rewhost_bridge.py ---
# █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █
# █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █
# █  ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄ ▄ █
# █ █ ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄ █ █
# █ █ █                                                             █ █ █
# █ █ █                      RewHost Bridge                         █ █ █
# █ █ █                 Userbot management module                   █ █ █
# █ █ █                                                             █ █ █
# █ █ █                  meta developer: @RewiX_X                   █ █ █
# █ █ █               https://github.com/Rewixx-png                 █ █ █
# █ █ █                                                             █ █ █
# █ █ █▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄█ █ █
# █ █▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄█ █
# █▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄█

import aiohttp
import asyncio
import typing
import io
from .. import loader, utils
from herokutl.tl.types import Message
from ..inline.types import InlineCall, InlineQuery, InlineMessage

@loader.tds
class RewHostBridgeMod(loader.Module):
    """Управляет вашим UserBot'ом на хостинге RewHost."""

    strings = {
        "name": "RewHostBridge",
        "no_key": "🚫 <b>API-ключ от RewHost не настроен.</b>\nНастройте его через <code>.config RewHostBridge</code>",
        "api_error": "🚫 <b>Ошибка API:</b> <code>{}</code>",
        "container_info": (
            "<b>ℹ️ UserBot «{name}»</b>\n\n"
            "<b>ID:</b> <code>{id}</code>\n"
            "<b>Статус:</b> <code>{status}</code> {status_emoji}\n"
            "<b>Сервер:</b> {server_name}\n"
            "<b>Тариф:</b> {tariff_name}\n"
            "<b>Образ:</b> {image_name}\n"
            "<b>Время до конца:</b> {time_left}\n\n"
            "<b>📊 Нагрузка:</b>\n"
            "  <b>CPU:</b> <code>{cpu}</code>\n"
            "  <b>RAM:</b> <code>{ram_usage} ({ram_perc})</code>"
        ),
        "no_containers": "🚫 У вас нет активных UserBot'ов на хостинге.",
        "action_success": "✅ Действие <code>{action}</code> для <b>{name}</b> успешно запущено.",
        "logs_caption": "📋 Последние {lines} строк логов для <b>{name}</b>:",
        "inline_manage": "⚙️ Управление «{name}»",
        "inline_status_desc": "Статус: {status} {status_emoji} | Нажмите для управления",
        "inline_start": "▶️ Запустить",
        "inline_stop": "⏹️ Остановить",
        "inline_restart": "🔄 Перезапустить",
        "inline_logs": "📋 Логи",
        "inline_status": "📊 Статус",
        "inline_back": "⬅️ Назад к списку",
        "inline_no_key_title": "🚫 API-ключ не настроен",
        "inline_no_key_desc": "Добавьте ключ через .config RewHostBridge",
        "inline_loading": "⏳ Загрузка...",
        "inline_logs_sent": "✅ Логи для «{name}» отправлены вам в личные сообщения.",
        "action_in_progress": "⏳ Выполняю: {action}...",
        "select_container_for_action": "Выберите UserBot, чтобы <b>{action_name}</b>:",
        "action_names": {
            "start": "запустить",
            "stop": "остановить",
            "restart": "перезагрузить",
            "logs": "посмотреть логи",
            "status": "посмотреть статус"
        }
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue("api_key", None, "API-ключ от @RewHostBot", validator=loader.validators.Hidden()),
            loader.ConfigValue("host_url", "https://rewixx.ru", "URL API хостинга", validator=loader.validators.Link())
        )

    async def _api_request(self, endpoint: str, method: str = "GET", params: dict = None, data: dict = None) -> dict:
        if not self.config["api_key"]: return {"error": self.strings("no_key")}
        headers = {"X-Web-Access-Token": self.config["api_key"]}
        url = f"{self.config['host_url'].strip('/')}/api/v1/user/{endpoint}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, headers=headers, params=params, json=data, timeout=30) as response:
                    res_json = await response.json()
                    if response.status >= 400: return {"error": res_json.get("message", f"HTTP {response.status}")}
                    return res_json
        except asyncio.TimeoutError: return {"error": "API request timed out."}
        except aiohttp.ClientError as e: return {"error": f"Network error: {e}"}

    async def _perform_action(self, message_or_call: typing.Union[Message, InlineCall], action: str, container_id: int, lines: int = 100):
        """Выполняет действие и обновляет сообщение, если это InlineCall."""
        is_call = isinstance(message_or_call, InlineCall)
        
        if action == "status":
            details_response = await self._api_request(f"container/{container_id}")
            if "error" in details_response: return await utils.answer(message_or_call, self.strings("api_error").format(details_response["error"]))
            details = details_response.get("data", {})
            status_emojis = {"running": "🟢", "exited": "🔴", "restarting": "🟡"}
            
            text = self.strings("container_info").format(
                name=details.get('container_name', 'N/A'), id=details.get('id', 'N/A'),
                status=details.get('status', 'N/A'), status_emoji=status_emojis.get(details.get('status'), '❓'),
                server_name=details.get('server_info', {}).get('name', 'N/A'),
                tariff_name=details.get('tariff_info', {}).get('name', 'N/A').capitalize(),
                image_name=details.get('image_info', {}).get('name', 'N/A').capitalize(),
                time_left=utils.formatted_uptime(details.get('remaining_seconds', 0)),
                cpu=details.get('stats', {}).get('cpu', 'N/A'),
                ram_usage=details.get('stats', {}).get('ram_usage', 'N/A'),
                ram_perc=details.get('stats', {}).get('ram_perc', 'N/A'),
            )
            
            if is_call: await message_or_call.edit(text)
            else: await utils.answer(message_or_call, text)

        elif action == "logs":
            logs_response = await self._api_request(f"container/{container_id}/logs", params={"lines": lines})
            if "error" in logs_response: return await utils.answer(message_or_call, self.strings("api_error").format(logs_response["error"]))
            
            logs = logs_response.get("data")
            container_response = await self._api_request(f"container/{container_id}")
            container_name = container_response.get("data", {}).get('container_name', 'N/A')

            if not logs or not logs.strip():
                if is_call: await call.answer("📋 Логи пусты.", show_alert=True)
                else: await utils.answer(message_or_call, "📋 Логи пусты.")
                return

            caption = self.strings("logs_caption").format(lines=lines, name=container_name)
            log_file = io.BytesIO(logs.encode('utf-8'))
            log_file.name = f"{container_name}.log"
            
            if is_call:
                await self.client.send_file("me", log_file, caption=caption)
                await message_or_call.answer(self.strings("inline_logs_sent").format(name=container_name), show_alert=True)
            else:
                await utils.answer_file(message_or_call, log_file, caption=caption)
        
        else: # start, stop, restart
            container_response = await self._api_request(f"container/{container_id}")
            container_name = container_response.get("data", {}).get('container_name', 'N/A')
            result = await self._api_request(f"container/{container_id}/action", method="POST", data={"action": action})
            
            text = self.strings("api_error").format(result["error"]) if "error" in result else self.strings("action_success").format(action=action, name=container_name)
            
            if is_call: await message_or_call.edit(text)
            else: await utils.answer(message_or_call, text)
    
    async def _interactive_selector(self, message: Message, action: str):
        """Показывает инлайн-меню выбора контейнера для действия."""
        await message.delete()
        
        loading_msg = await self.inline.form(text=self.strings("inline_loading"), message=message)
        
        response = await self._api_request("containers")
        if "error" in response:
            return await loading_msg.edit(response["error"])
        
        containers = response.get("data", [])
        if not containers:
            return await loading_msg.edit(self.strings("no_containers"))

        if len(containers) == 1:
            await loading_msg.delete()
            return await self._perform_action(message, action, containers[0]['id'])
        
        action_name = self.strings("action_names").get(action, action)
        text = self.strings("select_container_for_action").format(action_name=action_name)
        
        buttons = [
            {"text": c['container_name'], "callback": self.rh_interactive_callback, "args": (action, c['id'])}
            for c in containers
        ]
        
        await loading_msg.edit(text, reply_markup=utils.chunks(buttons, 2))

    @loader.command()
    async def rhstatus(self, message: Message):
        """[ID] - Показать статус вашего UserBot'а на хостинге"""
        args = utils.get_args(message)
        if args:
            container = await self._get_container(message, args)
            if container: await self._perform_action(message, "status", container['id'])
        else:
            await self._interactive_selector(message, "status")

    @loader.command()
    async def rhstart(self, message: Message):
        """[ID] - Запустить ваш UserBot на хостинге"""
        args = utils.get_args(message)
        if args:
            container = await self._get_container(message, args)
            if container: await self._perform_action(message, "start", container['id'])
        else:
            await self._interactive_selector(message, "start")

    @loader.command()
    async def rhstop(self, message: Message):
        """[ID] - Остановить ваш UserBot на хостинге"""
        args = utils.get_args(message)
        if args:
            container = await self._get_container(message, args)
            if container: await self._perform_action(message, "stop", container['id'])
        else:
            await self._interactive_selector(message, "stop")

    @loader.command()
    async def rhrestart(self, message: Message):
        """[ID] - Перезапустить ваш UserBot на хостинге"""
        args = utils.get_args(message)
        if args:
            container = await self._get_container(message, args)
            if container: await self._perform_action(message, "restart", container['id'])
        else:
            await self._interactive_selector(message, "restart")
            
    @loader.command(alias="rhlogss")
    async def rhlogs(self, message: Message):
        """[ID] [кол-во строк] - Показать логи UserBot'а"""
        args = utils.get_args(message)
        try:
            lines = int(args[1]) if len(args) > 1 else 100
        except (ValueError, IndexError):
            lines = 100
            
        if args:
            container = await self._get_container(message, args)
            if container: await self._perform_action(message, "logs", container['id'], lines=lines)
        else:
            await self._interactive_selector(message, "logs")

    @loader.callback_handler()
    async def rh_interactive_callback(self, call: InlineCall):
        """Обрабатывает нажатия кнопок из интерактивного селектора."""
        if not call.data: return
        
        try:
            action, container_id_str = call.data
            container_id = int(container_id_str)
        except (ValueError, IndexError):
            return
        
        await self._perform_action(call, action, container_id)

# --- END OF FILE RewHeroku-master/heroku/modules/rewhost_bridge.py ---