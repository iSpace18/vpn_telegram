import uuid
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.models import User, Plan, VPNKey
from bot.services.vpn_service import VPNService
from bot.services.payment_service import send_stars_invoice
from bot.keyboards.main import plans_keyboard, back_to_main_inline
from bot.config import settings

router = Router()
vpn_service = VPNService()

@router.message(F.text == "💳 Купить подписку")
async def show_plans(message: Message, db_session: AsyncSession):
    plans = (await db_session.execute(select(Plan).where(Plan.is_active == True))).scalars().all()
    if not plans:
        await message.answer("Нет доступных тарифов.")
        return
    await message.answer(
        "📦 Выберите тарифный план:",
        reply_markup=plans_keyboard(plans)
    )

@router.callback_query(F.data.startswith("buy_plan:"))
async def process_buy_plan(callback: CallbackQuery, db_session: AsyncSession, bot: Bot):
    plan_id = int(callback.data.split(":")[1])
    plan = await db_session.get(Plan, plan_id)
    if not plan:
        await callback.answer("Тариф не найден.", show_alert=True)
        return
    
    user = await db_session.scalar(select(User).where(User.telegram_id == callback.from_user.id))
    if not user:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return
    
    # Генерируем уникальный payload для инвойса
    payload = f"plan_{plan.id}_{user.telegram_id}_{uuid.uuid4()}"
    await send_stars_invoice(bot, callback.message.chat.id, plan, payload)
    await callback.answer()

@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    # Подтверждаем возможность оплаты
    await pre_checkout_query.answer(ok=True)

@router.message(F.successful_payment)
async def successful_payment(message: Message, db_session: AsyncSession, bot: Bot):
    payment = message.successful_payment
    payload = payment.invoice_payload  # формат: plan_{plan_id}_{telegram_id}_{uuid}
    
    parts = payload.split("_")
    if len(parts) < 3 or parts[0] != "plan":
        await message.answer("Ошибка обработки платежа. Обратитесь в поддержку.")
        return
    
    plan_id = int(parts[1])
    telegram_id = int(parts[2])
    
    plan = await db_session.get(Plan, plan_id)
    user = await db_session.scalar(select(User).where(User.telegram_id == telegram_id))
    
    if not plan or not user:
        await message.answer("Ошибка: тариф или пользователь не найдены.")
        return
    
    # Создаем VPN пользователя
    username = f"u{user.telegram_id}_{uuid.uuid4().hex[:8]}"
    try:
        vpn_data = await vpn_service.create_user(
            username=username,
            expiry_days=plan.duration_days,
            traffic_limit_gb=plan.traffic_limit_gb
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка создания VPN-пользователя: {e}")
        # Здесь нужно сделать возврат средств? В Telegram Stars возврат сложен.
        return
    
    # Сохраняем ключ в БД
    vpn_key = VPNKey(
        user_id=user.id,
        plan_id=plan.id,
        key_uuid=vpn_data["uuid"],
        key_data=vpn_data["subscription_url"],
        expiry_date=vpn_data["expiry_date"],
    )
    db_session.add(vpn_key)
    await db_session.commit()
    
    await message.answer(
        f"✅ Оплата прошла успешно!\n\n"
        f"🔑 Ваш ключ доступа:\n<code>{vpn_data['subscription_url']}</code>\n\n"
        f"📅 Действует до: {vpn_data['expiry_date'].strftime('%d.%m.%Y')}\n\n"
        f"Инструкция по подключению в разделе FAQ.",
        parse_mode="HTML"
    )

@router.message(F.text == "❓ FAQ")
async def show_faq(message: Message):
    # Здесь можно вывести инлайн-кнопки с вопросами
    from bot.keyboards.main import back_to_main_inline
    faq_text = (
        "📌 <b>Часто задаваемые вопросы</b>\n\n"
        "❓ <b>Как подключить VPN?</b>\n"
        "Скопируйте ссылку из ключа и импортируйте в приложение (например, v2rayNG, Streisand, FoxRay).\n\n"
        "❓ <b>Какие протоколы?</b>\n"
        "VLESS + Reality (по умолчанию).\n\n"
        "❓ <b>Политика возврата</b>\n"
        "Возврат средств не предусмотрен. Вы можете протестировать пробный период.\n\n"
        "❓ <b>Как продлить подписку?</b>\n"
        "В разделе «Мой профиль» → «Продлить подписку»."
    )
    await message.answer(faq_text, parse_mode="HTML", reply_markup=back_to_main_inline())