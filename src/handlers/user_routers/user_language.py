import asyncio
from aiogram import F, Router, html
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto # Добавили FSInputFile и InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

from src.locales import translator
from src.database import db
from src.states import *
from src.handlers.user_routers.user_main import command_start_handler
from src.config import PHOTO_PATH

router = Router()
# Список доступных языков, который легко расширять
# Ключ - это код языка, значение - название языка
AVAILABLE_LANGUAGES = {
    'en': 'English',
    'ru': 'Русский',
    #'es': 'Español'   # Пример нового языка
}

# --- Команда /language_change ---
@router.callback_query(F.data == 'change_language')
async def language_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик, который срабатывает при нажатии на кнопку смены языка.
    Динамически генерирует кнопки для каждого доступного языка.
    """
    try:
        # Пытаемся получить язык пользователя
        user_data = db.get_user_data(callback.from_user.id)
        lang = user_data.get('language', 'ru')
    except (NameError, AttributeError):
        lang = 'ru'

    builder = InlineKeyboardBuilder()

    # Динамически создаем кнопки для каждого языка из словаря
    for lang_code, lang_name in AVAILABLE_LANGUAGES.items():
        builder.button(
            text=lang_name,
            callback_data=f"set_lang:{lang_code}"
        )
    
    # Добавляем кнопку "Назад"
    builder.button(
        text=translator.get_button(lang, 'back'),
        callback_data="back_to_main"
    )
    
    # Размещаем кнопки в 2 столбца
    builder.adjust(2, 1)

    text = translator.get_message(lang, 'choose_language')
    photo = FSInputFile(PHOTO_PATH)

    # Редактируем предыдущее сообщение, заменяя его на фото с новым текстом
    await callback.message.edit_media(
        media=InputMediaPhoto(media=photo, caption=text, parse_mode="HTML"), 
        reply_markup=builder.as_markup()
    )
    
    await state.set_state(LanguageStates.choosing_language)
    await callback.answer()


@router.callback_query(LanguageStates.choosing_language, F.data.startswith('set_lang:'))
async def set_language_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик для установки выбранного языка.
    Язык извлекается из callback_data.
    """
    # Извлекаем код языка из callback_data
    # Например, из 'set_lang:en' получаем 'en'
    new_lang = callback.data.split(':')[1]

    # Обновляем язык в базе данных
    db.update_language(callback.from_user.id, new_lang)
    
    # Редактируем ПОДПИСЬ сообщения, а не текст
    await callback.message.edit_caption(
        caption=translator.get_message(new_lang, 'language_changed', language=new_lang.upper()),
        parse_mode="HTML"
    )
    
    # Ждем 1 секунду
    await asyncio.sleep(1)
    # Вызываем обработчик главного меню
    await command_start_handler(callback, state)
    # Очищаем состояние
    await state.clear()
    # Отправляем ответ на callback, чтобы убрать "часики"
    await callback.answer()
