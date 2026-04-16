import uuid
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from bot.models import User, Plan, VPNKey, Payment, PaymentMethod, TrialUsage
from bot.services.vpn_service import VPNService
from bot.services.payment_service import send_stars_invoice, create_yookassa_payment, check_yookassa_payment
from bot.keyboards.main import plans_keyboard, back_to_main_inline
from bot.services.plan_service import ensure_default_plans
from bot.config import settings

router = Router()
vpn_service = VPNService()

@router.message(F.text == "💳 Купить подписку")
async def show_plans(message: Message, db_session: AsyncSession):
    await ensure_default_plans(db_session)
    plans = (await db_session.execute(select(Plan).where(Plan.is_active == True))).scalars().all()
    if not plans:
        await message.answer("Нет доступных тарифов.")
        return
    await message.answer("📦 Выберите тарифный план:", reply_markup=plans_keyboard(plans))

@router.callback_query(F.data.startswith("buy_plan:"))
async def process_buy_plan(callback: CallbackQuery, db_session: AsyncSession):
    plan_id = int(callback.data.split(":")[1])
    plan = await db_session.get(Plan, plan_id)
    if not plan:
        await callback.answer("Тариф не найден.", show_alert=True)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Оплатить Telegram Stars", callback_data=f"pay_stars:{plan_id}")],
    ])
    if settings.YOOKASSA_SHOP_ID and settings.YOOKASSA_SECRET_KEY and plan.price_rub:
        kb.inline_keyboard.append(
            [InlineKeyboardButton(text="💳 Оплатить картой (ЮKassa)", callback_data=f"pay_yookassa:{plan_id}")]
        )
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_plans")])

    await callback.message.edit_text(
        f"💳 Вы выбрали тариф «{plan.name}».\n"
        f"Стоимость: {plan.price_stars} ⭐" + (f" или {plan.price_rub} ₽" if plan.price_rub else ""),
        reply_markup=kb
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_plans")
async def back_to_plans(callback: CallbackQuery, db_session: AsyncSession):
    plans = (await db_session.execute(select(Plan).where(Plan.is_active == True))).scalars().all()
    await callback.message.edit_text("📦 Выберите тарифный план:", reply_markup=plans_keyboard(plans))
    await callback.answer()

@router.callback_query(F.data.startswith("pay_stars:"))
async def pay_stars(callback: CallbackQuery, db_session: AsyncSession, bot: Bot):
    plan_id = int(callback.data.split(":")[1])
    plan = await db_session.get(Plan, plan_id)
    user = await db_session.scalar(select(User).where(User.telegram_id == callback.from_user.id))
    payload = f"plan_{plan.id}_{user.telegram_id}_{uuid.uuid4()}"
    await send_stars_invoice(bot, callback.message.chat.id, plan, payload)
    await callback.answer()

@router.callback_query(F.data.startswith("pay_yookassa:"))
async def pay_yookassa(callback: CallbackQuery, db_session: AsyncSession, bot: Bot):
    plan_id = int(callback.data.split(":")[1])
    plan = await db_session.get(Plan, plan_id)
    user = await db_session.scalar(select(User).where(User.telegram_id == callback.from_user.id))

    payment_id, confirmation_url = await create_yookassa_payment(
        amount_rub=plan.price_rub,
        description=f"Подписка {plan.name}",
        return_url=f"https://t.me/{(await bot.get_me()).username}"
    )
    payment = Payment(
        user_id=user.id,
        plan_id=plan.id,
        amount=plan.price_rub,
        method=PaymentMethod.YOOKASSA,
        payment_id=payment_id
    )
    db_session.add(payment)
    await db_session.commit()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_yookassa:{payment_id}")],
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="back_to_plans")]
    ])
    await callback.message.edit_text(
        f"💳 Для оплаты перейдите по ссылке:\n{confirmation_url}\n\nПосле оплаты нажмите «Проверить оплату».",
        reply_markup=kb
    )
    await callback.answer()

@router.callback_query(F.data.startswith("check_yookassa:"))
async def check_yookassa(callback: CallbackQuery, db_session: AsyncSession, bot: Bot):
    payment_id = callback.data.split(":")[1]
    payment = await db_session.scalar(select(Payment).where(Payment.payment_id == payment_id))
    if not payment:
        await callback.answer("Платёж не найден", show_alert=True)
        return

    status = await check_yookassa_payment(payment_id)
    if status == "succeeded" and payment.status != "succeeded":
        payment.status = "succeeded"
        payment.paid_at = datetime.utcnow()
        await db_session.commit()
        await grant_vpn_key(callback.message, db_session, payment.user_id, payment.plan_id)
    elif status == "pending":
        await callback.answer("Оплата ещё не прошла", show_alert=True)
    else:
        await callback.answer("Оплата не удалась или отменена", show_alert=True)
    await callback.answer()

async def grant_vpn_key(message: Message, db_session: AsyncSession, user_id: int, plan_id: int):
    user = await db_session.get(User, user_id)
    plan = await db_session.get(Plan, plan_id)
    username = f"u{user.telegram_id}_{uuid.uuid4().hex[:8]}"
    vpn_data = await vpn_service.create_user(
        username=username,
        expiry_days=plan.duration_days,
        traffic_limit_gb=plan.traffic_limit_gb
    )
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
        f"📅 Действует до: {vpn_data['expiry_date'].strftime('%d.%m.%Y')}",
        parse_mode="HTML"
    )

@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@router.message(F.successful_payment)
async def successful_payment(message: Message, db_session: AsyncSession):
    payload = message.successful_payment.invoice_payload
    parts = payload.split("_")
    if len(parts) < 3 or parts[0] != "plan":
        return
    plan_id = int(parts[1])
    telegram_id = int(parts[2])
    user = await db_session.scalar(select(User).where(User.telegram_id == telegram_id))
    await grant_vpn_key(message, db_session, user.id, plan_id)

@router.message(F.text == "🎁 Пробный период")
async def trial_period(message: Message, db_session: AsyncSession):
    user = await db_session.scalar(select(User).where(User.telegram_id == message.from_user.id))
    if not user:
        await message.answer("❌ Пользователь не найден. Введите /start")
        return
    if user.trial_used:
        await message.answer("❌ Вы уже использовали пробный период.")
        return

    existing = await db_session.scalar(
        select(VPNKey).where(VPNKey.user_id == user.id, VPNKey.plan_id.is_(None), VPNKey.is_active == True)
    )
    if existing:
        await message.answer("❌ У вас уже есть активный пробный ключ.")
        return

    username = f"trial_{user.telegram_id}_{uuid.uuid4().hex[:6]}"
    try:
        vpn_data = await vpn_service.create_user(
            username=username,
            expiry_days=settings.TRIAL_DAYS,
            traffic_limit_gb=None
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка создания пробного ключа: {e}")
        return

    vpn_key = VPNKey(
        user_id=user.id,
        plan_id=None,
        key_uuid=vpn_data["uuid"],
        key_data=vpn_data["subscription_url"],
        expiry_date=vpn_data["expiry_date"],
        is_active=True
    )
    db_session.add(vpn_key)
    user.trial_used = True
    trial_usage = TrialUsage(user_id=user.id)
    db_session.add(trial_usage)
    await db_session.commit()

    await message.answer(
        f"✅ Пробный ключ на {settings.TRIAL_DAYS} дн. активирован!\n\n"
        f"🔑 Ссылка для подключения:\n<code>{vpn_data['subscription_url']}</code>",
        parse_mode="HTML"
    )