from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from bot.models import User, VPNKey, Plan
from bot.keyboards.admin import admin_panel_keyboard
from bot.config import settings

router = Router()

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
    active_keys = await db_session.scalar(
        select(func.count()).select_from(VPNKey).where(VPNKey.is_active == True, VPNKey.expiry_date > func.now())
    )
    text = f"📊 Статистика:\n👥 Пользователей: {users_count}\n🔑 Активных ключей: {active_keys}"
    await callback.message.answer(text)
    await callback.answer()

@router.callback_query(F.data == "close_admin")
async def close_admin(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()