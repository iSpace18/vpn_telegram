from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from bot.models import User, VPNKey, Plan
from bot.keyboards.admin import (
    admin_panel_keyboard,
    admin_plans_menu_keyboard,
    admin_keys_menu_keyboard,
    back_to_admin_keyboard,
)
from bot.config import settings

router = Router()

# FSM для рассылки
class BroadcastState(StatesGroup):
    waiting_for_message = State()

# FSM для добавления тарифа
class AddPlanState(StatesGroup):
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_price_stars = State()
    waiting_for_price_rub = State()
    waiting_for_duration_days = State()
    waiting_for_traffic_limit = State()

# FSM для ручного управления ключами
class KeyActionState(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_key_uuid = State()
    waiting_for_confirm = State()

def is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS

# ---------- Главное меню админки ----------
@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return
    await message.answer("🔧 Админ-панель", reply_markup=admin_panel_keyboard())

@router.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.edit_text("🔧 Админ-панель", reply_markup=admin_panel_keyboard())
    await callback.answer()

@router.callback_query(F.data == "close_admin")
async def close_admin(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()

# ---------- Статистика ----------
@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery, db_session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    users_total = await db_session.scalar(select(func.count()).select_from(User))
    active_keys = await db_session.scalar(
        select(func.count()).select_from(VPNKey).where(
            VPNKey.is_active == True,
            VPNKey.expiry_date > func.now()
        )
    )
    # Сумма бонусов и выручка (если нужно, можно добавить сумму платежей)
    text = (
        f"📊 <b>Статистика</b>\n"
        f"👥 Всего пользователей: {users_total}\n"
        f"🔑 Активных ключей: {active_keys}\n"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_to_admin_keyboard())
    await callback.answer()

# ---------- Управление тарифами ----------
@router.callback_query(F.data == "admin_plans_menu")
async def plans_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.edit_text("📦 Управление тарифами", reply_markup=admin_plans_menu_keyboard())
    await callback.answer()

@router.callback_query(F.data == "admin_plan_add")
async def add_plan_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.edit_text(
        "Введите название тарифа (например: 'Месяц безлимит'):",
        reply_markup=back_to_admin_keyboard()
    )
    await state.set_state(AddPlanState.waiting_for_name)
    await callback.answer()

@router.message(AddPlanState.waiting_for_name)
async def add_plan_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(name=message.text)
    await message.answer("Введите описание тарифа (можно '-'):")
    await state.set_state(AddPlanState.waiting_for_description)

@router.message(AddPlanState.waiting_for_description)
async def add_plan_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Введите цену в Telegram Stars (целое число, например 150):")
    await state.set_state(AddPlanState.waiting_for_price_stars)

@router.message(AddPlanState.waiting_for_price_stars)
async def add_plan_stars(message: Message, state: FSMContext):
    try:
        price_stars = int(message.text)
    except ValueError:
        await message.answer("❌ Введите целое число.")
        return
    await state.update_data(price_stars=price_stars)
    await message.answer("Введите цену в рублях (для ЮKassa) или 0, если не используется:")
    await state.set_state(AddPlanState.waiting_for_price_rub)

@router.message(AddPlanState.waiting_for_price_rub)
async def add_plan_rub(message: Message, state: FSMContext):
    try:
        price_rub = int(message.text)
    except ValueError:
        await message.answer("❌ Введите целое число.")
        return
    await state.update_data(price_rub=price_rub if price_rub > 0 else None)
    await message.answer("Введите длительность в днях (например: 30):")
    await state.set_state(AddPlanState.waiting_for_duration_days)

@router.message(AddPlanState.waiting_for_duration_days)
async def add_plan_days(message: Message, state: FSMContext):
    try:
        days = int(message.text)
    except ValueError:
        await message.answer("❌ Введите целое число.")
        return
    await state.update_data(duration_days=days)
    await message.answer("Введите лимит трафика в ГБ (или 0 для безлимита):")
    await state.set_state(AddPlanState.waiting_for_traffic_limit)

@router.message(AddPlanState.waiting_for_traffic_limit)
async def add_plan_traffic(message: Message, state: FSMContext, db_session: AsyncSession):
    try:
        limit = int(message.text)
    except ValueError:
        await message.answer("❌ Введите целое число.")
        return
    data = await state.get_data()
    plan = Plan(
        name=data["name"],
        description=data["description"],
        price_stars=data["price_stars"],
        price_rub=data["price_rub"],
        duration_days=data["duration_days"],
        traffic_limit_gb=limit if limit > 0 else None,
        is_active=True
    )
    db_session.add(plan)
    await db_session.commit()
    await message.answer("✅ Тариф успешно добавлен!", reply_markup=back_to_admin_keyboard())
    await state.clear()

@router.callback_query(F.data == "admin_plan_delete")
async def delete_plan_list(callback: CallbackQuery, db_session: AsyncSession):
    if not is_admin(callback.from_user.id):
        return
    plans = (await db_session.execute(select(Plan))).scalars().all()
    if not plans:
        await callback.answer("Нет тарифов для удаления.", show_alert=True)
        return
    # Упрощённо: выводим список с кнопками (можно реализовать через InlineKeyboard)
    text = "Выберите тариф для удаления (пока не реализовано в UI, используйте БД)"
    await callback.message.edit_text(text, reply_markup=back_to_admin_keyboard())
    await callback.answer()

# ---------- Управление ключами (заглушки, можно расширить) ----------
@router.callback_query(F.data == "admin_keys_menu")
async def keys_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("🔧 Управление ключами", reply_markup=admin_keys_menu_keyboard())
    await callback.answer()

# ---------- Рассылка ----------
@router.callback_query(F.data == "admin_broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "📢 Введите текст сообщения для рассылки всем пользователям:",
        reply_markup=back_to_admin_keyboard()
    )
    await state.set_state(BroadcastState.waiting_for_message)
    await callback.answer()

@router.message(BroadcastState.waiting_for_message)
async def broadcast_send(message: Message, state: FSMContext, db_session: AsyncSession, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    # Получаем всех пользователей
    users = (await db_session.execute(select(User))).scalars().all()
    success = 0
    failed = 0
    for user in users:
        try:
            await bot.send_message(user.telegram_id, message.text)
            success += 1
        except Exception:
            failed += 1
    await message.answer(f"✅ Рассылка завершена.\nУспешно: {success}\nНеудачно: {failed}")
    await state.clear()

# ---------- Заглушка для серверов ----------
@router.callback_query(F.data == "admin_servers")
async def admin_servers(callback: CallbackQuery):
    await callback.answer("Раздел в разработке", show_alert=True)