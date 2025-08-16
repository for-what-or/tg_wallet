from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, FSInputFile, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

# Предполагается, что эти модули доступны
from src.database import db
from src.locales import translator
from src.config import *
from src.states import *

router = Router()

@router.callback_query(F.data == 'support')
async def support_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик, который срабатывает при нажатии на кнопку 'Поддержка'.
    Инициирует диалог с пользователем для сбора информации.
    """
    # Получаем язык пользователя из базы данных, если доступно.
    try:
        user_data = db.get_user_data(callback.from_user.id)
        lang = user_data.get('language', 'ru')
    except NameError:
        lang = 'ru'
        
    # Устанавливаем состояние FSM для ожидания сообщения от пользователя
    await state.set_state(SupportState.waiting_for_message)

    # Создаем клавиатуру с кнопкой "Назад" с локализованным текстом
    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'back'), callback_data="back_to_main")
    builder.adjust(1)
    
    # Отправляем сообщение с инструкциями, используя локализацию
    text = translator.get_message(
        lang,
        "support_instructions",
        user_id=callback.from_user.id,
        username=callback.from_user.username
    )
    
    # Используем FSInputFile и InputMediaPhoto для отправки фото
    photo = FSInputFile(PHOTO_PATH)
    await callback.message.edit_media(
        media=InputMediaPhoto(media=photo, caption=text, parse_mode="HTML"),
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.message(SupportState.waiting_for_message)
async def process_support_message(message: Message, state: FSMContext) -> None:
    """
    Обработчик, который принимает сообщение от пользователя и отправляет его в чат поддержки.
    Добавлена кнопка "Ответить" для администраторов.
    """
    # Отправляем подтверждение пользователю с локализованным текстом
    lang = translator.get_user_lang(message.from_user.id)
    await message.answer(translator.get_message(lang, "support_request_sent_user"))
    
    # Сбрасываем состояние FSM
    await state.clear()
    
    # Собираем информацию о пользователе
    user_info = {
        'id': message.from_user.id,
        'username': f"@{message.from_user.username}" if message.from_user.username else "No",
    }
    
    # Формируем текст заявки для операторов, используя локализацию
    support_request_text = translator.get_message(
        'ru',
        "support_request_admin",
        username=user_info['username'],
        user_id=user_info['id'],
        text=message.text
    )

    # Создаем кнопку "Ответить" с локализованным текстом
    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button('ru', "reply_admin"), callback_data=f"reply_to_support:{message.from_user.id}")
    builder.adjust(1)

    # Пересылаем сообщение пользователя в чат поддержки с кнопкой "Ответить"
    for group in ADMIN_GROUPS:
        try:
            await message.bot.send_message(
                chat_id=group,
                text=support_request_text,
                reply_markup=builder.as_markup()
            )
            
            # Если пользователь прислал фото, пересылаем его отдельно
            if message.photo:
                await message.bot.send_photo(
                    chat_id=group,
                    photo=message.photo[-1].file_id,
                    caption=translator.get_message('ru', "support_screenshots")
                )
        except Exception as e:
            # Логируем ошибку, если не удалось отправить сообщение
            print(f"Failed to send support request to group {group}: {e}")

# Обработчик для кнопки "Ответить" в административной группе
@router.callback_query(F.data.startswith('reply_to_support'))
async def reply_handler(callback: CallbackQuery, state: FSMContext) -> None:
    _, target_user_id = callback.data.split(":")
    await state.set_state(AdminReplyState.waiting_for_reply_text)
    await state.update_data(target_user_id=int(target_user_id))

    await callback.message.answer(translator.get_message('ru', "admin_enter_reply_text"))
    await callback.answer()
        
# Обработчик, который принимает текст ответа от администратора и отправляет его пользователю
@router.message(AdminReplyState.waiting_for_reply_text)
async def send_reply_to_user(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    target_user_id = data.get('target_user_id')

    if target_user_id is None:
        await message.answer(translator.get_message('ru', "admin_error_no_user_id"))
        await state.clear()
        return
    
    reply_text = message.text
    
    try:
        # Формируем текст ответа для пользователя
        final_text = translator.get_message('ru', "support_reply_to_user", text=reply_text)
        await message.bot.send_message(
            chat_id=target_user_id,
            text=final_text
        )
        await message.answer(translator.get_message('ru', "admin_reply_sent_success"))
    except Exception as e:
        await message.answer(translator.get_message('ru', "admin_reply_sent_error", error=e))
    finally:
        await state.clear()
