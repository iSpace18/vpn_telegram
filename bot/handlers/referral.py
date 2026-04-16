from aiogram import Router, F, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.models import User
from bot.services.referral_service import get_referral_stats
from bot.keyboards.main import back_to_main_inline
from bot.config import settings

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
        f"Бонусы можно использовать для оплаты подписки."
    )
    await message.answer(text, parse_mode="HTML", reply_markup=back_to_main_inline())

@router.inline_query()
async def inline_referral(inline_query: InlineQuery, db_session: AsyncSession, bot: Bot):
    query = inline_query.query.strip()
    if query.lower() != "/djan_vpn":
        return

    user = await db_session.scalar(select(User).where(User.telegram_id == inline_query.from_user.id))
    if not user:
        result = InlineQueryResultArticle(
            id="start",
            title="Запустить бота",
            input_message_content=InputTextMessageContent(
                message_text="Нажмите кнопку, чтобы запустить бота и получить реферальную ссылку."
            ),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🚀 Запустить", url=f"https://t.me/{(await bot.get_me()).username}?start")]
            ])
        )
        await inline_query.answer([result], cache_time=0)
        return

    ref_link = f"https://t.me/{(await bot.get_me()).username}?start={user.referral_code}"
    result = InlineQueryResultArticle(
        id="ref",
        title="🔗 Ваша реферальная ссылка",
        description="Нажмите, чтобы отправить ссылку в чат",
        input_message_content=InputTextMessageContent(
            message_text=f"🎁 Присоединяйтесь к VPN-сервису по моей ссылке и получите бонус:\n{ref_link}"
        ),
    )
    await inline_query.answer([result], cache_time=0)