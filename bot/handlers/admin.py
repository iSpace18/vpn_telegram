from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from bot.models import User, VPNKey, Plan
from bot.keyboards.admin import admin_panel_keyboard
from bot.config import settings

router = Router()

# Фильтр для админов
def is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("🔧 Админ-панель", reply_markup=admin_panel_keyboard())

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery, db_session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    users_count = await db_session.scalar(select(func.count()).select_from(User))
    active_keys_count = await db_session.scalar(
        select(func.count()).select_from(VPNKey).where(VPNKey.is_active == True, VPNKey.expiry_date > func.now())
    )
    # Выручку в звездах посчитать сложнее без хранения истории платежей.
    text = (
        f"📊 <b>Статистика</b>\n"
        f"👥 Пользователей: {users_count}\n"
        f"🔑 Активных ключей: {active_keys_count}\n"
    )
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, db_session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.answer("Введите сообщение для рассылки. Для отмены /cancel")
    # Здесь нужно использовать FSM для сбора сообщения и рассылки.
    await callback.answer()

# Остальные обработчики админки (управление ключами, серверами) реализуются аналогично с использованием FSM.