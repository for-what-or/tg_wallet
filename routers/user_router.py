import os
import logging

from aiogram import F, Router, html
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

user_router = Router()

@user_router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    text = """
    ВСТАВИТЬ ИМЯ — Ваш надежный партнер в мире P2P-сделок

    🔒 Безопасность на первом месте
    Покупайте и продавайте что угодно — от Telegram-подарков и NFT до токенов и фиатных валют — быстро, удобно и без риска.

    💼 Почему выбирают нас:
    • Интуитивное управление кошельками
    • Прозрачная и выгодная реферальная программа

    📘 Пошаговая инструкция
    Ознакомьтесь с руководством, чтобы совершать сделки легко и уверенно: [Ссылка]
    """
    await message.answer(text)

@user_router.message(Command("id"))
async def command_help_handler(message: Message) -> None:
    await message.answer(f"ID: {message.from_user.id}")

@user_router.message()
async def other_handler(message: Message) -> None:
    await message.answer(message.text)
