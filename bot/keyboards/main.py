from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="💳 Купить подписку")],
        [KeyboardButton(text="👤 Мой профиль"), KeyboardButton(text="🤝 Реферальная система")],
        [KeyboardButton(text="🎁 Пробный период")],
        [KeyboardButton(text="❓ FAQ"), KeyboardButton(text="📞 Поддержка")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def plans_keyboard(plans) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for plan in plans:
        builder.button(
            text=f"{plan.name} - {plan.price_stars} ⭐",
            callback_data=f"buy_plan:{plan.id}"
        )
    builder.button(text="🔙 Назад", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()

def back_to_main_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")]]
    )