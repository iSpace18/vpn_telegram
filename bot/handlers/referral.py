from aiogram import Router, F, Bot
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models import User
from bot.services.referral_service import get_referral_stats
from bot.keyboards.main import back_to_main_inline

router = Router()

@router.message(F.text == "🤝 Реферальная система")
async def referral_info(message: Message, db_session: AsyncSession, bot: Bot):
    user = await db_session.scalar(select(User).where(User.telegram_id == message.from_user.id))
    if not user:
        await message.answer("Пользователь не найден.")
        return
    
    stats = await get_referral_stats(db_session, user, bot)
    text = (
        f"🤝 <b>Реферальная программа</b>\n\n"
        f"Приглашайте друзей и получайте бонусы!\n"
        f"За каждого приглашенного пользователя вы получите {settings.REFERRAL_BONUS_PERCENT} ⭐ на баланс.\n\n"
        f"🔗 Ваша реферальная ссылка:\n<code>{stats['referral_link']}</code>\n\n"
        f"👥 Приглашено друзей: {stats['referrals_count']}\n"
        f"💰 Баланс бонусов: {stats['bonus_balance']} ⭐\n\n"
        f"Бонусы можно использовать для оплаты подписки (функция в разработке)."
    )
    await message.answer(text, parse_mode="HTML", reply_markup=back_to_main_inline())