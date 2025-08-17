from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault

# src/bot_commands.py

async def set_bot_commands(bot: Bot):
    """
    Устанавливает список команд для бота.
    Эти команды будут отображаться в меню при нажатии на /
    """
    commands = []
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
