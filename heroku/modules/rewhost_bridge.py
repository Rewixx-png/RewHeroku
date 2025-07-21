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
from .. import loader, utils
from herokutl.tl.types import Message
from ..inline.types import InlineCall, InlineQuery

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
        "inline_logs": "📋 Логи (в лс)",
        "inline_back": "⬅️ Назад к списку",
        "inline_no_key_title": "🚫 API-ключ не настроен",
        "inline_no_key_desc": "Добавьте ключ через .config RewHostBridge",
        "inline_loading": "⏳ Загрузка...",
        "inline_logs_sent": "✅ Логи для «{name}» отправлены вам в личные сообщения.",
        "action_in_progress": "⏳ Выполняю: {action}...",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_key",
                None,
                "API-ключ, полученный в боте @RewHostBot",
                validator=loader.validators.Hidden(),
            ),
            loader.ConfigValue(
                "host_url",
                "https://rewixx.ru", # URL вашего API
                "URL API хостинга RewHost",
                validator=loader.validators.Link(),
            )
        )

    async def _api_request(self, endpoint: str, method: str = "GET", params: dict = None, data: dict = None) -> dict:
        if not self.config["api_key"]:
            return {"error": self.strings("no_key")}

        headers = {"X-Web-Access-Token": self.config["api_key"]}
        url = f"{self.config['host_url'].strip('/')}/api/v1/user/{endpoint}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, headers=headers, params=params, json=data, timeout=30) as response:
                    res_json = await response.json()
                    if response.status >= 400:
                        return {"error": res_json.get("message", f"HTTP {response.status}")}
                    return res_json
        except asyncio.TimeoutError:
            return {"error": "API request timed out."}
        except aiohttp.ClientError as e:
            return {"error": f"Network error: {e}"}

    async def _get_container(self, message: Message, args: list) -> typing.Optional[dict]:
        response = await self._api_request("containers")
        if "error" in response:
            await utils.answer(message, response["error"])
            return None
        
        containers = response.get("data", [])
        
        if not containers:
            await utils.answer(message, self.strings("no_containers"))
            return None

        if not args:
            if len(containers) == 1:
                return containers[0]
            
            text = "У вас несколько UserBot'ов. Укажите ID:\n\n"
            text += "\n".join([f"• <code>{c['container_name']}</code> (ID: <code>{c['id']}</code>)" for c in containers])
            await utils.answer(message, text)
            return None
        
        try:
            container_id = int(args[0])
            container = next((c for c in containers if c['id'] == container_id), None)
            if not container:
                await utils.answer(message, f"🚫 UserBot с ID <code>{container_id}</code> не найден.")
                return None
            return container
        except (ValueError, IndexError):
            await utils.answer(message, "🚫 Некорректный ID.")
            return None

    @loader.command(alias="rh")
    async def rhstatus(self, message: Message):
        """[ID] - Показать статус вашего UserBot'а на хостинге"""
        args = utils.get_args(message)
        container = await self._get_container(message, args)
        if not container: return

        details_response = await self._api_request(f"container/{container['id']}")
        if "error" in details_response:
            await utils.answer(message, self.strings("api_error").format(details_response["error"]))
            return
        
        details = details_response.get("data", {})
        status_emojis = {"running": "🟢", "exited": "🔴", "restarting": "🟡"}
        
        await utils.answer(message, self.strings("container_info").format(
            name=details.get('container_name', 'N/A'), id=details.get('id', 'N/A'),
            status=details.get('status', 'N/A'), status_emoji=status_emojis.get(details.get('status'), '❓'),
            server_name=details.get('server_info', {}).get('name', 'N/A'),
            tariff_name=details.get('tariff_info', {}).get('name', 'N/A').capitalize(),
            image_name=details.get('image_info', {}).get('name', 'N/A').capitalize(),
            time_left=utils.formatted_uptime(details.get('remaining_seconds', 0)),
            cpu=details.get('stats', {}).get('cpu', 'N/A'),
            ram_usage=details.get('stats', {}).get('ram_usage', 'N/A'),
            ram_perc=details.get('stats', {}).get('ram_perc', 'N/A'),
        ))
        
    @loader.command()
    async def rhstart(self, message: Message):
        """[ID] - Запустить ваш UserBot на хостинге"""
        container = await self._get_container(message, utils.get_args(message))
        if not container: return
        
        result = await self._api_request(f"container/{container['id']}/action", method="POST", data={"action": "start"})
        if "error" in result:
            await utils.answer(message, self.strings("api_error").format(result["error"]))
        else:
            await utils.answer(message, self.strings("action_success").format(action="start", name=container['container_name']))
            
    @loader.command()
    async def rhstop(self, message: Message):
        """[ID] - Остановить ваш UserBot на хостинге"""
        container = await self._get_container(message, utils.get_args(message))
        if not container: return
        
        result = await self._api_request(f"container/{container['id']}/action", method="POST", data={"action": "stop"})
        if "error" in result:
            await utils.answer(message, self.strings("api_error").format(result["error"]))
        else:
            await utils.answer(message, self.strings("action_success").format(action="stop", name=container['container_name']))
            
    @loader.command()
    async def rhrestart(self, message: Message):
        """[ID] - Перезапустить ваш UserBot на хостинге"""
        container = await self._get_container(message, utils.get_args(message))
        if not container: return
        
        result = await self._api_request(f"container/{container['id']}/action", method="POST", data={"action": "restart"})
        if "error" in result:
            await utils.answer(message, self.strings("api_error").format(result["error"]))
        else:
            await utils.answer(message, self.strings("action_success").format(action="restart", name=container['container_name']))

    @loader.command(alias="rhlogss") # Добавляем алиас с опечаткой для удобства
    async def rhlogs(self, message: Message):
        """[ID] [кол-во строк] - Показать логи UserBot'а"""
        args = utils.get_args(message)
        container = await self._get_container(message, args)
        if not container: return
        
        try:
            lines = int(args[1]) if len(args) > 1 else 100
        except (ValueError, IndexError):
            lines = 100

        logs_response = await self._api_request(f"container/{container['id']}/logs", params={"lines": lines})
        
        # <<< НАЧАЛО ИСПРАВЛЕНИЯ >>>
        if "error" in logs_response:
            await utils.answer(message, self.strings("api_error").format(logs_response["error"]))
            return
        
        # Теперь logs_response - это весь словарь, извлекаем 'data'
        logs = logs_response.get("data")
        # Проверяем, что 'logs' теперь строка, а не None
        if not logs or not logs.strip():
        # <<< КОНЕЦ ИСПРАВЛЕНИЯ >>>
            await utils.answer(message, "📋 Логи пусты.")
            return

        caption = self.strings("logs_caption").format(lines=lines, name=container['container_name'])
        await utils.answer_file(message, logs, caption, filename=f"{container['container_name']}.log")
    
    @loader.inline_handler("rh")
    async def rh_inline_handler(self, query: InlineQuery):
        """Инлайн-панель управления юзерботами."""
        if not self.config["api_key"]:
            return await query.answer([
                {
                    "title": self.strings("inline_no_key_title"),
                    "description": self.strings("inline_no_key_desc"),
                    "message": self.strings("no_key"),
                }
            ])
        
        response = await self._api_request("containers")
        if "error" in response:
            return await query.answer([{"title": "API Error", "description": response["error"], "message": self.strings("api_error").format(response["error"])}])
            
        containers = response.get("data", [])
        if not containers:
            return await query.answer([{"title": "No UserBots", "description": "You have no active UserBots on the hosting.", "message": self.strings("no_containers")}])
        
        results = []
        status_emojis = {"running": "🟢", "exited": "🔴", "restarting": "🟡"}
        
        for c in containers:
            details_response = await self._api_request(f"container/{c['id']}")
            details = details_response.get("data", {})
            
            status = details.get('status', 'N/A')
            status_emoji = status_emojis.get(status, '❓')
            
            buttons = []
            if status == 'running':
                buttons.append({"text": self.strings("inline_stop"), "callback": self.rh_callback_action, "args": (f"stop_{c['id']}",)})
                buttons.append({"text": self.strings("inline_restart"), "callback": self.rh_callback_action, "args": (f"restart_{c['id']}",)})
            else:
                buttons.append({"text": self.strings("inline_start"), "callback": self.rh_callback_action, "args": (f"start_{c['id']}",)})
            
            buttons.append({"text": self.strings("inline_logs"), "callback": self.rh_callback_action, "args": (f"logs_{c['id']}",)})
            
            results.append({
                "title": c['container_name'],
                "description": self.strings("inline_status_desc").format(status=status, status_emoji=status_emoji),
                "message": self.strings("container_info").format(
                    name=details.get('container_name', 'N/A'), id=details.get('id', 'N/A'),
                    status=status, status_emoji=status_emoji,
                    server_name=details.get('server_info', {}).get('name', 'N/A'),
                    tariff_name=details.get('tariff_info', {}).get('name', 'N/A').capitalize(),
                    image_name=details.get('image_info', {}).get('name', 'N/A').capitalize(),
                    time_left=utils.formatted_uptime(details.get('remaining_seconds', 0)),
                    cpu=details.get('stats', {}).get('cpu', 'N/A'),
                    ram_usage=details.get('stats', {}).get('ram_usage', 'N/A'),
                    ram_perc=details.get('stats', {}).get('ram_perc', 'N/A'),
                ),
                "reply_markup": buttons
            })
            
        await query.answer(results, cache_time=10)

    @loader.callback_handler()
    async def rh_callback_action(self, call: InlineCall):
        if not call.data: return
        
        try:
            action, container_id_str = call.data.split("_")
            container_id = int(container_id_str)
        except (ValueError, IndexError):
            return

        await call.answer(self.strings("action_in_progress").format(action=action))
        
        if action == "logs":
            logs_response = await self._api_request(f"container/{container_id}/logs", params={"lines": 200})
            if "error" in logs_response: return
            
            logs = logs_response.get("data")
            container_response = await self._api_request(f"container/{container_id}")
            container_name = container_response.get("data", {}).get('container_name', 'N/A')
            
            caption = self.strings("logs_caption").format(lines=200, name=container_name)
            await self.client.send_file("me", logs.encode('utf-8'), caption=caption)
            await self.inline.bot.send_message(call.from_user.id, self.strings("inline_logs_sent").format(name=container_name))
        else:
            await self._api_request(f"container/{container_id}/action", method="POST", data={"action": action})
        
        await asyncio.sleep(2)
        
        details_response = await self._api_request(f"container/{container_id}")
        if "error" in details_response: return
        
        details = details_response.get("data", {})
        status_emojis = {"running": "🟢", "exited": "🔴", "restarting": "🟡"}
        status = details.get('status', 'N/A')
        
        buttons = []
        if status == 'running':
            buttons.append({"text": self.strings("inline_stop"), "callback": self.rh_callback_action, "args": (f"stop_{container_id}",)})
            buttons.append({"text": self.strings("inline_restart"), "callback": self.rh_callback_action, "args": (f"restart_{container_id}",)})
        else:
            buttons.append({"text": self.strings("inline_start"), "callback": self.rh_callback_action, "args": (f"start_{container_id}",)})
        
        buttons.append({"text": self.strings("inline_logs"), "callback": self.rh_callback_action, "args": (f"logs_{container_id}",)})
        
        try:
            await call.edit(
                text=self.strings("container_info").format(
                    name=details.get('container_name', 'N/A'), id=details.get('id', 'N/A'),
                    status=status, status_emoji=status_emojis.get(status, '❓'),
                    server_name=details.get('server_info', {}).get('name', 'N/A'),
                    tariff_name=details.get('tariff_info', {}).get('name', 'N/A').capitalize(),
                    image_name=details.get('image_info', {}).get('name', 'N/A').capitalize(),
                    time_left=utils.formatted_uptime(details.get('remaining_seconds', 0)),
                    cpu=details.get('stats', {}).get('cpu', 'N/A'),
                    ram_usage=details.get('stats', {}).get('ram_usage', 'N/A'),
                    ram_perc=details.get('stats', {}).get('ram_perc', 'N/A'),
                ),
                reply_markup=buttons
            )
        except Exception:
            pass
# --- END OF FILE RewHeroku-master/heroku/modules/rewhost_bridge.py ---