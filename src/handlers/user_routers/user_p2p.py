import re
import html 
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram import types

from src.locales import translator
from src.database import db
from src.states import *
from src.handlers.user_routers.user_main import command_start_handler
from src.config import * # Импортируем все переменные из модуля config

router = Router()

# --- P2P Обмен ---
# Обработчик для кнопки "P2P Обмен"
@router.callback_query(F.data == 'p2p')
async def p2p_menu_handler(callback: CallbackQuery) -> None:
    user_data = db.get_user_data(callback.from_user.id)
    lang = user_data.get('language', 'ru')
    if not user_data.get('ton_wallet'):
        builder = InlineKeyboardBuilder()
        builder.button(text=translator.get_button(lang, 'add_wallet'), callback_data="add_change_wallet")
        builder.adjust(1)
        await callback.answer(translator.get_message(lang, 'wallet_not_added_warning'), show_alert=True)
        return
    
    p2p_pairs = db.get_all_p2p_pairs() # Получаем пары из БД
    
    builder = InlineKeyboardBuilder()
    if p2p_pairs:
        for pair in p2p_pairs:
            # Создаем кнопки динамически
            builder.button(text=pair.replace('_', ' <> '), callback_data=f"p2p_{pair}")
    
    builder.button(text=translator.get_button(lang, 'back'), callback_data="back_to_main")
    builder.adjust(1)
    
    # Используем путь к файлу, импортированный напрямую
    photo = FSInputFile(PHOTO_PATH)
    await callback.message.edit_media(
        media=InputMediaPhoto(media=photo, caption=translator.get_message(lang, 'p2p_description'), parse_mode="HTML"),
        reply_markup=builder.as_markup()
    )
    await callback.answer()

# Обработчик для выбора валютной пары в P2P
@router.callback_query(F.data.startswith('p2p_') & ~F.data.startswith('p2p_trader_select:'))
async def p2p_select_currency_handler(callback: CallbackQuery) -> None:
    user_data = db.get_user_data(callback.from_user.id)
    lang = user_data.get('language', 'ru')
    
    currency_pair = callback.data.split('_', 1)[1] # Например, 'TON_RUB'
    
    # Получаем листинги из БД
    traders_list = db.get_p2p_listings(currency_pair)

    builder = InlineKeyboardBuilder()

    # Формируем только заголовок текста
    escaped_currency_pair = html.escape(currency_pair.replace('_', ' <> '))
    traders_text = translator.get_message(lang, 'p2p_traders_header', currency_pair=escaped_currency_pair) + "\n\n"
    
    if not traders_list:
        traders_text += translator.get_message(lang, 'no_active_traders')
    else:
        for trader in traders_list:
            # Создаем кнопку для каждого трейдера
            button_text = translator.get_message(
                lang,
                'p2p_trader_format',
                nickname=trader['nickname'],
                currency_pair=currency_pair.replace('_', ' > '),
                price=trader['price'],
                limit=trader['limit'],
                action=trader['action']
            )
            # Экранируем текст для кнопки, чтобы избежать ошибок с разметкой
            escaped_button_text = html.escape(button_text)
            builder.button(
                text=escaped_button_text,
                callback_data=f"p2p_trader_select:{trader['id']}"
            )
        builder.adjust(1) # Располагаем кнопки по одной в ряд

    builder.button(text=translator.get_button(lang, 'back'), callback_data="p2p")
    builder.adjust(1)
    
    # Используем путь к файлу, импортированный напрямую
    photo = FSInputFile(PHOTO_PATH)
    await callback.message.edit_media(
        media=InputMediaPhoto(media=photo, caption=traders_text, parse_mode="HTML"),
        reply_markup=builder.as_markup()
    )
    await callback.answer()

# Новый обработчик для выбора конкретного трейдера
@router.callback_query(F.data.startswith('p2p_trader_select:'))
async def p2p_select_trader_handler(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)
    lang = user_data.get('language', 'ru')
    
    response_text = translator.get_message(lang, 'not_enough_balance')
    
    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'back_to_main'), callback_data="back_to_main")
    
    # Используем путь к файлу, импортированный напрямую
    photo = FSInputFile(PHOTO_PATH)
    await callback.message.edit_media(
        media=InputMediaPhoto(media=photo, caption=response_text, parse_mode="HTML"),
        reply_markup=builder.as_markup()
    )
    await callback.answer(response_text, parse_mode="HTML", show_alert=True)


# Обработчик для подтверждения продажи
@router.callback_query(F.data.startswith('p2p_sell:'))
async def p2p_sell_handler(callback: CallbackQuery, state: FSMContext) -> None:
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)
    lang = user_data.get('language', 'ru')

    trader_id = int(callback.data.split(':')[1])
    trader_listing = db.get_p2p_listing_by_id(trader_id)
    
    if not trader_listing:
        await callback.message.edit_text(translator.get_message(lang, 'trader_not_found'))
        await callback.answer()
        return

    currency_to_sell = trader_listing['currency_pair'].split('_')[0]
    amount_to_sell = min(user_data.get(currency_to_sell, 0), trader_listing['limit'])
    
    if user_data.get(currency_to_sell, 0) < amount_to_sell:
        response_text = translator.get_message(lang, 'not_enough_balance')
        builder = InlineKeyboardBuilder()
        builder.button(text=translator.get_button(lang, 'back'), callback_data="back_to_main")
        
        # Используем путь к файлу, импортированный напрямую
        photo = FSInputFile(PHOTO_PATH)
        await callback.message.edit_media(
            media=InputMediaPhoto(media=photo, caption=response_text, parse_mode="HTML"),
            reply_markup=builder.as_markup()
        )
        await callback.answer()
        return

    db.update_balance(user_id, currency_to_sell, user_data[currency_to_sell] - amount_to_sell)

    response_text = translator.get_message(lang, 'funds_transfer_notice')
    
    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'back_to_main'), callback_data="back_to_main")
    
    # Используем путь к файлу, импортированный напрямую
    photo = FSInputFile(PHOTO_PATH)
    await callback.message.edit_media(
        media=InputMediaPhoto(media=photo, caption=response_text, parse_mode="HTML"),
        reply_markup=builder.as_markup()
    )
    await callback.answer()
