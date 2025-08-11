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
# Импортируем клавиатуры из нового файла
from src.utils.keyboards import get_main_menu_keyboard, get_register_keyboard
# Импортируем хелперы из нового файла
from src.utils.formatters import format_ton_wallet, format_card_number

from src.handlers.user_routers.user_main import command_start_handler

router = Router()

# --- Мой профиль ---
@router.callback_query(F.data == 'profile')
async def profile_handler(callback: CallbackQuery) -> None:
    user_data = db.get_user_data(callback.from_user.id)

    lang = user_data.get('language', 'ru')

    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'add_wallet'), callback_data="add_change_wallet")
    builder.button(text=translator.get_button(lang, 'top_up_wallet'), callback_data="top_up_wallet") # <-- ДОБАВЛЕНО
    builder.button(text=translator.get_button(lang, 'ref_link'), callback_data="ref_link")
    builder.button(text=translator.get_button(lang, 'back'), callback_data="back_to_main")
    builder.adjust(1)
    
    # Получаем плейсхолдер 'не добавлен' для текущего языка
    not_added_text = translator.get_message(lang, 'not_added')

    # Форматируем адрес кошелька и номер карты с помощью новых функций
    formatted_ton_wallet = format_ton_wallet(
        user_data.get('ton_wallet', not_added_text),
        placeholder=not_added_text
    )
    formatted_card_number = format_card_number(
        user_data.get('card_number', not_added_text),
        placeholder=not_added_text
    )

    profile_text = translator.get_message(
        lang, 
        'profile_text',
        balance=user_data.get('balance', '0'),
        ton_wallet=formatted_ton_wallet,
        card_number=formatted_card_number,
        deals_count=user_data.get('deals_count', 0)
    )

    await callback.message.edit_text(profile_text, reply_markup=builder.as_markup())
    await callback.answer()



# --- Добавление/изменение кошельков и карт ---
@router.callback_query(F.data == 'add_change_wallet')
async def add_wallet_card_handler(callback: CallbackQuery) -> None:
    user_data = db.get_user_data(callback.from_user.id)
    lang = user_data.get('language', 'ru')

    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'add_ton_wallet'), callback_data="add_ton_wallet")
    builder.button(text=translator.get_button(lang, 'add_card'), callback_data="add_card")
    builder.button(text=translator.get_button(lang, 'back'), callback_data="back_to_main")
    builder.adjust(1)
    
    await callback.message.edit_text(
        translator.get_message(lang, 'select_add_type'),
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data == 'add_ton_wallet')
async def add_ton_wallet_handler(callback: CallbackQuery, state: FSMContext) -> None:
    user_data = db.get_user_data(callback.from_user.id)
    lang = user_data.get('language', 'ru')
    
    # Создаем клавиатуру с кнопкой "Назад"
    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'back'), callback_data="add_change_wallet")
    builder.adjust(1)

    await callback.message.edit_text(
        translator.get_message(lang, 'add_ton_wallet'),
        reply_markup=builder.as_markup()
    )
    await state.set_state(WalletStates.waiting_for_wallet)
    await callback.answer()


@router.message(WalletStates.waiting_for_wallet, F.text)
async def process_ton_wallet(message: Message, state: FSMContext) -> None:
    user_data = db.get_user_data(message.from_user.id)
    lang = user_data.get('language', 'ru')
    wallet_address = message.text
    
    if not re.match(r'^[a-zA-Z0-9_-]{48}$', wallet_address):
        await message.answer(translator.get_message(lang, 'wallet_validation_error'))
        return
    
    db.update_ton_wallet(message.from_user.id, wallet_address)
    await state.clear()
    await message.answer(translator.get_message(lang, 'wallet_added_success'))
    await command_start_handler(message, state)


@router.callback_query(F.data == 'add_card')
async def add_card_handler(callback: CallbackQuery, state: FSMContext) -> None:
    user_data = db.get_user_data(callback.from_user.id)
    lang = user_data.get('language', 'ru')

    # Создаем клавиатуру с кнопкой "Назад"
    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'back'), callback_data="add_change_wallet")
    builder.adjust(1)

    await callback.message.edit_text(
        translator.get_message(lang, 'add_card'),
        reply_markup=builder.as_markup()
    )
    await state.set_state(CardStates.waiting_for_card)
    await callback.answer()


@router.message(CardStates.waiting_for_card, F.text)
async def process_card_number(message: Message, state: FSMContext) -> None:
    user_data = db.get_user_data(message.from_user.id)
    lang = user_data.get('language', 'ru')
    card_number = message.text.replace(' ', '')
    
    if not re.match(r'^\d{16}$', card_number):
        await message.answer(translator.get_message(lang, 'card_validation_error'))
        return

    db.update_card_number(message.from_user.id, card_number)
    await state.clear()
    await message.answer(translator.get_message(lang, 'card_added_success'))
    await command_start_handler(message, state)



# --- Логика пополнения кошелька ---
@router.callback_query(F.data == 'top_up_wallet')
async def top_up_wallet_handler(callback: CallbackQuery, state: FSMContext) -> None:
    user_data = db.get_user_data(callback.from_user.id)
    lang = user_data.get('language', 'ru')
    
    ton_wallet_address = "UQDoDzbmTF6UO6x9dAoKn_KvbINKptV6kHrCMqv3G4csblFh"
    
    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'confirm_top_up'), callback_data="confirm_top_up")
    builder.button(text=translator.get_button(lang, 'cancel_top_up'), callback_data="cancel_top_up")
    builder.adjust(2)
    
    text = translator.get_message(lang, 'top_up_wallet_text', ton_wallet_address=ton_wallet_address)
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await state.set_state(TopUpStates.waiting_for_confirmation)
    await callback.answer()
    
@router.callback_query(TopUpStates.waiting_for_confirmation, F.data == "confirm_top_up")
async def confirm_top_up_handler(callback: CallbackQuery, state: FSMContext) -> None:
    user_data = db.get_user_data(callback.from_user.id)
    lang = user_data.get('language', 'ru')
    
    final_confirmation_text = translator.get_message(lang, 'top_up_request_sent')
    
    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'back_to_main'), callback_data="back_to_main")
    builder.adjust(1)
    
    await callback.message.edit_text(final_confirmation_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await state.clear()
    await callback.answer()
    
@router.callback_query(TopUpStates.waiting_for_confirmation, F.data == "cancel_top_up")
async def cancel_top_up_handler(callback: CallbackQuery, state: FSMContext) -> None:
    user_data = db.get_user_data(callback.from_user.id)
    lang = user_data.get('language', 'ru')
    await callback.message.edit_text(translator.get_message(lang, 'top_up_canceled'))
    await state.clear()
    await command_start_handler(callback, state)


# --- Обработчики, требующие привязанного кошелька ---
@router.callback_query(F.data.in_({'ref_link'}))
async def handle_wallet_required_action(callback: CallbackQuery, state: FSMContext) -> None:
    user_data = db.get_user_data(callback.from_user.id)
    lang = user_data.get('language', 'ru')

    # Проверка наличия TON-кошелька
    if not user_data.get('ton_wallet'):
        builder = InlineKeyboardBuilder()
        builder.button(text=translator.get_button(lang, 'add_wallet'), callback_data="add_change_wallet")
        builder.adjust(1)
        await callback.message.edit_text(
            translator.get_message(lang, 'wallet_not_added_warning'),
            reply_markup=builder.as_markup()
        )
        await callback.answer()
        return

    # Новая логика для генерации реферальной ссылки
    bot_username = (await callback.bot.get_me()).username
    user_id = callback.from_user.id
    referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'back'), callback_data="back_to_main")
    builder.adjust(1)
    
    await callback.message.edit_text(
        translator.get_message(lang, 'ref_link_text', referral_link=html.code(referral_link)),
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()
