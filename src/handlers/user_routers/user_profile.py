import re
from aiogram import F, Router, html
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

from src.locales import translator
from src.database import db
from src.states import *
from src.utils.formatters import format_ton_wallet, format_card_number
from src.handlers.user_routers.user_main import command_start_handler

from src.config import ADMIN_GROUPS

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
    """
    Обработчик, который срабатывает при нажатии на 'Пополнить кошелек'.
    Сразу просит пользователя ввести сумму пополнения.
    """
    user_data = db.get_user_data(callback.from_user.id)
    lang = user_data.get('language', 'ru')

    if not user_data.get('ton_wallet'):
        builder = InlineKeyboardBuilder()
        builder.button(text=translator.get_button(lang, 'add_wallet'), callback_data="add_change_wallet")
        builder.adjust(1)
        await callback.answer(translator.get_message(lang, 'wallet_not_added_warning'), show_alert=True)
        return
    
    # Создаем клавиатуру с кнопкой "Отмена"
    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'cancel_top_up'), callback_data="cancel_top_up")
    
    text = translator.get_message(lang, 'top_up_enter_amount')
    
    await callback.message.edit_text(
        text, 
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    
    # Устанавливаем состояние, ожидающее ввода суммы
    await state.set_state(TopUpStates.waiting_for_amount)
    await callback.answer()

@router.message(TopUpStates.waiting_for_amount, F.text)
async def process_top_up_amount(message: Message, state: FSMContext) -> None:
    """
    Обработчик для получения суммы пополнения.
    Проверяет введенную сумму и отправляет пользователю адрес для перевода.
    """
    user_data = db.get_user_data(message.from_user.id)
    lang = user_data.get('language', 'ru')
    
    try:
        amount = float(message.text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        text = translator.get_message(lang, 'p2p_invalid_amount')
        await message.answer(text, parse_mode="HTML")
        return
    
    # Сохраняем сумму в контекст состояния
    await state.update_data(amount=amount)
    
    # Адрес кошелька, на который нужно перевести средства
    ton_wallet_address = "UQDoDzbmTF6UO6x9dAoKn_KvbINKptV6kHrCMqv3G4csblFh"
    
    # Создаем клавиатуру с кнопкой подтверждения перевода
    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'confirm_top_up'), callback_data="confirm_transfer")
    builder.button(text=translator.get_button(lang, 'cancel_top_up'), callback_data="cancel_top_up")
    builder.adjust(1, 1)
    
    # Формируем и отправляем сообщение с инструкцией по переводу
    text = translator.get_message(lang, 'top_up_wallet_text', ton_wallet_address=ton_wallet_address, amount=amount)
    
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    
    # Устанавливаем новое состояние, ожидающее подтверждения перевода от пользователя
    await state.set_state(TopUpStates.waiting_for_confirmation)


@router.callback_query(TopUpStates.waiting_for_confirmation, F.data == "confirm_transfer")
async def confirm_transfer_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик, который срабатывает после того, как пользователь подтвердил перевод.
    Отправляет заявку администраторам.
    """
    state_data = await state.get_data()
    amount = state_data.get('amount')

    if amount is None:
        await callback.message.edit_text("Произошла ошибка, попробуйте еще раз.")
        await state.clear()
        return

    # Создаем клавиатуру для администратора
    admin_builder = InlineKeyboardBuilder()
    admin_builder.button(
        text="✅ Подтвердить",
        callback_data=f"admin_confirm_top_up:{callback.from_user.id}:{amount}"
    )
    admin_builder.button(
        text="❌ Отклонить",
        callback_data=f"admin_decline_top_up:{callback.from_user.id}:{amount}"
    )
    admin_builder.adjust(2)
    
    # Формируем текст заявки для администратора
    admin_text = (
        "🔔 Новая заявка на пополнение\n\n"
        f"👤 Пользователь: @{callback.from_user.username or 'N/A'}\n"
        f"🆔 ID: {callback.from_user.id}\n"
        f"💰 Сумма: {amount} TON"
    )

    # Отправляем заявку в чат поддержки
    for group in ADMIN_GROUPS:
        await callback.bot.send_message(
            chat_id=group,
            text=admin_text,
            reply_markup=admin_builder.as_markup()
        )
    
    # Отправляем подтверждение пользователю
    await callback.message.edit_text(
        "✅ Ваша заявка на пополнение отправлена администраторам.\n"
        "Ожидайте подтверждения."
    )
    
    # Очищаем состояние пользователя
    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("admin_confirm_top_up"))
async def admin_confirm_top_up(callback: CallbackQuery) -> None:
    """
    Обработчик для кнопки 'Подтвердить' в чате администратора.
    Обновляет баланс пользователя и уведомляет обе стороны.
    """
    # Разбираем callback_data для получения ID пользователя и суммы
    _prefix, user_id_str, amount_str = callback.data.split(':')
    user_id = int(user_id_str)
    amount = float(amount_str)

    # Получаем данные пользователя и обновляем баланс
    user_data = db.get_user_data(user_id)
    current_balance = user_data.get('balance', 0)
    new_balance = current_balance + amount
    db.update_user_data(user_id, {'balance': new_balance})

    # Уведомляем администратора, что заявка подтверждена
    await callback.message.edit_text(
        f"✅ Заявка на пополнение от пользователя {user_id} на сумму {amount} TON подтверждена."
    )
    await callback.answer("Заявка подтверждена")

    # Уведомляем пользователя о пополнении
    user_text = (
        f"✅ Ваша заявка на пополнение на сумму {amount} TON была успешно подтверждена.\n"
        f"Ваш новый баланс: {new_balance} TON."
    )
    await callback.bot.send_message(
        chat_id=user_id,
        text=user_text
    )


@router.callback_query(F.data.startswith("admin_decline_top_up"))
async def admin_decline_top_up(callback: CallbackQuery) -> None:
    """
    Обработчик для кнопки 'Отклонить' в чате администратора.
    Уведомляет пользователя об отказе.
    """
    # Разбираем callback_data для получения ID пользователя и суммы
    _prefix, user_id_str, amount_str = callback.data.split(':')
    user_id = int(user_id_str)
    amount = float(amount_str)

    # Уведомляем администратора об отказе
    await callback.message.edit_text(
        f"❌ Заявка на пополнение от пользователя {user_id} на сумму {amount} TON отклонена."
    )
    await callback.answer("Заявка отклонена")

    # Уведомляем пользователя об отказе
    user_text = f"❌ Ваша заявка на пополнение на сумму {amount} TON была отклонена администратором."
    await callback.bot.send_message(
        chat_id=user_id,
        text=user_text
    )


@router.callback_query(F.data == "cancel_top_up")
async def cancel_top_up_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик отмены пополнения на любом этапе.
    """
    user_data = db.get_user_data(callback.from_user.id)
    lang = user_data.get('language', 'ru')
    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'back_to_main'), callback_data="back_to_main")
    builder.adjust(1)
    
    await callback.message.edit_text(
        translator.get_message(lang, 'top_up_canceled'),
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await state.clear()
    await callback.answer()



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
