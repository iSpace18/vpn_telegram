import uuid
from yookassa import Configuration, Payment
from bot.config import settings

if settings.YOOKASSA_SHOP_ID and settings.YOOKASSA_SECRET_KEY:
    Configuration.account_id = settings.YOOKASSA_SHOP_ID
    Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

async def create_yookassa_payment(amount_rub: float, description: str, return_url: str) -> tuple[str, str]:
    """
    Создаёт платёж в ЮKassa.
    Возвращает (payment_id, confirmation_url)
    """
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
    """Возвращает статус платежа: pending, succeeded, canceled"""
    payment = Payment.find_one(payment_id)
    return payment.status