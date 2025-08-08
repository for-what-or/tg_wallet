from routers.admin_router import admin_router
from config import ADMINS_LIST, bot, dp
from routers.user_router import user_router
from config import on_error
from aiogram.methods import DeleteWebhook

async def start_bot() -> None:
    await bot(DeleteWebhook(drop_pending_updates=True))
    dp.include_routers(admin_router, user_router)
    dp.errors.register(on_error)
    await dp.start_polling(bot)