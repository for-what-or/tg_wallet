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

router = Router()

# Хэндлеры для /start и кнопки "Назад"
@router.message(CommandStart())
@router.callback_query(F.data == 'back_to_main')
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


@router.callback_query(F.data == 'register')
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


@router.message(RegistrationStates.waiting_for_name, F.text)
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


@router.callback_query(RegistrationStates.waiting_for_name, F.data == 'use_profile_name')
async def use_profile_name_handler(callback: CallbackQuery, state: FSMContext) -> None:
    user_id = callback.from_user.id
    user_name = callback.from_user.full_name
    lang = db.get_user_language(user_id) if db.user_exists(user_id) else 'ru'

    db.register_new_user(user_id, user_name, user_name, lang)
    await state.clear()
    await command_start_handler(callback, state)

# --- Команда /id ---
@router.message(Command("id"))
async def command_id_handler(message: Message) -> None:
    # ... (логика из вашего файла, без изменений) ...
    user_data = db.get_user_data(message.from_user.id)
    lang = user_data.get('language', 'ru')
    user_id = message.from_user.id

    await message.answer(
        translator.get_message(lang, 'id_text_with_copy', user_id=user_id),
        parse_mode="HTML"
    )
