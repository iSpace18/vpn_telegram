import aiohttp
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from bot.config import settings

class VPNService:
    def __init__(self):
        self.base_url = settings.VPN_PANEL_URL.rstrip("/")
        self.username = settings.VPN_PANEL_USERNAME
        self.password = settings.VPN_PANEL_PASSWORD
        self._token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
    
    async def _get_auth(self) -> aiohttp.BasicAuth:
        # Marzban использует Basic Auth
        return aiohttp.BasicAuth(self.username, self.password)
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.base_url}/api{endpoint}"
        auth = await self._get_auth()
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, auth=auth, **kwargs) as resp:
                resp.raise_for_status()
                return await resp.json()
    
    async def create_user(self, username: str, expiry_days: int, traffic_limit_gb: Optional[int] = None) -> Dict[str, Any]:
        """
        Создание пользователя в Marzban.
        Возвращает данные пользователя, включая ссылку на подключение.
        """
        data = {
            "username": username,
            "proxies": {"vless": {}},  # настройки по умолчанию
            "inbounds": {"vless": ["VLESS TCP REALITY"]},
            "expire": int((datetime.utcnow() + timedelta(days=expiry_days)).timestamp()),
            "data_limit": traffic_limit_gb * 1024 * 1024 * 1024 if traffic_limit_gb else 0,  # в байтах
            "data_limit_reset_strategy": "no_reset",
            "status": "active",
        }
        user = await self._request("POST", "/user", json=data)
        # Получаем ключ доступа
        user_info = await self._request("GET", f"/user/{username}")
        # Формируем ссылку на подключение
        subscription_url = f"{self.base_url}/sub/{username}/{user_info['subscription_url'].split('/')[-1]}"
        return {
            "uuid": username,  # в Marzban username используется как идентификатор
            "subscription_url": subscription_url,
            "expiry_date": datetime.fromtimestamp(user_info["expire"]),
        }
    
    async def delete_user(self, username: str) -> bool:
        try:
            await self._request("DELETE", f"/user/{username}")
            return True
        except Exception:
            return False
    
    async def reset_user_traffic(self, username: str) -> bool:
        try:
            await self._request("POST", f"/user/{username}/reset")
            return True
        except Exception:
            return False
    
    async def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        try:
            return await self._request("GET", f"/user/{username}")
        except Exception:
            return None