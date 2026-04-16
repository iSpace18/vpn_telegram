import uuid
from aiogram import Bot
from aiogram.types import LabeledPrice
from bot.models import Plan
from bot.config import settings

# ----- Telegram Stars -----
async def send_stars_invoice(
    bot: Bot,
    chat_id: int,
    plan: Plan,
    payload: str,
    photo_url: str | None = None
):
    prices = [LabeledPrice(label=plan.name, amount=plan.price_stars)]
    await bot.send_invoice(
        chat_id=chat_id,
        title=f"Подписка {plan.name}",
        description=plan.description or f"Доступ на {plan.duration_days} дней",
        payload=payload,
        provider_token="",          # Для Telegram Stars
        currency="XTR",
        prices=prices,
        start_parameter="vpn_subscription",
        photo_url=photo_url,
        need_name=False,
        need_phone_number=False,
        need_email=False,
        need_shipping_address=False,
        is_flexible=False,
    )

# ----- ЮKassa (опционально) -----
if settings.YOOKASSA_SHOP_ID and settings.YOOKASSA_SECRET_KEY:
    from yookassa import Configuration, Payment
    Configuration.account_id = settings.YOOKASSA_SHOP_ID
    Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

    async def create_yookassa_payment(amount_rub: float, description: str, return_url: str) -> tuple[str, str]:
        idempotence_key = str(uuid.uuid4())
        payment = Payment.create({
            "amount": {
                "value": f"{amount_rub:.2f}",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url
            },
            "capture": True,
            "description": description
        }, idempotence_key)
        return payment.id, payment.confirmation.confirmation_url

    async def check_yookassa_payment(payment_id: str) -> str:
        payment = Payment.find_one(payment_id)
        return payment.status
else:
    # Заглушки, чтобы избежать ошибок импорта
    async def create_yookassa_payment(amount_rub: float, description: str, return_url: str):
        raise NotImplementedError("ЮKassa не настроена")

    async def check_yookassa_payment(payment_id: str):
        raise NotImplementedError("ЮKassa не настроена")