from aiogram import F, Router, html
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

from src.locales import translator
from src.database import db
from src.states import *
from src.handlers.user_routers.user_main import command_start_handler

router = Router()

# --- Смена языка ---
@router.callback_query(F.data == 'change_language')
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


@router.callback_query(LanguageStates.choosing_language, F.data.in_({'set_english', 'set_russian'}))
async def set_language_handler(callback: CallbackQuery, state: FSMContext) -> None:
    new_lang = 'en' if callback.data == 'set_english' else 'ru'
    db.update_language(callback.from_user.id, new_lang)
    
    await state.clear()
    await command_start_handler(callback, state)