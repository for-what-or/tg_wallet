import re
from aiogram import F, Router, html
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram import types

from src.locales import translator
from src.database import db
from src.states import RegistrationStates, WalletStates, CardStates, LanguageStates

user_router = Router()

def get_main_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру главного меню.
    """
    builder_start = InlineKeyboardBuilder()
    builder_start.button(text=translator.get_button(lang, 'profile'), callback_data="profile")
    builder_start.button(text=translator.get_button(lang, 'add_wallet'), callback_data="add_change_wallet")
    builder_start.button(text=translator.get_button(lang, 'create_deal'), callback_data="create_deal")
    builder_start.button(text=translator.get_button(lang, 'ref_link'), callback_data="ref_link")
    builder_start.button(text=translator.get_button(lang, 'change_language'), callback_data="change_language")
    builder_start.adjust(1)
    return builder_start.as_markup()

def get_register_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для регистрации.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="Начать регистрацию", callback_data="register")
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
        text = translator.get_message('ru', 'first_message')
        keyboard = get_register_keyboard()
        await update.answer(text, reply_markup=keyboard)

@user_router.callback_query(F.data == 'register')
async def register_handler(callback: CallbackQuery, state: FSMContext) -> None:
    builder = InlineKeyboardBuilder()
    builder.button(text="Имя из профиля", callback_data="use_profile_name")
    builder.adjust(1)
    await callback.message.edit_text(
        translator.get_message('ru', 'register'),
        reply_markup=builder.as_markup()
    )
    await state.set_state(RegistrationStates.waiting_for_name)
    await callback.answer()

@user_router.message(RegistrationStates.waiting_for_name, F.text)
async def process_name(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    user_name = message.text
    full_name = message.from_user.full_name

    if not (2 <= len(user_name) <= 50):
        await message.answer("Имя должно быть от 2 до 50 символов. Пожалуйста, попробуйте ещё раз.")
        return

    db.register_new_user(user_id, user_name, full_name, 'ru')
    await state.clear()
    await command_start_handler(message, state)

@user_router.callback_query(RegistrationStates.waiting_for_name, F.data == 'use_profile_name')
async def use_profile_name_handler(callback: CallbackQuery, state: FSMContext) -> None:
    user_id = callback.from_user.id
    user_name = callback.from_user.full_name
    
    db.register_new_user(user_id, user_name, user_name, 'ru')
    await state.clear()
    await command_start_handler(callback, state)


# --- Мой профиль ---
# Важно! Убедитесь, что у вас есть импорт command_start_handler
# from .start_handler import command_start_handler 

@user_router.callback_query(F.data == 'profile')
async def profile_handler(callback: CallbackQuery) -> None:
    user_data = db.get_user_data(callback.from_user.id)
    
    # Обработка случая, когда пользователь не найден в базе
    if user_data is None:
        await callback.answer("Ошибка: пользователь не найден. Пожалуйста, попробуйте перезапустить бота.")
        await command_start_handler(callback) # Или другая функция для перезапуска
        return

    lang = user_data.get('language', 'ru')

    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'transfer'), callback_data="transfer")
    builder.button(text=translator.get_button(lang, 'withdraw'), callback_data="withdraw")
    builder.button(text=translator.get_button(lang, 'back'), callback_data="back_to_main")
    builder.adjust(1)

    # Теперь все переменные для форматирования передаются напрямую в get_message
    profile_text = translator.get_message(
        lang, 
        'profile_text',
        user_name=user_data.get('username', callback.from_user.full_name),
        balance=user_data.get('balance', '0'),
        ton_wallet=user_data.get('ton_wallet', 'Не добавлен'),
        card_number=user_data.get('card_number', 'Не добавлена'),
        deals_count=user_data.get('deals_count', 0)
    )

    await callback.message.edit_text(profile_text, reply_markup=builder.as_markup())
    await callback.answer()




# --- Добавление кошелька/карты (FSM-логика) ---
@user_router.callback_query(F.data == 'add_change_wallet')
async def add_wallet_card_handler(callback: CallbackQuery) -> None:
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 TON-кошелек", callback_data="add_ton_wallet")
    builder.button(text="💳 Карта", callback_data="add_card")
    builder.button(text="⬅️ Назад", callback_data="back_to_main")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "💼 Выберите что хотите добавить:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@user_router.callback_query(F.data == 'add_ton_wallet')
async def add_ton_wallet_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "Добавьте ваш TON-кошелек\n\n"
        "Пожалуйста, отправьте адрес вашего кошелька."
    )
    await state.set_state(WalletStates.waiting_for_wallet)
    await callback.answer()

@user_router.message(WalletStates.waiting_for_wallet, F.text)
async def process_ton_wallet(message: Message, state: FSMContext) -> None:
    wallet_address = message.text
    # Простая проверка валидности адреса TON-кошелька
    if not re.match(r'^[a-zA-Z0-9_-]{48}$', wallet_address):
        await message.answer("Неверный формат адреса. Пожалуйста, отправьте корректный адрес TON-кошелька.")
        return
    
    db.update_ton_wallet(message.from_user.id, wallet_address)
    await state.clear()
    await message.answer("✅ TON-кошелек успешно добавлен!")
    await command_start_handler(message, state)


@user_router.callback_query(F.data == 'add_card')
async def add_card_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "💳 Добавьте вашу банковскую карту:\n\n"
        "Пожалуйста, отправьте номер вашей карты (16 цифр)."
    )
    await state.set_state(CardStates.waiting_for_card)
    await callback.answer()

@user_router.message(CardStates.waiting_for_card, F.text)
async def process_card_number(message: Message, state: FSMContext) -> None:
    card_number = message.text.replace(' ', '')
    # Простая проверка на 16 цифр
    if not re.match(r'^\d{16}$', card_number):
        await message.answer("Неверный формат номера карты. Пожалуйста, введите 16 цифр.")
        return

    db.update_card_number(message.from_user.id, card_number)
    await state.clear()
    await message.answer("✅ Карта успешно добавлена!")
    await command_start_handler(message, state)


# --- Смена языка ---
@user_router.callback_query(F.data == 'change_language')
async def language_handler(callback: CallbackQuery, state: FSMContext) -> None:
    builder = InlineKeyboardBuilder()
    builder.button(text="English", callback_data="set_english")
    builder.button(text="Русский", callback_data="set_russian")
    builder.button(text="⬅️ Назад", callback_data="back_to_main")
    builder.adjust(2, 1)
    
    await callback.message.edit_text(
        "🌍 Choose your language:\nВыберите язык:",
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


@user_router.message(Command("id"))
async def command_id_handler(message: Message) -> None:
    user_id = message.from_user.id
    await message.answer(
        f"Ваш ID:\n"
        f"<code>{user_id}</code>\n\n"
        "Нажмите на ID, чтобы скопировать",
        parse_mode="HTML"
    )

