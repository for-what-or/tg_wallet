from aiogram import F, Router
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram import types

from src.database import db
from src.locales import translator
from src.config import PHOTO_PATH

router = Router()

@router.callback_query(F.data == 'about_us')
async def about_us_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик, который срабатывает при нажатии на кнопку 'О нас'.
    Отправляет информацию о боте с четырьмя кнопками.
    """
    try:
        user_data = db.get_user_data(callback.from_user.id)
        lang = user_data.get('language', 'ru')
    except NameError:
        lang = 'ru'
        
    builder = InlineKeyboardBuilder()
    
    # 1. Кнопка "Гарантии и Безопасность".
    builder.add(types.InlineKeyboardButton(
        text=translator.get_button(lang, 'guarantees_and_security'),
        callback_data="guarantees_and_security"
    ))

    # 2. Кнопка "Как это работает".
    builder.add(types.InlineKeyboardButton(
        text=translator.get_button(lang, 'how_it_works'),
        callback_data="how_it_works"
    ))

    # 3. Кнопка "Правила сервиса".
    builder.add(types.InlineKeyboardButton(
        text=translator.get_button(lang, 'service_rules'),
        callback_data="service_rules"
    ))
    
    # 4. Кнопка для возврата в главное меню.
    builder.add(types.InlineKeyboardButton(
        text=translator.get_button(lang, 'back'),
        callback_data="back_to_main"
    ))

    builder.adjust(1, 1, 1, 1)

    about_us_text = translator.get_message(lang, 'about_us_text')

    # --- ИЗМЕНЕНИЕ: Используем edit_media для обновления сообщения-фото ---
    photo = FSInputFile(PHOTO_PATH)
    await callback.message.edit_media(
        media=InputMediaPhoto(media=photo, caption=about_us_text),
        reply_markup=builder.as_markup()
    )
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---
    
    await callback.answer()

@router.callback_query(F.data == 'guarantees_and_security')
async def guarantees_and_security_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик, который отображает информацию о гарантиях и безопасности.
    """
    try:
        user_data = db.get_user_data(callback.from_user.id)
        lang = user_data.get('language', 'ru')
    except NameError:
        lang = 'ru'
    
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text=translator.get_button(lang, 'back'),
        callback_data="about_us"
    ))
    builder.adjust(1)
    
    # Текст для раздела "Гарантии и Безопасность".
    text = translator.get_message(lang, 'guarantees_and_security_text')
    
    # --- ИЗМЕНЕНИЕ: Используем edit_media для обновления сообщения-фото ---
    photo = FSInputFile(PHOTO_PATH)
    await callback.message.edit_media(
        media=InputMediaPhoto(media=photo, caption=text),
        reply_markup=builder.as_markup()
    )
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---
    await callback.answer()

@router.callback_query(F.data == 'how_it_works')
async def how_it_works_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик, который отображает информацию о том, как работает сервис.
    """
    try:
        user_data = db.get_user_data(callback.from_user.id)
        lang = user_data.get('language', 'ru')
    except NameError:
        lang = 'ru'
    
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text=translator.get_button(lang, 'back'),
        callback_data="about_us"
    ))
    builder.adjust(1)
    
    # Текст для раздела "Как это работает".
    text = translator.get_message(lang, 'how_it_works_text')
    
    # --- ИЗМЕНЕНИЕ: Используем edit_media для обновления сообщения-фото ---
    photo = FSInputFile(PHOTO_PATH)
    await callback.message.edit_media(
        media=InputMediaPhoto(media=photo, caption=text),
        reply_markup=builder.as_markup()
    )
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---
    await callback.answer()

@router.callback_query(F.data == 'service_rules')
async def service_rules_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик, который отображает правила сервиса.
    """
    try:
        user_data = db.get_user_data(callback.from_user.id)
        lang = user_data.get('language', 'ru')
    except NameError:
        lang = 'ru'
    
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text=translator.get_button(lang, 'back'),
        callback_data="about_us"
    ))
    builder.adjust(1)
    
    # Текст для раздела "Правила сервиса".
    text = translator.get_message(lang, 'service_rules_text')
    
    # --- ИЗМЕНЕНИЕ: Используем edit_media для обновления сообщения-фото ---
    photo = FSInputFile(PHOTO_PATH)
    await callback.message.edit_media(
        media=InputMediaPhoto(media=photo, caption=text),
        reply_markup=builder.as_markup()
    )
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---
    await callback.answer()
