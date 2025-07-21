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
# █ █ █               https://github.com/Rewixx-png                  █ █ █
# █ █ █                                                             █ █ █
# █ █ █▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄█ █ █
# █ █▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄█ █
# █▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄█

import aiohttp
import asyncio
import typing
from .. import loader, utils
from herokutl.tl.types import Message
from ..inline.types import InlineQuery, ChosenInlineResult

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
        "action_confirmed": "✅ Действие «{action}» для <b>{name}</b> подтверждено и будет выполнено в фоновом режиме.",
        "logs_caption": "📋 Последние {lines} строк логов для <b>{name}</b>:",
        "inline_manage": "⚙️ Управление «{name}»",
        "inline_status_desc": "Статус: {status} {status_emoji} | Нажмите для управления",
        "inline_start": "▶️ Запустить",
        "inline_stop": "⏹️ Остановить",
        "inline_restart": "🔄 Перезапустить",
        "inline_logs": "📋 Логи (в лс)",
        "inline_status": "📊 Статус",
        "inline_back": "⬅️ Назад к списку",
        "inline_no_key_title": "🚫 API-ключ не настроен",
        "inline_no_key_desc": "Добавьте ключ через .config RewHostBridge",
        "inline_loading": "⏳ Загрузка...",
        "inline_logs_sent": "✅ Логи для «{name}» отправлены вам в личные сообщения.",
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
        """Получает контейнер по ID или единственный, если ID не указан."""
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
            name=details.get('container_name', 'N/A'),
            id=details.get('id', 'N/A'),
            status=details.get('status', 'N/A'),
            status_emoji=status_emojis.get(details.get('status'), '❓'),
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

    @loader.command()
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
        if "error" in logs_response:
            await utils.answer(message, self.strings("api_error").format(logs_response["error"]))
            return
        
        logs = logs_response
        if not logs or not logs.strip():
            await utils.answer(message, "📋 Логи пусты.")
            return

        caption = self.strings("logs_caption").format(lines=lines, name=container['container_name'])
        await utils.answer_file(message, logs, caption, filename=f"{container['container_name']}.log")
    
    @loader.inline_handler("rh")
    async def rh_inline_handler(self, query: InlineQuery):
        """Инлайн-обработчик для управления UserBot'ами."""
        if not self.config["api_key"]:
            return await query.answer([
                {
                    "title": self.strings("inline_no_key_title"),
                    "description": self.strings("inline_no_key_desc"),
                    "message": self.strings("no_key"),
                }
            ])
        
        q = query.query.strip().split()
        
        # Уровень 2: Меню управления конкретным контейнером
        if len(q) > 1 and q[1] == "manage":
            try:
                container_id = int(q[2])
            except (ValueError, IndexError):
                return
            
            details_response = await self._api_request(f"container/{container_id}")
            if "error" in details_response: return

            details = details_response.get("data", {})
            status_emojis = {"running": "🟢", "exited": "🔴", "restarting": "🟡"}
            
            actions = [
                {"id": f"rh_action_status_{container_id}", "title": self.strings("inline_status"), "msg": self.strings("container_info").format(
                    name=details.get('container_name', 'N/A'), id=details.get('id', 'N/A'),
                    status=details.get('status', 'N/A'), status_emoji=status_emojis.get(details.get('status'), '❓'),
                    server_name=details.get('server_info', {}).get('name', 'N/A'),
                    tariff_name=details.get('tariff_info', {}).get('name', 'N/A').capitalize(),
                    image_name=details.get('image_info', {}).get('name', 'N/A').capitalize(),
                    time_left=utils.formatted_uptime(details.get('remaining_seconds', 0)),
                    cpu=details.get('stats', {}).get('cpu', 'N/A'),
                    ram_usage=details.get('stats', {}).get('ram_usage', 'N/A'),
                    ram_perc=details.get('stats', {}).get('ram_perc', 'N/A'),
                )},
                {"id": f"rh_action_logs_{container_id}", "title": self.strings("inline_logs"), "msg": self.strings("inline_logs_sent").format(name=details.get('container_name', 'N/A'))},
            ]

            if details.get('status') == 'running':
                actions.append({"id": f"rh_action_stop_{container_id}", "title": self.strings("inline_stop"), "msg": self.strings("action_confirmed").format(action="stop", name=details.get('container_name', 'N/A'))})
                actions.append({"id": f"rh_action_restart_{container_id}", "title": self.strings("inline_restart"), "msg": self.strings("action_confirmed").format(action="restart", name=details.get('container_name', 'N/A'))})
            else:
                actions.append({"id": f"rh_action_start_{container_id}", "title": self.strings("inline_start"), "msg": self.strings("action_confirmed").format(action="start", name=details.get('container_name', 'N/A'))})
            
            results = [{
                "id": action["id"],
                "title": action["title"],
                "message": action["msg"]
            } for action in actions]

            # Кнопка "Назад"
            results.append({
                "id": "rh_action_back",
                "title": self.strings("inline_back"),
                "message": "...", # Не будет отправлено
                "switch_inline_query_current_chat": "rh"
            })
            
            return await query.answer(results)

        # Уровень 1: Список контейнеров
        containers_response = await self._api_request("containers")
        if "error" in containers_response:
            return await query.answer([{"title": "API Error", "description": containers_response["error"], "message": containers_response["error"]}])
            
        containers = containers_response.get("data", [])
        if not containers:
            return await query.answer([{"title": "No UserBots", "description": "You have no active UserBots on the hosting.", "message": self.strings("no_containers")}])
        
        results = []
        status_emojis = {"running": "🟢", "exited": "🔴", "restarting": "🟡"}
        for c in containers:
            status_emoji = status_emojis.get(c.get('status'), '❓')
            results.append({
                "id": f"rh_{c['id']}",
                "title": c['container_name'],
                "description": self.strings("inline_status_desc").format(status=c.get('status', 'N/A'), status_emoji=status_emoji),
                "message": self.strings("inline_manage").format(name=c['container_name']),
                "switch_inline_query_current_chat": f"rh manage {c['id']}"
            })
        
        await query.answer(results, cache_time=5)

    @loader.chosen_inline_handler()
    async def rh_chosen_result_handler(self, result: ChosenInlineResult):
        """Обрабатывает выбор действия из инлайн-меню."""
        result_id = result.result_id
        if not result_id.startswith("rh_action_"):
            return

        parts = result_id.split("_")
        action = parts[2]
        
        if action in ["start", "stop", "restart"]:
            container_id = int(parts[3])
            await self._api_request(f"container/{container_id}/action", method="POST", data={"action": action})
        elif action == "logs":
            container_id = int(parts[3])
            logs_response = await self._api_request(f"container/{container_id}/logs", params={"lines": 200})
            if "error" in logs_response: return
            
            container = (await self._api_request(f"container/{container_id}")).get("data")
            caption = self.strings("logs_caption").format(lines=200, name=container.get('container_name', 'N/A'))
            await self.client.send_file("me", logs_response.encode('utf-8'), caption=caption, attributes=[])


# --- END OF FILE RewHeroku-master/heroku/modules/rewhost_bridge.py ---