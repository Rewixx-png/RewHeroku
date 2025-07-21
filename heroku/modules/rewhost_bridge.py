# --- START OF FILE RewHeroku-master/heroku/modules/rewhost_bridge.py ---
# █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █
# █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █
# █  ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄ ▄ █
# █ █ ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄ █ █
# █ █ █                                                             █ █ █
# █ █ █                      RewHost Bridge                         █ █ █
# █ █ █                 Userbot management module                   █ █ █
# █ █ █                                                             █ █ █
# █ █ █                  meta developer: @RewiX_X                  █ █ █
# █ █ █               https://github.com/Rewixx-png                 █ █ █
# █ █ █                                                             █ █ █
# █ █ █▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄█ █ █
# █ █▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄█ █
# █▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄█

import aiohttp
import asyncio
import typing
from .. import loader, utils
# <<< ИСПРАВЛЕНИЕ: Правильный импорт типа Message >>>
from herokutl.tl.types import Message

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
                "https://rewixx.ru", # Укажите реальный URL вашего API
                "URL API хостинга RewHost",
                validator=loader.validators.Link(),
            )
        )

    async def _api_request(self, endpoint: str, method: str = "GET", params: dict = None, data: dict = None) -> dict:
        """Вспомогательная функция для выполнения запросов к API."""
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
                    return res_json.get("data")
        except asyncio.TimeoutError:
            return {"error": "API request timed out."}
        except aiohttp.ClientError as e:
            return {"error": f"Network error: {e}"}

    # <<< ИСПРАВЛЕНИЕ: Заменен тип loader.Message на Message и улучшен тип возврата >>>
    async def _get_container(self, message: Message, args: list) -> typing.Optional[dict]:
        """Получает контейнер по ID или единственный, если ID не указан."""
        containers = await self._api_request("containers")
        if not containers or "error" in containers:
            await utils.answer(message, containers.get("error") if isinstance(containers, dict) else "Unknown API error")
            return None
        
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

    # <<< ИСПРАВЛЕНИЕ: Добавлен alias, как и планировалось >>>
    @loader.command(alias="rh")
    async def rhstatus(self, message: Message):
        """[ID] - Показать статус вашего UserBot'а на хостинге"""
        args = utils.get_args(message)
        container = await self._get_container(message, args)
        if not container:
            return

        details = await self._api_request(f"container/{container['id']}")
        if not details or "error" in details:
            await utils.answer(message, self.strings("api_error").format(details.get("error", "Unknown error")))
            return

        status_emojis = {"running": "🟢", "exited": "🔴", "restarting": "🟡"}
        
        await utils.answer(message, self.strings("container_info").format(
            name=details['container_name'],
            id=details['id'],
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
        except ValueError:
            lines = 100

        logs = await self._api_request(f"container/{container['id']}/logs", params={"lines": lines})
        if not logs or "error" in logs:
            await utils.answer(message, self.strings("api_error").format(logs.get("error", "Unknown error")))
            return
        
        if not logs.strip():
            await utils.answer(message, "📋 Логи пусты.")
            return

        caption = self.strings("logs_caption").format(lines=lines, name=container['container_name'])
        await utils.answer_file(message, logs, caption, filename=f"{container['container_name']}.log")

# --- END OF FILE RewHeroku-master/heroku/modules/rewhost_bridge.py ---```

### Что было исправлено:

1.  **Импорт `Message`:** В самом начале файла добавлена строка `from herokutl.tl.types import Message`.
2.  **Типизация:** Во всех командах (`rhstatus`, `rhstart` и т.д.) и во вспомогательной функции `_get_container` неверный тип `loader.Message` заменен на правильный `Message`.
3.  **Алиас:** Добавлен декоратор `@loader.command(alias="rh")` для команды `rhstatus`, чтобы она была доступна и по короткой команде `.rh`.
4.  **Тип возврата:** Улучшен тип возврата в `_get_container` на `typing.Optional[dict]`, что более современно и точно.
5.  **Обработка ошибок API:** Немного улучшена обработка ошибок от API, чтобы пользователю было понятнее, что пошло не так.

Теперь этот модуль должен без проблем загрузиться в ваш юзербот RewHeroku и начать работать.