from aiogram import types
from aiogram.exceptions import TelegramBadRequest

async def delete_old_message(message: types.Message) -> None:
    """
    Безопасное удаление старого сообщения, чтобы не загромождать чат.
    """
    try:
        await message.delete()
    except TelegramBadRequest as e:
        # Игнорируем ошибку, если сообщение уже удалено
        # или если бот не имеет прав на удаление
        print(f"Failed to delete message: {e}")