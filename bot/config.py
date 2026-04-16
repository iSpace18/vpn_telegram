from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Optional

class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_IDS: List[int]
    DATABASE_URL: str = "sqlite+aiosqlite:///data/bot.db"
    
    VPN_PANEL_URL: str
    VPN_PANEL_USERNAME: str
    VPN_PANEL_PASSWORD: str
    
    TRIAL_DAYS: int = 3
    REFERRAL_BONUS_PERCENT: int = 15
    
    YOOKASSA_SHOP_ID: Optional[str] = None
    YOOKASSA_SECRET_KEY: Optional[str] = None
    
    WEBHOOK_URL: Optional[str] = None
    WEBHOOK_PORT: int = 8443
    
    @field_validator("ADMIN_IDS", mode="before")
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            return [int(i.strip()) for i in v.split(",") if i.strip()]
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()