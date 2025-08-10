import re
from aiogram import F, Router, html
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram import types

from src.locales import translator
from src.database import db
from src.states import RegistrationStates, WalletStates, CardStates, LanguageStates, P2PStates

user_router = Router()

def get_main_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру главного меню.
    """
    builder_start = InlineKeyboardBuilder()
    builder_start.button(text=translator.get_button(lang, 'profile'), callback_data="profile")
    #builder_start.button(text=translator.get_button(lang, 'add_wallet'), callback_data="add_change_wallet")
    builder_start.button(text=translator.get_button(lang, 'create_deal'), callback_data="create_deal")
    #builder_start.button(text=translator.get_button(lang, 'ref_link'), callback_data="ref_link")
    # Новая кнопка для P2P-обмена
    builder_start.button(text=translator.get_button(lang, 'p2p'), callback_data="p2p")
    builder_start.button(text=translator.get_button(lang, 'change_language'), callback_data="change_language")
    builder_start.adjust(1)
    return builder_start.as_markup()

def get_register_keyboard(lang: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для регистрации.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'start_registration'), callback_data="register")
    builder.adjust(1)
    return builder.as_markup()

# Хэндлеры для /start и кнопки "Назад"
@user_router.message(CommandStart())
@user_router.callback_query(F.data == 'back_to_main')
async def command_start_handler(update: types.Message | types.CallbackQuery, state: FSMContext) -> None:
    # Сбрасываем все состояния FSM при возвращении в главное меню
    await state.clear()

    user_id = update.from_user.id
    if db.user_exists(user_id):
        lang = db.get_user_language(user_id)
        text = translator.get_message(lang, 'welcome')
        keyboard = get_main_menu_keyboard(lang)
        
        if isinstance(update, types.Message):
            await update.answer(text, reply_markup=keyboard)
        else:
            await update.message.edit_text(text, reply_markup=keyboard)
    else:
        # Для незарегистрированных пользователей всегда используем русский
        text = translator.get_message('ru', 'first_message')
        keyboard = get_register_keyboard('ru')
        if isinstance(update, types.Message):
            await update.answer(text, reply_markup=keyboard)
        else:
            await update.message.edit_text(text, reply_markup=keyboard)


@user_router.callback_query(F.data == 'register')
async def register_handler(callback: CallbackQuery, state: FSMContext) -> None:
    lang = db.get_user_language(callback.from_user.id) if db.user_exists(callback.from_user.id) else 'ru'
    
    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'use_profile_name'), callback_data="use_profile_name")
    builder.adjust(1)
    await callback.message.edit_text(
        translator.get_message(lang, 'register'),
        reply_markup=builder.as_markup()
    )
    await state.set_state(RegistrationStates.waiting_for_name)
    await callback.answer()


@user_router.message(RegistrationStates.waiting_for_name, F.text)
async def process_name(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    user_name = message.text
    full_name = message.from_user.full_name
    lang = db.get_user_language(user_id) if db.user_exists(user_id) else 'ru'

    if not (2 <= len(user_name) <= 50):
        await message.answer(translator.get_message(lang, 'name_validation_error'))
        return

    db.register_new_user(user_id, user_name, full_name, lang)
    await state.clear()
    await command_start_handler(message, state)


@user_router.callback_query(RegistrationStates.waiting_for_name, F.data == 'use_profile_name')
async def use_profile_name_handler(callback: CallbackQuery, state: FSMContext) -> None:
    user_id = callback.from_user.id
    user_name = callback.from_user.full_name
    lang = db.get_user_language(user_id) if db.user_exists(user_id) else 'ru'

    db.register_new_user(user_id, user_name, user_name, lang)
    await state.clear()
    await command_start_handler(callback, state)


# --- Мой профиль ---
@user_router.callback_query(F.data == 'profile')
async def profile_handler(callback: CallbackQuery) -> None:
    user_data = db.get_user_data(callback.from_user.id)
    
    if user_data is None:
        await callback.answer(translator.get_message('ru', 'user_not_found_error')) # используем русскую локаль как запасную
        await command_start_handler(callback, FSMContext) 
        return

    lang = user_data.get('language', 'ru')

    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'add_wallet'), callback_data="add_change_wallet")
    builder.button(text=translator.get_button(lang, 'ref_link'), callback_data="ref_link")

    #builder.button(text=translator.get_button(lang, 'transfer'), callback_data="transfer")
    #builder.button(text=translator.get_button(lang, 'withdraw'), callback_data="withdraw")
    builder.button(text=translator.get_button(lang, 'back'), callback_data="back_to_main")
    builder.adjust(1)

    profile_text = translator.get_message(
        lang, 
        'profile_text',
        balance=user_data.get('balance', '0'),
        ton_wallet=user_data.get('ton_wallet', translator.get_message(lang, 'not_added')),
        card_number=user_data.get('card_number', translator.get_message(lang, 'not_added')),
        deals_count=user_data.get('deals_count', 0)
    )

    await callback.message.edit_text(profile_text, reply_markup=builder.as_markup())
    await callback.answer()


# --- Добавление/изменение кошельков и карт ---
@user_router.callback_query(F.data == 'add_change_wallet')
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


@user_router.callback_query(F.data == 'add_ton_wallet')
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


@user_router.message(WalletStates.waiting_for_wallet, F.text)
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


@user_router.callback_query(F.data == 'add_card')
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


@user_router.message(CardStates.waiting_for_card, F.text)
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


# --- Смена языка ---
@user_router.callback_query(F.data == 'change_language')
async def language_handler(callback: CallbackQuery, state: FSMContext) -> None:
    user_data = db.get_user_data(callback.from_user.id)
    lang = user_data.get('language', 'ru')

    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'english'), callback_data="set_english")
    builder.button(text=translator.get_button(lang, 'russian'), callback_data="set_russian")
    builder.button(text=translator.get_button(lang, 'back'), callback_data="back_to_main")
    builder.adjust(2, 1)
    
    await callback.message.edit_text(
        translator.get_message(lang, 'choose_language'),
        reply_markup=builder.as_markup()
    )
    await state.set_state(LanguageStates.choosing_language)
    await callback.answer()


@user_router.callback_query(LanguageStates.choosing_language, F.data.in_({'set_english', 'set_russian'}))
async def set_language_handler(callback: CallbackQuery, state: FSMContext) -> None:
    new_lang = 'en' if callback.data == 'set_english' else 'ru'
    db.update_language(callback.from_user.id, new_lang)
    
    await state.clear()
    await command_start_handler(callback, state)


# --- Команда /id ---
@user_router.message(Command("id"))
async def command_id_handler(message: Message) -> None:
    user_data = db.get_user_data(message.from_user.id)
    lang = user_data.get('language', 'ru')
    user_id = message.from_user.id

    await message.answer(
        translator.get_message(lang, 'id_text_with_copy', user_id=user_id),
        parse_mode="HTML"
    )

# --- P2P Обмен ---
# Обработчик для кнопки "P2P Обмен"
@user_router.callback_query(F.data == 'p2p')
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
@user_router.callback_query(F.data.startswith('p2p_'))
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

# --- Обработчики, требующие привязанного кошелька ---
@user_router.callback_query(F.data.in_({'create_deal', 'ref_link'}))
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

    if callback.data == 'create_deal':
        await create_deal_menu_handler(callback, state)
    elif callback.data == 'ref_link':
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
        
# --- Новая логика для создания сделки ---
async def create_deal_menu_handler(callback: CallbackQuery, state: FSMContext) -> None:
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

@user_router.callback_query(P2PStates.waiting_for_recipient_type, F.data == "add_recipient_ton_wallet")
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

@user_router.callback_query(P2PStates.waiting_for_recipient_type, F.data == "add_recipient_card")
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

@user_router.message(P2PStates.waiting_for_recipient_wallet, F.text)
async def process_recipient_ton_wallet(message: Message, state: FSMContext) -> None:
    user_data = db.get_user_data(message.from_user.id)
    lang = user_data.get('language', 'ru')
    wallet_address = message.text
    
    if not re.match(r'^[a-zA-Z0-9_-]{48}$', wallet_address):
        await message.answer(translator.get_message(lang, 'wallet_validation_error'))
        return
    
    await state.update_data(recipient_address=wallet_address)
    await message.answer(translator.get_message(lang, 'p2p_wallet_added_success'))
    await message.answer(translator.get_message(lang, 'p2p_enter_amount'))
    await state.set_state(P2PStates.waiting_for_amount)

@user_router.message(P2PStates.waiting_for_recipient_card, F.text)
async def process_recipient_card(message: Message, state: FSMContext) -> None:
    user_data = db.get_user_data(message.from_user.id)
    lang = user_data.get('language', 'ru')
    card_number = message.text.replace(' ', '')
    
    if not re.match(r'^\d{16}$', card_number):
        await message.answer(translator.get_message(lang, 'card_validation_error'))
        return

    await state.update_data(recipient_address=card_number)
    await message.answer(translator.get_message(lang, 'p2p_card_added_success'))
    await message.answer(translator.get_message(lang, 'p2p_enter_amount'))
    await state.set_state(P2PStates.waiting_for_amount)


@user_router.message(P2PStates.waiting_for_amount, F.text)
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

    await state.update_data(amount=amount)
    data = await state.get_data()

    # Формируем текст подтверждения
    confirmation_text = translator.get_message(lang, 'p2p_confirm_deal_header') + "\n\n"
    confirmation_text += f"**{translator.get_message(lang, 'p2p_recipient_type')}:** {data['recipient_type'].replace('ton_wallet', translator.get_button(lang, 'add_ton_wallet')).replace('card', translator.get_button(lang, 'add_card'))}\n"
    confirmation_text += f"**{translator.get_message(lang, 'p2p_recipient_address')}:** `{data['recipient_address']}`\n"
    confirmation_text += f"**{translator.get_message(lang, 'p2p_transfer_amount')}:** {data['amount']} TON"
    
    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'p2p_confirm'), callback_data="confirm_deal")
    builder.button(text=translator.get_button(lang, 'p2p_decline'), callback_data="decline_deal")
    builder.adjust(2)
    
    await message.answer(confirmation_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await state.set_state(P2PStates.waiting_for_confirmation)


@user_router.callback_query(P2PStates.waiting_for_confirmation, F.data == "confirm_deal")
async def confirm_deal_handler(callback: CallbackQuery, state: FSMContext) -> None:
    user_data = db.get_user_data(callback.from_user.id)
    lang = user_data.get('language', 'ru')
    data = await state.get_data()

    # TODO: Здесь должна быть логика проведения сделки

    # Формируем текст финального подтверждения сделки
    final_confirmation_text = (
        f"✅ *{translator.get_button(lang, 'p2p_confirm')}!* ✅\n\n"
        f"**{translator.get_message(lang, 'p2p_recipient_type')}:** {data['recipient_type'].replace('ton_wallet', translator.get_button(lang, 'add_ton_wallet')).replace('card', translator.get_button(lang, 'add_card'))}\n"
        f"**{translator.get_message(lang, 'p2p_recipient_address')}:** `{data['recipient_address']}`\n"
        f"**{translator.get_message(lang, 'p2p_transfer_amount')}:** {data['amount']} TON"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'back'), callback_data="back_to_main")
    builder.adjust(1)
    
    await callback.message.edit_text(final_confirmation_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    
    await state.clear()
    await callback.answer()


@user_router.callback_query(P2PStates.waiting_for_confirmation, F.data == "decline_deal")
async def decline_deal_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text("Сделка отменена.")
    await state.clear()
    await callback.answer()
