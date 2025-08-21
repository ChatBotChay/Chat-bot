import os
import asyncio

from aiogram import Bot, Dispatcher
from bot.midlewares import UserMiddleware

from bot.handlers.admin_handlers import admin_router
from bot.handlers.super_admin_handlers import super_admin_router
from bot.handlers.waiter_handlers import waiter_router
from config import settings

bot = Bot(token=settings.BOT_TOKEN)

dp = Dispatcher()
dp.message.middleware(UserMiddleware())
dp.callback_query.middleware(UserMiddleware())

dp.include_router(waiter_router)
dp.include_router(admin_router)
dp.include_router(super_admin_router)



async def main():
    print("Бот запущен!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())