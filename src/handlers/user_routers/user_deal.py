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

@router.callback_query(F.data.in_({'create_deal'}))
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
    
    user_data = db.get_user_data(callback.from_user.id)
    lang = user_data.get('language', 'ru')
    
    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'add_ton_wallet'), callback_data="add_recipient_ton_wallet")
    builder.button(text=translator.get_button(lang, 'add_card'), callback_data="add_recipient_card")
    builder.button(text=translator.get_button(lang, 'back'), callback_data="back_to_main")
    builder.adjust(1)

    await callback.message.edit_text(
        translator.get_message(lang, 'p2p_enter_recipient_type'),
        reply_markup=builder.as_markup()
    )
    await state.set_state(P2PStates.waiting_for_recipient_type)
    await callback.answer()


@router.callback_query(P2PStates.waiting_for_recipient_type, F.data == "add_recipient_ton_wallet")
async def add_recipient_ton_wallet_handler(callback: CallbackQuery, state: FSMContext) -> None:
    user_data = db.get_user_data(callback.from_user.id)
    lang = user_data.get('language', 'ru')

    # Создаем клавиатуру с кнопкой "Назад", которая возвращает на экран выбора типа получателя
    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'back'), callback_data="create_deal")
    builder.adjust(1)

    await callback.message.edit_text(
        translator.get_message(lang, 'p2p_enter_recipient_wallet'),
        reply_markup=builder.as_markup()
    )
    await state.set_state(P2PStates.waiting_for_recipient_wallet)
    await state.update_data(recipient_type='ton_wallet')
    await callback.answer()

@router.callback_query(P2PStates.waiting_for_recipient_type, F.data == "add_recipient_card")
async def add_recipient_card_handler(callback: CallbackQuery, state: FSMContext) -> None:
    user_data = db.get_user_data(callback.from_user.id)
    lang = user_data.get('language', 'ru')
    
    # Создаем клавиатуру с кнопкой "Назад", которая возвращает на экран выбора типа получателя
    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'back'), callback_data="create_deal")
    builder.adjust(1)

    await callback.message.edit_text(
        translator.get_message(lang, 'p2p_enter_recipient_card'),
        reply_markup=builder.as_markup()
    )
    await state.set_state(P2PStates.waiting_for_recipient_card)
    await state.update_data(recipient_type='card')
    await callback.answer()

@router.message(P2PStates.waiting_for_recipient_wallet, F.text)
async def process_recipient_ton_wallet(message: Message, state: FSMContext) -> None:
    user_data = db.get_user_data(message.from_user.id)
    lang = user_data.get('language', 'ru')
    wallet_address = message.text
    
    if not re.match(r'^[a-zA-Z0-9_-]{48}$', wallet_address):
        await message.answer(translator.get_message(lang, 'wallet_validation_error'))
        return
    
    await state.update_data(recipient_address=wallet_address)
    await message.answer(translator.get_message(lang, 'p2p_wallet_added_success'))
    
    # --- ИЗМЕНЕНИЕ ---
    # Теперь запрашиваем сумму в TON
    await message.answer(translator.get_message(lang, 'p2p_enter_ton_amount'))
    # --- /ИЗМЕНЕНИЕ ---
    
    await state.set_state(P2PStates.waiting_for_amount)

@router.message(P2PStates.waiting_for_recipient_card, F.text)
async def process_recipient_card(message: Message, state: FSMContext) -> None:
    user_data = db.get_user_data(message.from_user.id)
    lang = user_data.get('language', 'ru')
    card_number = message.text.replace(' ', '')
    
    if not re.match(r'^\d{16}$', card_number):
        await message.answer(translator.get_message(lang, 'card_validation_error'))
        return

    await state.update_data(recipient_address=card_number)
    await message.answer(translator.get_message(lang, 'p2p_card_added_success'))
    
    # --- ИЗМЕНЕНИЕ ---
    # Теперь запрашиваем сумму в RUB
    await message.answer(translator.get_message(lang, 'p2p_enter_rub_amount'))
    # --- /ИЗМЕНЕНИЕ ---
    
    await state.set_state(P2PStates.waiting_for_amount)


@router.message(P2PStates.waiting_for_amount, F.text)
async def process_deal_amount(message: Message, state: FSMContext) -> None:
    user_data = db.get_user_data(message.from_user.id)
    lang = user_data.get('language', 'ru')
    
    try:
        amount = float(message.text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer(translator.get_message(lang, 'p2p_invalid_amount'))
        return
    
    # --- ИЗМЕНЕНИЕ: Проверка баланса ---
    # Получаем текущий баланс пользователя
    user_balance = float(user_data.get('balance', 0))
    # Проверяем, достаточно ли средств для сделки
    if amount > user_balance:
        await message.answer(translator.get_message(lang, 'p2p_insufficient_balance'))
        return
    # --- /ИЗМЕНЕНИЕ ---

    await state.update_data(amount=amount)
    data = await state.get_data()

    # Определяем валюту для отображения
    currency_symbol = 'TON' if data.get('recipient_type') == 'ton_wallet' else 'Рублей'
    
    # Формируем текст подтверждения
    confirmation_text = translator.get_message(lang, 'p2p_confirm_deal_header') + "\n\n"
    confirmation_text += f"**{translator.get_message(lang, 'p2p_recipient_type')}:** {data['recipient_type'].replace('ton_wallet', translator.get_button(lang, 'add_ton_wallet')).replace('card', translator.get_button(lang, 'add_card'))}\n"
    confirmation_text += f"**{translator.get_message(lang, 'p2p_recipient_address')}:** `{data['recipient_address']}`\n"
    confirmation_text += f"**{translator.get_message(lang, 'p2p_transfer_amount')}:** {data['amount']} {currency_symbol}"
    
    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'p2p_confirm'), callback_data="confirm_deal")
    builder.button(text=translator.get_button(lang, 'p2p_decline'), callback_data="decline_deal")
    builder.adjust(2)
    
    await message.answer(confirmation_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await state.set_state(P2PStates.waiting_for_confirmation)


@router.callback_query(P2PStates.waiting_for_confirmation, F.data == "confirm_deal")
async def confirm_deal_handler(callback: CallbackQuery, state: FSMContext) -> None:
    user_data = db.get_user_data(callback.from_user.id)
    lang = user_data.get('language', 'ru')
    data = await state.get_data()
    
    # TODO: Здесь должна быть логика проведения сделки.
    # 1. Найти получателя по `data['recipient_address']`.
    # 2. Если получатель найден, списать с баланса отправителя `data['amount']`.
    # 3. Зачислить эту сумму на баланс получателя.
    # 4. Если получателя нет, деньги можно "списать в никуда" или вернуть пользователю.

    # Определяем валюту и адрес получения в зависимости от типа
    if data['recipient_type'] == 'ton_wallet':
        currency_name = 'TON'
        address_label = 'Адрес получения'
        currency_symbol = 'TON'
    else: # card
        currency_name = 'Rub'
        address_label = 'Адрес получения'
        currency_symbol = 'Рублей'
        
    final_confirmation_text = (
        f"✅ *Запрос на вывод успешно оформлен*\n"
        f"Ваш перевод обрабатывается. Средства будут зачислены в течение 1–24 часов в зависимости от загрузки сети.\n\n"
        f"🔹 **Валюта:** {currency_name}\n"
        f"🔹 **Сумма:** {data['amount']} {currency_symbol}\n"
        f"🔹 **{address_label}:** `{data['recipient_address']}`\n\n"
        f"Спасибо, что пользуетесь нашим сервисом!"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'back_to_main'), callback_data="back_to_main")
    builder.adjust(1)
    
    await callback.message.edit_text(final_confirmation_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    
    await state.clear()
    await callback.answer()


@router.callback_query(P2PStates.waiting_for_confirmation, F.data == "decline_deal")
async def decline_deal_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text("Сделка отменена.")
    await state.clear()
    await callback.answer()