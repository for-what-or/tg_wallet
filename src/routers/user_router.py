from aiogram import F, Router, html
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.types.callback_query import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types

from src.database import db  # Импортируем нашу базу данных

user_router = Router()

@user_router.message(CommandStart())
@user_router.callback_query(F.data == 'back_to_main')
async def command_start_handler(update: types.Message | types.CallbackQuery) -> None:
    builder_start = InlineKeyboardBuilder()
    builder_start.button(text="👤 Мой профиль", callback_data="profile")
    builder_start.button(text="💼 Добавить/изменить кошелек", callback_data="add_change_wallet")
    builder_start.button(text="Создать сделку", callback_data="create_deal")
    builder_start.button(text="Реферальная ссылка", callback_data="ref_link")
    builder_start.button(text="🌍 Change language", callback_data="change_language")
    #builder_start.button(text="Еще кнопки", callback_data="more")
    builder_start.adjust(1)

    text = """
    ВСТАВИТЬ ИМЯ — Ваш надежный партнер в мире P2P-сделок

    🔒 Безопасность на первом месте
    Покупайте и продавайте что угодно — от Telegram-подарков и NFT до токенов и фиатных валют — быстро, удобно и без риска.

    💼 Почему выбирают нас:
    • Интуитивное управление кошельками
    • Прозрачная и выгодная реферальная программа

    📘 Пошаговая инструкция
    Ознакомьтесь с руководством, чтобы совершать сделки легко и уверенно: [Ссылка]

    Выберите нужный раздел 👇🏻
    """
    if isinstance(update, types.Message):
        await update.answer(text, reply_markup=builder_start.as_markup())
    else:
        await update.message.edit_text(text, reply_markup=builder_start.as_markup())

# Мой профиль
@user_router.callback_query(F.data == 'profile')
async def profile_handler(callback: CallbackQuery) -> None:
    builder = InlineKeyboardBuilder()
    builder.button(text="Перевести", callback_data="transfer")
    builder.button(text="Вывести", callback_data="withdraw")
    builder.button(text="⬅️ Назад", callback_data="back_to_main")
    builder.adjust(1)

    profile_text = f"""
👤 {callback.from_user.full_name}

Баланс TON: {'0'}

💼 TON-кошелек: {'Не добавлен'}
💳 Карта: {'Не добавлена'}
🤝 Совершенные сделки: 0
    """
    await callback.message.edit_text(profile_text, reply_markup=builder.as_markup())
    await callback.answer()

# Добавление кошелька/карты
@user_router.callback_query(F.data == 'add_change_wallet')
async def add_wallet_card_handler(callback: CallbackQuery) -> None:
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 TON-кошелек", callback_data="add_wallet_card")
    builder.button(text="💳 Карта", callback_data="add_card")
    builder.button(text="⬅️ Назад", callback_data="back_to_main")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "💼 Выберите что хотите добавить:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

# Добавление TON-кошелька
@user_router.callback_query(F.data == 'add_wallet_card')
async def add_ton_wallet_handler(callback: CallbackQuery) -> None:
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="add_change_wallet")
    
    await callback.message.edit_text(
        "Добавьте ваш TON-кошелек\n\n"
        "Пожалуйста, отправьте адрес вашего кошелька.",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@user_router.callback_query(F.data == 'add_card')
async def add_card_handler(callback: CallbackQuery) -> None:
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="add_change_wallet")
    
    await callback.message.edit_text(
        "💳 Добавьте вашу банковскую карту:\n\n"
        "Пожалуйста, отправьте номер вашей карты (16 цифр).\n",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

# Смена языка
@user_router.callback_query(F.data == 'change_language')
async def language_handler(callback: CallbackQuery) -> None:
    builder = InlineKeyboardBuilder()
    builder.button(text="English", callback_data="set_english")
    builder.button(text="Русский", callback_data="set_russian")
    builder.button(text="⬅️ Назад", callback_data="back_to_main")
    builder.adjust(2, 1)
    
    await callback.message.edit_text(
        "🌍 Choose your language:\n"
        "Выберите язык:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@user_router.callback_query(F.data == 'back_to_main')
async def back_handler(callback: CallbackQuery) -> None:
    await command_start_handler(callback.message)
    await callback.answer()

@user_router.message(Command("id"))
async def command_help_handler(message: Message) -> None:
    user_id = message.from_user.id
    await message.answer(
        f"Ваш ID:\n"
        f"<code>{user_id}</code>\n\n"
        "Нажмите на ID, чтобы скопировать",
        parse_mode="HTML"
    )






@user_router.callback_query(F.data == 'more')
@user_router.message(Command("more"))
async def more_buttons(update: types.Message | types.CallbackQuery):
    builder_more = InlineKeyboardBuilder()
    builder_more.button(text="Тон кошелек", callback_data="ton_wallet")
    builder_more.button(text="Карта", callback_data="card")
    builder_more.adjust(1)
    
    if isinstance(update, types.Message):
        await update.answer('Больше кнопок.', reply_markup=builder_more.as_markup())
    else:
        await update.answer()
        await update.message.answer('Больше кнопок.', reply_markup=builder_more.as_markup())

'''
@user_router.callback_query(F.data == 'add_change_wallet')
async def add_change_wallet_handler(callback_query: CallbackQuery) -> None:
    await callback_query.answer()
    await callback_query.message.answer("Добавьте ваш Тон кошелек")


@user_router.callback_query(F.data == 'create_deal')

@user_router.callback_query(F.data == 'ref_link')


@user_router.callback_query(F.data == 'ton_wallet')

@user_router.callback_query(F.data == 'card')'''