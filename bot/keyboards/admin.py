from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def admin_panel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="📢 Рассылка", callback_data="admin_broadcast")
    builder.button(text="🔧 Управление ключами", callback_data="admin_keys")
    builder.button(text="🖥 Серверы", callback_data="admin_servers")
    builder.button(text="❌ Закрыть", callback_data="close_admin")
    builder.adjust(2)
    return builder.as_markup()