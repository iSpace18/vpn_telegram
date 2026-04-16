from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from sqlalchemy.ext.asyncio import AsyncSession
from bot.keyboards.main import main_menu_keyboard
from bot.services.referral_service import get_or_create_user
from bot.services.plan_service import ensure_default_plans

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, db_session: AsyncSession):
    args = message.text.split()
    referrer_code = None
    if len(args) > 1 and args[1].startswith("ref"):
        referrer_code = args[1][3:]

    # Убедимся, что тарифы созданы
    await ensure_default_plans(db_session)

    user = await get_or_create_user(
        db_session,
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
        referrer_code
    )

    await message.answer(
        f"👋 Добро пожаловать, {message.from_user.full_name}!\n"
        "Я бот для продажи доступа к VPN. Выберите действие в меню.",
        reply_markup=main_menu_keyboard()
    )

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()