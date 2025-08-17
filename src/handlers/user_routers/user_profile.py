import re
from aiogram import F, Router, html
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

from src.locales import translator
from src.database import db
from src.states import *
from src.utils.formatters import format_ton_wallet, format_card_number
from src.handlers.user_routers.user_main import command_start_handler

from src.config import ADMIN_GROUPS, PHOTO_PATH

router = Router()

# --- Мой профиль ---
@router.callback_query(F.data == 'profile')
async def profile_handler(callback: CallbackQuery) -> None:
    
    user_data = db.get_user_data(callback.from_user.id)

    lang = user_data.get('language', 'ru')

    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'add_wallet'), callback_data="add_change_wallet")
    builder.button(text=translator.get_button(lang, 'top_up_wallet'), callback_data="top_up_wallet")
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
    
    photo = FSInputFile(PHOTO_PATH)
    await callback.message.edit_media(
        media=InputMediaPhoto(media=photo, caption=profile_text, parse_mode="HTML"),
        reply_markup=builder.as_markup()
    )
    await callback.answer()


# --- Добавление/изменение кошельков и карт ---
@router.callback_query(F.data == 'add_change_wallet')
async def add_wallet_card_handler(callback: CallbackQuery) -> None:
    user_data = db.get_user_data(callback.from_user.id)
    lang = user_data.get('language', 'ru')

    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'add_ton_wallet'), callback_data="add_ton_wallet")
    builder.button(text=translator.get_button(lang, 'add_card'), callback_data="add_card")
    builder.button(text=translator.get_button(lang, 'back'), callback_data="profile")
    builder.adjust(1)
    
    photo = FSInputFile(PHOTO_PATH)
    await callback.message.edit_media(
        media=InputMediaPhoto(media=photo, caption=translator.get_message(lang, 'select_add_type'), parse_mode="HTML"),
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

    photo = FSInputFile(PHOTO_PATH)
    await callback.message.edit_media(
        media=InputMediaPhoto(media=photo, caption=translator.get_message(lang, 'add_ton_wallet'), parse_mode="HTML"),
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
    
    photo = FSInputFile(PHOTO_PATH)
    await message.bot.send_photo(
        chat_id=message.chat.id,
        photo=photo,
        caption=translator.get_message(lang, 'wallet_added_success')
    )
    # The original call to command_start_handler did not pass the state, so it's been updated.
    await command_start_handler(message, state)


@router.callback_query(F.data == 'add_card')
async def add_card_handler(callback: CallbackQuery, state: FSMContext) -> None:
    user_data = db.get_user_data(callback.from_user.id)
    lang = user_data.get('language', 'ru')

    # Создаем клавиатуру с кнопкой "Назад"
    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'back'), callback_data="add_change_wallet")
    builder.adjust(1)

    photo = FSInputFile(PHOTO_PATH)
    await callback.message.edit_media(
        media=InputMediaPhoto(media=photo, caption=translator.get_message(lang, 'add_card'), parse_mode="HTML"),
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
    
    photo = FSInputFile(PHOTO_PATH)
    await message.bot.send_photo(
        chat_id=message.chat.id,
        photo=photo,
        caption=translator.get_message(lang, 'card_added_success')
    )
    # The original call to command_start_handler did not pass the state, so it's been updated.
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
    
    photo = FSInputFile(PHOTO_PATH)
    await callback.message.edit_media(
        media=InputMediaPhoto(media=photo, caption=text, parse_mode="HTML"), # ИСПРАВЛЕНИЕ: Используем HTML
        reply_markup=builder.as_markup()
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
    
    # Формируем текст заявки для администратора
    # FIX: Telegram's HTML parser doesn't support <br>. We replace it with '\n'.
    text = translator.get_message(
        lang, 
        'top_up_wallet_text', 
        # ИСПРАВЛЕНИЕ: Используем html.code() для корректного отображения адреса
        ton_wallet_address=html.code(ton_wallet_address), 
        amount=amount
    ).replace('<br>', '\n')
    
    photo = FSInputFile(PHOTO_PATH)
    await message.bot.send_photo(
        chat_id=message.chat.id,
        photo=photo,
        caption=text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML" # ИСПРАВЛЕНИЕ: Используем HTML
    )
    
    # Устанавливаем новое состояние, ожидающее подтверждения перевода от пользователя
    await state.set_state(TopUpStates.waiting_for_confirmation)

@router.callback_query(TopUpStates.waiting_for_confirmation, F.data == "confirm_transfer")
async def confirm_transfer_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик, который срабатывает после того, как пользователь подтвердил перевод.
    Отправляет заявку администраторам.
    """
    lang = "ru"
    state_data = await state.get_data()
    amount = state_data.get('amount')

    if amount is None:
        # Используем локализованное сообщение об ошибке
        await callback.message.edit_text(translator.get_message(lang, "top_up_error"))
        await state.clear()
        return

    # Создаем клавиатуру для администратора с локализованными кнопками
    admin_builder = InlineKeyboardBuilder()
    admin_builder.button(
        text=translator.get_button(lang, "p2p_confirm"),
        callback_data=f"admin_confirm_top_up:{callback.from_user.id}:{amount}"
    )
    admin_builder.button(
        text=translator.get_button(lang, "p2p_decline"),
        callback_data=f"admin_decline_top_up:{callback.from_user.id}:{amount}"
    )
    admin_builder.adjust(2)
    
    # Формируем текст заявки для администратора, используя локализацию
    admin_text = translator.get_message(
        lang,
        "admin_new_top_up_request",
        username=callback.from_user.username or 'N/A',
        user_id=callback.from_user.id,
        amount=amount,
        currency="TON"
    )

    # Отправляем заявку в чат поддержки
    for group in ADMIN_GROUPS:
        await callback.bot.send_message(
            chat_id=group,
            text=admin_text,
            reply_markup=admin_builder.as_markup()
        )
    
    # Отправляем подтверждение пользователю с локализованным текстом
    photo = FSInputFile(PHOTO_PATH)
    await callback.message.edit_media(
        media=InputMediaPhoto(media=photo, caption=translator.get_message(lang, "top_up_request_sent_to_admins")),
        reply_markup=None
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
    lang = "ru"

    # Получаем данные пользователя и обновляем баланс
    user_data = db.get_user_data(user_id)
    current_balance = user_data.get('balance', 0)
    new_balance = current_balance + amount
    db.update_user_data(user_id, {'balance': new_balance})

    # Уведомляем администратора, что заявка подтверждена, используя локализацию
    await callback.message.edit_text(
        translator.get_message(
            lang,
            "admin_request_confirmed_top_up",
            user_id=user_id,
            amount=amount,
            currency="TON"
        )
    )
    await callback.answer(translator.get_message(lang, "admin_request_confirmed_alert"))

    # Уведомляем пользователя о пополнении
    user_text = translator.get_message(
        lang,
        "user_top_up_confirmed",
        amount=amount,
        currency="TON",
        new_balance=new_balance
    )
    photo = FSInputFile(PHOTO_PATH)
    await callback.bot.send_photo(
        chat_id=user_id,
        photo=photo,
        caption=user_text
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
    lang = "ru"

    # Уведомляем администратора об отказе, используя локализацию
    await callback.message.edit_text(
        translator.get_message(
            lang,
            "admin_request_declined_top_up",
            user_id=user_id,
            amount=amount,
            currency="TON"
        )
    )
    await callback.answer(translator.get_message(lang, "admin_request_declined_alert"))

    # Уведомляем пользователя об отказе, используя локализацию
    user_text = translator.get_message(
        lang,
        "user_top_up_declined",
        amount=amount,
        currency="TON"
    )
    photo = FSInputFile(PHOTO_PATH)
    await callback.bot.send_photo(
        chat_id=user_id,
        photo=photo,
        caption=user_text
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
    
    photo = FSInputFile(PHOTO_PATH)
    await callback.message.edit_media(
        media=InputMediaPhoto(media=photo, caption=translator.get_message(lang, 'top_up_canceled'), parse_mode="HTML"),
        reply_markup=builder.as_markup()
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
        photo = FSInputFile(PHOTO_PATH)
        await callback.message.edit_media(
            media=InputMediaPhoto(media=photo, caption=translator.get_message(lang, 'wallet_not_added_warning'), parse_mode="HTML"),
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
    
    photo = FSInputFile(PHOTO_PATH)
    await callback.message.edit_media(
        media=InputMediaPhoto(media=photo, caption=translator.get_message(lang, 'ref_link_text', referral_link=html.code(referral_link)), parse_mode="HTML"),
        reply_markup=builder.as_markup()
    )
    await callback.answer()
