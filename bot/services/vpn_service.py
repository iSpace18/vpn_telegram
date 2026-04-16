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
        self.base_url = settings.VPN_PANEL_URL.rstrip("/")
        self.username = settings.VPN_PANEL_USERNAME
        self.password = settings.VPN_PANEL_PASSWORD
        self._cookies: Optional[Dict[str, str]] = None

    async def _get_auth(self) -> aiohttp.BasicAuth:
        return aiohttp.BasicAuth(self.username, self.password)

    async def _login(self, session: aiohttp.ClientSession) -> None:
        if self._cookies:
            return
        login_url = f"{self.base_url}/login"
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

            url = f"{self.base_url}/panel/api{endpoint}"
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
        
        # Ищем по remark "DjanVPN"
        for inbound in inbounds:
            if inbound.get("remark") == "DjanVPN":
                logger.info(f"Найден inbound по remark 'DjanVPN', ID {inbound['id']}")
                return inbound["id"]
        
        # Ищем по протоколу vless
        for inbound in inbounds:
            if inbound.get("protocol") == "vless":
                logger.info(f"Найден inbound по протоколу vless, ID {inbound['id']}")
                return inbound["id"]
        
        # Если ничего не подошло, берём первый
        inbound = inbounds[0]
        logger.warning(f"Не найден подходящий inbound, беру первый: remark='{inbound.get('remark')}', ID {inbound['id']}")
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
                    }
                ]
            },
        }
        await self._request("POST", "/inbounds/addClient", json=client_data)

        inbound_info = await self._request("GET", f"/inbounds/get/{inbound_id}")
        clients = inbound_info.get("obj", {}).get("settings", {}).get("clients", [])
        client = None
        for c in clients:
            if c.get("email") == username:
                client = c
                break
        if not client:
            raise Exception("Клиент не найден после создания")

        sub_url = f"{self.base_url}/sub/{username}/{client_uuid}"
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