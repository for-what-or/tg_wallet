from aiogram import html
from aiogram.filters import BaseFilter, Command
from aiogram.types import Message
from aiogram import Router

from config import ADMINS_LIST

admin_router = Router()

class IsAdmin(BaseFilter):
    def __init__(self) -> None:
        self.admin_ids = ADMINS_LIST
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in self.admin_ids

"""@admin_router.message(IsAdmin(), Command('start'))
async def admin_start_handler(message: Message) -> None:
    await message.answer(f"Привет, администратор {html.bold(message.from_user.full_name)}!")"""

@admin_router.message(IsAdmin(), Command('admin'))
async def admin_handler(message: Message) -> None:
    await message.answer("Админ панель:")
