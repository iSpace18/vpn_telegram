import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings
from bot.utils.logger import setup_logger
from bot.utils.db import engine
from bot.models import Base
from bot.middlewares.database import DBSessionMiddleware

from bot.handlers import start, payment, profile, referral, support, admin, faq

async def on_startup(bot: Bot):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await bot.set_my_commands([
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="admin", description="Админ-панель"),
    ])

async def main():
    setup_logger()
    logging.info("Starting bot...")

    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(DBSessionMiddleware())

    dp.include_router(start.router)
    dp.include_router(payment.router)
    dp.include_router(profile.router)
    dp.include_router(referral.router)
    dp.include_router(support.router)
    dp.include_router(admin.router)
    dp.include_router(faq.router)

    dp.startup.register(on_startup)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())