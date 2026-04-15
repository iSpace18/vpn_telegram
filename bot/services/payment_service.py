from aiogram import Bot
from aiogram.types import LabeledPrice
from bot.models import Plan

async def send_stars_invoice(
    bot: Bot,
    chat_id: int,
    plan: Plan,
    payload: str,
    photo_url: str | None = None
):
    """
    Отправляет инвойс для оплаты Telegram Stars.
    """
    prices = [LabeledPrice(label=plan.name, amount=plan.price_stars)]
    await bot.send_invoice(
        chat_id=chat_id,
        title=f"Подписка {plan.name}",
        description=plan.description or f"Доступ на {plan.duration_days} дней",
        payload=payload,
        provider_token="",  # Для Telegram Stars
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