import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from py3xui import Api, AsyncApi
from bot.config import settings

logger = logging.getLogger(__name__)

class VPNService:
    def __init__(self):
        # Приводим URL к нужному формату (добавляем протокол, если его нет)
        panel_url = settings.VPN_PANEL_URL.rstrip('/')
        if not panel_url.startswith(('http://', 'https://')):
            panel_url = f"https://{panel_url}"
        
        # Создаем экземпляр асинхронного API клиента
        self.api = AsyncApi(
            host=panel_url,
            username=settings.VPN_PANEL_USERNAME,
            password=settings.VPN_PANEL_PASSWORD,
            use_tls=True, # Используем TLS
            verify_ssl=False # Отключаем проверку SSL сертификата
        )
        logger.info(f"VPNService initialized for {panel_url}")

    async def _get_inbound_id(self) -> int:
        """Возвращает ID первого найденного inbound с протоколом VLESS"""
        try:
            inbounds = await self.api.inbound.get_list()
            logger.info(f"Получено {len(inbounds)} inbound'ов из панели")
            for inbound in inbounds:
                if inbound.protocol == 'vless':
                    logger.info(f"Найден VLESS inbound с ID: {inbound.id}, порт: {inbound.port}")
                    return inbound.id
            raise Exception("Не найден inbound с протоколом VLESS")
        except Exception as e:
            logger.exception("Ошибка при получении списка inbound'ов")
            raise

    async def create_user(
        self, username: str, expiry_days: int, traffic_limit_gb: Optional[int] = None
    ) -> Dict[str, Any]:
        """Создает нового VPN пользователя и возвращает данные для подключения"""
        # 1. Получаем ID inbound
        inbound_id = await self._get_inbound_id()
        
        # 2. Создаем клиента
        new_client = {
            "email": username,
            "enable": True,
            "expiryTime": int((datetime.utcnow() + timedelta(days=expiry_days)).timestamp() * 1000),
            "totalGB": traffic_limit_gb if traffic_limit_gb else 0,
            "flow": "xtls-rprx-vision",
            "limitIp": 1,
        }
        
        await self.api.inbound.add_client(inbound_id, [new_client])
        logger.info(f"Клиент {username} успешно добавлен в inbound {inbound_id}")

        # 3. Получаем обновленный inbound, чтобы найти UUID нового клиента
        updated_inbound = await self.api.inbound.get(inbound_id)
        client_uuid = None
        for client in updated_inbound.settings.clients:
            if client.email == username:
                client_uuid = client.id
                break

        if not client_uuid:
            raise Exception(f"Не удалось найти UUID для клиента {username}")

        # 4. Формируем ссылку на подписку
        sub_url = f"{settings.VPN_PANEL_URL.rstrip('/')}/sub/{username}/{client_uuid}"
        logger.info(f"Создана подписка для {username}: {sub_url}")
        
        return {
            "uuid": client_uuid,
            "subscription_url": sub_url,
            "expiry_date": datetime.fromtimestamp(new_client["expiryTime"] / 1000),
        }

    async def delete_user(self, username: str) -> bool:
        """Удаляет VPN пользователя"""
        try:
            inbound_id = await self._get_inbound_id()
            await self.api.inbound.delete_client_by_email(inbound_id, username)
            logger.info(f"Клиент {username} удалён")
            return True
        except Exception as e:
            logger.exception(f"Не удалось удалить клиента {username}")
            return False