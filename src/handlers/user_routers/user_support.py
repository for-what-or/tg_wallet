from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, FSInputFile, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
import asyncio

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
    try:
        user_data = db.get_user_data(callback.from_user.id)
        lang = user_data.get('language', 'ru')
    except NameError:
        lang = 'ru'
    
    await state.set_state(SupportState.waiting_for_message)
    await state.set_data({}) # Очищаем данные FSM для нового диалога

    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'back'), callback_data="back_to_main")
    builder.adjust(1)
    
    text = translator.get_message(
        lang,
        "support_instructions",
        user_id=callback.from_user.id,
        username=callback.from_user.username
    )
    
    photo = FSInputFile(PHOTO_PATH)
    await callback.message.edit_media(
        media=InputMediaPhoto(media=photo, caption=text, parse_mode="HTML"),
        reply_markup=builder.as_markup()
    )
    await callback.answer()

async def send_support_request(message: Message, state: FSMContext):
    """
    Отправляет заявку в поддержку. Отдельная функция для чистоты кода.
    """
    data = await state.get_data()
    user_info = data.get('user_info')
    media_group = data.get('media_group')
    user_message_text = data.get('user_message_text', "")
    
    # Формируем текст заявки для операторов
    support_request_text = translator.get_message(
        'ru',
        "support_request_admin",
        username=user_info['username'],
        user_id=user_info['id'],
        text=user_message_text
    )

    # Создаем кнопку "Ответить"
    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button('ru', "reply_admin"), callback_data=f"reply_to_support:{user_info['id']}")
    builder.adjust(1)
    
    for group in ADMIN_GROUPS:
        try:
            # Отправляем заявку
            if media_group:
                # Отправляем сначала текст с кнопкой
                await message.bot.send_message(
                    chat_id=group,
                    text=support_request_text,
                    reply_markup=builder.as_markup()
                )
                # Затем отправляем медиагруппу (без текста)
                await message.bot.send_media_group(
                    chat_id=group,
                    media=media_group,
                )
            elif data.get('single_photo_id'):
                # Если одиночное фото, отправляем его с текстом и кнопкой
                await message.bot.send_photo(
                    chat_id=group,
                    photo=data['single_photo_id'],
                    caption=support_request_text,
                    reply_markup=builder.as_markup()
                )
            else:
                # Если только текст, отправляем сообщение
                await message.bot.send_message(
                    chat_id=group,
                    text=support_request_text,
                    reply_markup=builder.as_markup()
                )
        except Exception as e:
            print(f"Failed to send support request to group {group}: {e}")
            
    # Отправляем подтверждение пользователю и сбрасываем состояние
    try:
        user_data = db.get_user_data(message.from_user.id)
        lang = user_data.get('language', 'ru')
    except NameError:
        lang = 'ru'
    
    await message.answer(translator.get_message(lang, "support_request_sent_user"))
    await state.clear()


@router.message(SupportState.waiting_for_message)
async def process_support_message(message: Message, state: FSMContext) -> None:
    """
    Единый обработчик для всех типов сообщений в состоянии поддержки.
    """
    # Сохраняем информацию о пользователе
    await state.update_data(user_info={
        'id': message.from_user.id,
        'username': f"@{message.from_user.username}" if message.from_user.username else "No",
    })
    
    data = await state.get_data()
    # Отменяем предыдущую задачу, если она есть
    if 'media_group_task' in data and data['media_group_task']:
        data['media_group_task'].cancel()
        
    # Если это часть медиагруппы
    if message.media_group_id:
        current_media_group = data.get('media_group', [])
        # Добавляем фото в медиагруппу
        if message.photo:
            current_media_group.append(InputMediaPhoto(media=message.photo[-1].file_id))
        
        # Обновляем данные в FSM
        await state.update_data(
            media_group=current_media_group,
            user_message_text=message.caption or data.get('user_message_text', "")
        )
        
        # Создаем новую задачу с таймером
        new_task = asyncio.create_task(
            asyncio.sleep(1.5) # Ждем 1.5 секунды
        )
        await state.update_data(media_group_task=new_task)
        
        try:
            await new_task
            await send_support_request(message, state)
        except asyncio.CancelledError:
            pass # Игнорируем отмененные задачи
            
    # Если это обычное сообщение (не часть медиагруппы)
    else:
        # Сохраняем информацию о фото или тексте
        if message.photo:
            await state.update_data(
                single_photo_id=message.photo[-1].file_id,
                user_message_text=message.caption or ""
            )
        else:
            await state.update_data(user_message_text=message.text)
        
        # Отправляем заявку немедленно
        await send_support_request(message, state)


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
