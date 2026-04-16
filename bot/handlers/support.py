from aiogram import Router, F
from aiogram.types import Message
from bot.keyboards.main import back_to_main_inline
from bot.config import settings

router = Router()

@router.message(F.text == "📞 Поддержка")
async def support_handler(message: Message):
    admin_id = settings.ADMIN_IDS[0]
    text = (
        "📞 <b>Поддержка</b>\n\n"
        f"Свяжитесь с администратором: <a href='tg://user?id={admin_id}'>Написать</a>\n\n"
        "Опишите вашу проблему, приложите скриншоты."
    )
    await message.answer(text, parse_mode="HTML", reply_markup=back_to_main_inline())