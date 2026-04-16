import aiohttp
import ssl
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from bot.config import settings

class VPNService:
    def __init__(self):
        # Убираем слеш в конце, если он есть
        self.base_url = settings.VPN_PANEL_URL.rstrip("/")
        self.username = settings.VPN_PANEL_USERNAME
        self.password = settings.VPN_PANEL_PASSWORD
        self._cookies: Optional[Dict[str, str]] = None

    async def _get_auth(self) -> aiohttp.BasicAuth:
        """Базовая аутентификация (используется как запасной вариант)"""
        return aiohttp.BasicAuth(self.username, self.password)

    async def _login(self, session: aiohttp.ClientSession) -> None:
        """Авторизация для получения cookies (требуется для большинства запросов API)"""
        if self._cookies:
            return
        login_url = f"{self.base_url}/login"
        auth = await self._get_auth()
        # Пробуем авторизоваться через POST, чтобы получить cookie
        try:
            async with session.post(
                login_url,
                auth=auth,
                data={"username": self.username, "password": self.password},
                allow_redirects=False
            ) as resp:
                if resp.status in (200, 302):
                    # Сохраняем cookies для последующих запросов
                    self._cookies = {key: value.value for key, value in session.cookie_jar}
        except Exception:
            # Если не получилось, будем использовать Basic Auth для каждого запроса
            pass

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        # Создаём SSL-контекст, игнорирующий ошибки сертификата (для самоподписанных)
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connector = aiohttp.TCPConnector(ssl=ssl_context)

        async with aiohttp.ClientSession(connector=connector, cookies=self._cookies) as session:
            # Пробуем авторизоваться, если ещё нет cookies
            await self._login(session)
            auth = await self._get_auth() if not self._cookies else None

            # Полный URL для API – обязательно начинается с /panel/api
            url = f"{self.base_url}/panel/api{endpoint}"
            async with session.request(method, url, auth=auth, **kwargs) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def _get_inbound_id(self, protocol: str = "vless") -> int:
        """Получает ID первого inbound с заданным протоколом"""
        data = await self._request("GET", "/inbounds/list")
        inbounds = data.get("obj", [])
        for inbound in inbounds:
            if inbound.get("protocol") == protocol:
                return inbound["id"]
        raise Exception(f"Inbound с протоколом {protocol} не найден")

    async def create_user(
        self, username: str, expiry_days: int, traffic_limit_gb: Optional[int] = None
    ) -> Dict[str, Any]:
        # Находим ID нужного inbound (например, VLESS)
        inbound_id = await self._get_inbound_id("vless")

        # Подготавливаем данные нового клиента
        import uuid
        client_uuid = str(uuid.uuid4())
        client_data = {
            "id": inbound_id,
            "settings": {
                "clients": [
                    {
                        "id": client_uuid,
                        "email": username,
                        "enable": True,
                        "expiryTime": int((datetime.utcnow() + timedelta(days=expiry_days)).timestamp() * 1000),
                        "totalGB": traffic_limit_gb if traffic_limit_gb else 0,
                    }
                ]
            },
        }
        # Добавляем клиента в inbound
        await self._request("POST", "/inbounds/addClient", json=client_data)

        # Получаем обновлённую информацию об inbound, чтобы извлечь ссылку для подключения
        inbound_info = await self._request("GET", f"/inbounds/get/{inbound_id}")
        # Ищем созданного клиента в списке
        client = None
        for c in inbound_info.get("obj", {}).get("settings", {}).get("clients", []):
            if c.get("email") == username:
                client = c
                break
        if not client:
            raise Exception("Клиент не найден после создания")

        # Формируем ссылку для подключения (sub_url)
        # Обычно она строится как /sub/{email}/{uuid}
        sub_url = f"{self.base_url}/sub/{username}/{client_uuid}"
        return {
            "uuid": client_uuid,
            "subscription_url": sub_url,
            "expiry_date": datetime.fromtimestamp(client["expiryTime"] / 1000),
        }

    async def delete_user(self, username: str) -> bool:
        # Находим inbound и удаляем клиента по email
        inbound_id = await self._get_inbound_id("vless")
        await self._request(
            "POST",
            f"/inbounds/delClient/{inbound_id}",
            json={"email": username},
        )
        return True