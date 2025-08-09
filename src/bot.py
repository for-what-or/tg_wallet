from src.routers import routers
from src.config import bot, dp
from aiogram.methods import DeleteWebhook

async def start_bot() -> None:
    await bot(DeleteWebhook(drop_pending_updates=True))
    for router in routers:
        dp.include_router(router)
    await dp.start_polling(bot)