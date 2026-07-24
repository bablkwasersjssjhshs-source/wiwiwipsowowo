from aiogram import Bot, Dispatcher
from config import TOKEN
import asyncio
from routers.handlers import router

dp = Dispatcher()

async def main():
    bot = Bot(TOKEN)
    dp.include_router(router)  # Убрали await, так как это не асинхронная функция
    await dp.start_polling(bot)

asyncio.run(main())