import re
from aiogram import F, Router, html
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram import types

from src.locales import translator
from src.database import db
from src.states import *
from src.handlers.user_routers.user_main import command_start_handler

router = Router()


# --- P2P Обмен ---
# Обработчик для кнопки "P2P Обмен"
@router.callback_query(F.data == 'p2p')
async def p2p_menu_handler(callback: CallbackQuery) -> None:
    user_data = db.get_user_data(callback.from_user.id)
    lang = user_data.get('language', 'ru')
    
    p2p_pairs = db.get_all_p2p_pairs() # Получаем пары из БД
    
    builder = InlineKeyboardBuilder()
    if p2p_pairs:
        for pair in p2p_pairs:
            # Создаем кнопки динамически
            builder.button(text=pair.replace('_', ' <> '), callback_data=f"p2p_{pair}")
    
    builder.button(text=translator.get_button(lang, 'back'), callback_data="back_to_main")
    builder.adjust(1)
    
    await callback.message.edit_text(
        translator.get_message(lang, 'p2p_description'),
        reply_markup=builder.as_markup()
    )
    await callback.answer()

# УДАЛИТЕ ЭТОТ СЛОВАРЬ:
# mock_traders_data = { ... }

# Обработчик для выбора валютной пары в P2P
@router.callback_query(F.data.startswith('p2p_'))
async def p2p_select_currency_handler(callback: CallbackQuery) -> None:
    user_data = db.get_user_data(callback.from_user.id)
    lang = user_data.get('language', 'ru')
    
    currency_pair = callback.data.split('_', 1)[1] # Например, 'TON_RUB'
    
    # Получаем листинги из БД вместо mock-данных
    traders_list = db.get_p2p_listings(currency_pair)

    # Формируем текст с описанием сделок
    traders_text = translator.get_message(lang, 'p2p_traders_header', currency_pair=currency_pair) + "\n\n"
    if not traders_list:
        traders_text = translator.get_message(lang, 'no_active_traders')
    else:
        for trader in traders_list:
            traders_text += translator.get_message(
                lang,
                'p2p_trader_format',
                nickname=trader['nickname'],
                currency_pair=currency_pair.replace('_', ' > '),
                price=trader['price'],
                limit=trader['limit'],
                action=trader['action'] # Действие (покупка/продажа)
            ) + "\n"

    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'back'), callback_data="p2p")
    builder.adjust(1)
    
    await callback.message.edit_text(traders_text, reply_markup=builder.as_markup())
    await callback.answer()
