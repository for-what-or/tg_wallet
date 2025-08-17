from src.handlers import routers
from src.config import bot, dp
from aiogram.methods import DeleteWebhook

# Импортируем функцию установки команд

async def start_bot() -> None:
    # Удаление вебхука и ожидающих обновлений
    await bot(DeleteWebhook(drop_pending_updates=True))
    
    # Регистрация всех роутеров
    for router in routers:
        dp.include_router(router)
        
    # Запуск бота
    await dp.start_polling(bot)
