import aiohttp
import ssl
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from bot.config import settings

logger = logging.getLogger(__name__)

class VPNService:
    def __init__(self):
        # Разбираем полный URL на host:port и префикс (webBasePath)
        full_url = settings.VPN_PANEL_URL.rstrip("/")
        # Если после host:port есть путь, он будет префиксом
        # Пример: https://89.44.76.190:24811/1tp7Aa7VP5Rx2yVSi8
        parts = full_url.split("/")
        if len(parts) >= 4 and parts[3] != "":
            self.base_url = "/".join(parts[:3])   # https://89.44.76.190:24811
            self.prefix = "/" + "/".join(parts[3:])  # /1tp7Aa7VP5Rx2yVSi8
        else:
            self.base_url = full_url
            self.prefix = ""

        self.username = settings.VPN_PANEL_USERNAME
        self.password = settings.VPN_PANEL_PASSWORD
        self._cookies: Optional[Dict[str, str]] = None
        logger.info(f"VPNService: base_url={self.base_url}, prefix={self.prefix}")

    async def _get_auth(self) -> aiohttp.BasicAuth:
        return aiohttp.BasicAuth(self.username, self.password)

    async def _login(self, session: aiohttp.ClientSession) -> None:
        if self._cookies:
            return
        login_url = f"{self.base_url}{self.prefix}/login"
        auth = await self._get_auth()
        logger.info(f"Попытка входа: {login_url}")
        try:
            async with session.post(
                login_url,
                auth=auth,
                data={"username": self.username, "password": self.password},
                allow_redirects=False,
                ssl=False
            ) as resp:
                logger.info(f"Ответ входа: {resp.status}")
                if resp.status in (200, 302):
                    # Сохраняем все куки для дальнейших запросов
                    cookies = session.cookie_jar.filter_cookies(login_url)
                    self._cookies = {key: cookie.value for key, cookie in cookies.items()}
                    logger.info(f"Куки получены: {list(self._cookies.keys())}")
                else:
                    text = await resp.text()
                    logger.warning(f"Статус входа {resp.status}, тело: {text[:200]}")
        except Exception as e:
            logger.exception("Ошибка при входе")

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connector = aiohttp.TCPConnector(ssl=ssl_context)

        async with aiohttp.ClientSession(connector=connector, cookies=self._cookies) as session:
            await self._login(session)
            auth = await self._get_auth() if not self._cookies else None

            # Правильный URL: base_url + префикс + /panel/api + endpoint
            url = f"{self.base_url}{self.prefix}/panel/api{endpoint}"
            logger.info(f"Запрос: {method} {url}")
            try:
                async with session.request(method, url, auth=auth, ssl=False, **kwargs) as resp:
                    logger.info(f"Ответ: {resp.status} для {url}")
                    if resp.status != 200:
                        text = await resp.text()
                        logger.error(f"Ошибка API: {resp.status}, тело: {text[:300]}")
                    resp.raise_for_status()
                    return await resp.json()
            except Exception as e:
                logger.exception(f"Ошибка запроса к {url}")
                raise

    async def _get_inbound_id(self) -> int:
        data = await self._request("GET", "/inbounds/list")
        inbounds = data.get("obj", [])
        if not inbounds:
            raise Exception("В панели нет inbound. Создайте inbound в 3x-ui.")
        
        # Ищем inbound с протоколом VLESS
        for inbound in inbounds:
            if inbound.get("protocol") == "vless":
                logger.info(f"Найден inbound VLESS с ID {inbound['id']}")
                return inbound["id"]
        # Если VLESS не найден, берём первый попавшийся (на всякий случай)
        inbound = inbounds[0]
        logger.warning(f"VLESS не найден, беру первый inbound: remark='{inbound.get('remark')}', ID {inbound['id']}")
        return inbound["id"]

    async def create_user(
        self, username: str, expiry_days: int, traffic_limit_gb: Optional[int] = None
    ) -> Dict[str, Any]:
        inbound_id = await self._get_inbound_id()
        client_uuid = str(uuid.uuid4())
        expiry_timestamp = int((datetime.utcnow() + timedelta(days=expiry_days)).timestamp() * 1000)

        client_data = {
            "id": inbound_id,
            "settings": {
                "clients": [
                    {
                        "id": client_uuid,
                        "email": username,
                        "enable": True,
                        "expiryTime": expiry_timestamp,
                        "totalGB": traffic_limit_gb if traffic_limit_gb else 0,
                        "flow": "xtls-rprx-vision",
                        "limitIp": 1,
                    }
                ]
            },
        }
        await self._request("POST", "/inbounds/addClient", json=client_data)

        # Получаем обновлённый inbound для извлечения данных клиента
        inbound_info = await self._request("GET", f"/inbounds/get/{inbound_id}")
        clients = inbound_info.get("obj", {}).get("settings", {}).get("clients", [])
        client = None
        for c in clients:
            if c.get("email") == username:
                client = c
                break
        if not client:
            raise Exception("Клиент не найден после создания")

        # Формируем ссылку для подключения (sub)
        sub_url = f"{self.base_url}{self.prefix}/sub/{username}/{client_uuid}"
        logger.info(f"Клиент создан: {username}, ссылка: {sub_url}")
        return {
            "uuid": client_uuid,
            "subscription_url": sub_url,
            "expiry_date": datetime.fromtimestamp(client["expiryTime"] / 1000),
        }

    async def delete_user(self, username: str) -> bool:
        inbound_id = await self._get_inbound_id()
        await self._request(
            "POST",
            f"/inbounds/delClient/{inbound_id}",
            json={"email": username},
        )
        logger.info(f"Клиент {username} удалён")
        return True