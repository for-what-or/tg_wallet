from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault

# src/bot_commands.py

async def set_bot_commands(bot: Bot):
    """
    Устанавливает список команд для бота.
    Эти команды будут отображаться в меню при нажатии на /
    """
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Показать список команд и их описание"),
        BotCommand(command="balance", description="Показать/изменить баланс (например, /balance +100)"),
        BotCommand(command="id", description="Показать свой ID"),
        BotCommand(command="addvip", description="Выдать разрешение на пополнение (только для админов)"),
        BotCommand(command="rmvip", description="Забрать разрешение на пополнение (только для админов)")
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
