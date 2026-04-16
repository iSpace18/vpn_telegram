from aiogram import Router, F
from aiogram.types import Message
from bot.keyboards.main import back_to_main_inline

router = Router()

@router.message(F.text == "❓ FAQ")
async def show_faq(message: Message):
    text = (
        "📌 <b>Часто задаваемые вопросы</b>\n\n"
        "❓ <b>Как подключить VPN?</b>\n"
        "Скопируйте ссылку из полученного ключа и импортируйте в приложение (v2rayNG, Streisand, FoxRay).\n\n"
        "❓ <b>Какие протоколы используются?</b>\n"
        "VLESS + Reality (маскировка трафика).\n\n"
        "❓ <b>Политика возврата</b>\n"
        "Возврат средств не предусмотрен. Вы можете протестировать пробный период.\n\n"
        "❓ <b>Как продлить подписку?</b>\n"
        "В разделе «Мой профиль» → «Продлить подписку» (функция в разработке).\n\n"
        "❓ <b>Сколько устройств можно подключить?</b>\n"
        "Один ключ — одно устройство. Для нескольких устройств приобретите дополнительные ключи."
    )
    await message.answer(text, parse_mode="HTML", reply_markup=back_to_main_inline())