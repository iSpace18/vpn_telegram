import aiohttp
import ssl
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from bot.config import settings

class VPNService:
    def __init__(self):
        self.base_url = settings.VPN_PANEL_URL.rstrip("/")
        self.username = settings.VPN_PANEL_USERNAME
        self.password = settings.VPN_PANEL_PASSWORD

    async def _get_auth(self) -> aiohttp.BasicAuth:
        return aiohttp.BasicAuth(self.username, self.password)

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.base_url}/api{endpoint}"
        auth = await self._get_auth()
        # Создаём контекст SSL, который не проверяет сертификат
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.request(method, url, auth=auth, **kwargs) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def create_user(self, username: str, expiry_days: int, traffic_limit_gb: Optional[int] = None) -> Dict[str, Any]:
        data = {
            "username": username,
            "proxies": {"vless": {}},
            "inbounds": {"vless": ["VLESS TCP REALITY"]},
            "expire": int((datetime.utcnow() + timedelta(days=expiry_days)).timestamp()),
            "data_limit": traffic_limit_gb * 1024 * 1024 * 1024 if traffic_limit_gb else 0,
            "data_limit_reset_strategy": "no_reset",
            "status": "active",
        }
        await self._request("POST", "/user", json=data)
        user_info = await self._request("GET", f"/user/{username}")
        subscription_url = f"{self.base_url}/sub/{username}/{user_info['subscription_url'].split('/')[-1]}"
        return {
            "uuid": username,
            "subscription_url": subscription_url,
            "expiry_date": datetime.fromtimestamp(user_info["expire"]),
        }

    async def delete_user(self, username: str) -> bool:
        try:
            await self._request("DELETE", f"/user/{username}")
            return True
        except Exception:
            return False