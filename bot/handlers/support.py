from aiogram import Router, F
from aiogram.types import Message
from bot.keyboards.main import back_to_main_inline
from bot.config import settings

router = Router()

@router.message(F.text == "📞 Поддержка")
async def support_handler(message: Message):
    admin_usernames = []
    for admin_id in settings.ADMIN_IDS:
        # Получение username администраторов можно сделать через get_chat
        admin_usernames.append(f"@{admin_id}")  # упрощенно
    text = (
        "📞 <b>Поддержка</b>\n\n"
        "Если у вас возникли вопросы или проблемы, свяжитесь с администратором:\n"
        f"{', '.join(admin_usernames)}\n\n"
        "Опишите вашу проблему, приложите скриншоты."
    )
    await message.answer(text, parse_mode="HTML", reply_markup=back_to_main_inline())