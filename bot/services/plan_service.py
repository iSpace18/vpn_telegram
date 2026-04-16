from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.models import Plan

DEFAULT_PLANS = [
    {"name": "1 день", "description": "Пробный день", "price_stars": 59, "price_rub": 59, "duration_days": 1, "traffic_limit_gb": None},
    {"name": "1 неделя", "description": "Неделя безлимита", "price_stars": 150, "price_rub": 150, "duration_days": 7, "traffic_limit_gb": None},
    {"name": "1 месяц", "description": "Месяц безлимита", "price_stars": 200, "price_rub": 200, "duration_days": 30, "traffic_limit_gb": None},
    {"name": "6 месяцев", "description": "Полгода безлимита", "price_stars": 750, "price_rub": 750, "duration_days": 180, "traffic_limit_gb": None},
    {"name": "1 год", "description": "Год безлимита", "price_stars": 1500, "price_rub": 1500, "duration_days": 365, "traffic_limit_gb": None},
]

async def ensure_default_plans(session: AsyncSession):
    # Проверяем, есть ли уже тарифы
    existing = await session.scalar(select(Plan).limit(1))
    if existing is None:
        for plan_data in DEFAULT_PLANS:
            plan = Plan(**plan_data, is_active=True)
            session.add(plan)
        await session.commit()