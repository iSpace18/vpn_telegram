import secrets
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.models import User, ReferralBonus
from bot.config import settings

def generate_referral_code() -> str:
    return secrets.token_hex(8)

async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    full_name: str | None,
    referrer_code: str | None = None
) -> User:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        # Находим реферера по коду
        referrer = None
        if referrer_code:
            result = await session.execute(
                select(User).where(User.referral_code == referrer_code)
            )
            referrer = result.scalar_one_or_none()
        
        user = User(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            referral_code=generate_referral_code(),
            referrer_id=referrer.id if referrer else None,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        # Начисляем бонус рефереру
        if referrer:
            bonus_amount = settings.REFERRAL_BONUS_PERCENT  # или расчет от чего-то
            referrer.bonus_balance += bonus_amount
            bonus = ReferralBonus(
                referrer_id=referrer.id,
                referred_user_id=user.id,
                amount=bonus_amount,
            )
            session.add(bonus)
            await session.commit()
    
    return user

async def get_referral_stats(session: AsyncSession, user: User) -> dict:
    referrals_count = await session.scalar(
        select(func.count()).select_from(User).where(User.referrer_id == user.id)
    )
    return {
        "referral_code": user.referral_code,
        "referral_link": f"https://t.me/{(await bot.get_me()).username}?start={user.referral_code}",
        "referrals_count": referrals_count,
        "bonus_balance": user.bonus_balance,
    }