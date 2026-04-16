from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def admin_panel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="📢 Рассылка", callback_data="admin_broadcast")
    builder.button(text="🔧 Управление ключами", callback_data="admin_keys_menu")
    builder.button(text="📦 Управление тарифами", callback_data="admin_plans_menu")
    builder.button(text="🖥 Серверы", callback_data="admin_servers")
    builder.button(text="❌ Закрыть", callback_data="close_admin")
    builder.adjust(2)
    return builder.as_markup()

def admin_plans_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить тариф", callback_data="admin_plan_add")
    builder.button(text="❌ Удалить тариф", callback_data="admin_plan_delete")
    builder.button(text="👁 Скрыть/Показать", callback_data="admin_plan_toggle")
    builder.button(text="🔙 Назад", callback_data="back_to_admin")
    builder.adjust(1)
    return builder.as_markup()

def admin_keys_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔑 Показать ключи пользователя", callback_data="admin_keys_show")
    builder.button(text="🚫 Заблокировать ключ", callback_data="admin_keys_block")
    builder.button(text="✅ Разблокировать ключ", callback_data="admin_keys_unblock")
    builder.button(text="🗑 Удалить ключ", callback_data="admin_keys_delete")
    builder.button(text="🔙 Назад", callback_data="back_to_admin")
    builder.adjust(1)
    return builder.as_markup()

def back_to_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад в админ-панель", callback_data="back_to_admin")]]
    )