from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from bot.models import User, VPNKey
from bot.keyboards.profile import profile_keyboard
from bot.keyboards.main import back_to_main_inline

router = Router()

@router.message(F.text == "👤 Мой профиль")
async def profile_menu(message: Message, db_session: AsyncSession):
    user = await db_session.scalar(select(User).where(User.telegram_id == message.from_user.id))
    if not user:
        await message.answer("Пользователь не найден.")
        return

    active_keys = await db_session.scalar(
        select(func.count()).select_from(VPNKey).where(
            VPNKey.user_id == user.id,
            VPNKey.is_active == True,
            VPNKey.expiry_date > func.now()
        )
    )

    text = (
        f"👤 <b>Профиль</b>\n"
        f"🆔 ID: <code>{user.telegram_id}</code>\n"
        f"📅 Регистрация: {user.registered_at.strftime('%d.%m.%Y')}\n"
        f"🔑 Активных ключей: {active_keys}\n"
        f"💰 Бонусный баланс: {user.bonus_balance} ⭐\n"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=profile_keyboard())

@router.callback_query(F.data == "my_keys")
async def show_my_keys(callback: CallbackQuery, db_session: AsyncSession):
    user = await db_session.scalar(select(User).where(User.telegram_id == callback.from_user.id))
    keys = (await db_session.execute(
        select(VPNKey).where(VPNKey.user_id == user.id).order_by(VPNKey.created_at.desc())
    )).scalars().all()

    if not keys:
        await callback.message.answer("У вас пока нет ключей.", reply_markup=back_to_main_inline())
        await callback.answer()
        return

    text = "🔑 <b>Ваши ключи:</b>\n\n"
    for key in keys:
        status = "✅" if key.is_active and key.expiry_date > func.now() else "❌"
        text += f"{status} <code>{key.key_uuid}</code> до {key.expiry_date.strftime('%d.%m.%Y')}\n"
        if key.key_data:
            text += f"Ссылка: <code>{key.key_data}</code>\n"
        text += "\n"

    await callback.message.answer(text, parse_mode="HTML", reply_markup=back_to_main_inline())
    await callback.answer()