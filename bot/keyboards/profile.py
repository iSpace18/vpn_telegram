from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def profile_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔑 Мои ключи", callback_data="my_keys")
    builder.button(text="🔄 Продлить подписку", callback_data="renew_subscription")
    builder.button(text="🔙 Назад", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()