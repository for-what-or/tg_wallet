import re
import html
from aiogram import F, Router, types
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Предполагается, что эти модули доступны
from src.database import db
from src.locales import translator
from src.config import ADMIN_GROUPS

router = Router()

# Создаем группу состояний для диалога с поддержкой пользователя
class SupportState(StatesGroup):
    waiting_for_message = State()

# Создаем группу состояний для диалога с администратором по поводу ответа
class AdminReplyState(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_reply_text = State()

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

    # Создаем клавиатуру с кнопкой "Назад".
    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'back'), callback_data="back_to_main")
    builder.adjust(1)
    
    # Отправляем сообщение с инструкциями
    text = (
        "🛠 Поддержка\n"
        "Нужна помощь или возник вопрос? Мы на связи 24/7.\n\n"
        "Пожалуйста, укажите:\n"
        "🔹Ваш ID (или номер телефона / username)\n"
        "🔹Суть проблемы\n"
        "🔹Скриншоты, если есть\n\n"
        "Опишите вашу проблему максимально подробно."
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.message(SupportState.waiting_for_message)
async def process_support_message(message: Message, state: FSMContext) -> None:
    """
    Обработчик, который принимает сообщение от пользователя и отправляет его в чат поддержки.
    Добавлена кнопка "Ответить" для администраторов.
    """
    # Отправляем подтверждение пользователю
    await message.answer(
        "✅ Ваша заявка отправлена в службу поддержки.\n"
        "Оператор свяжется с вами в течение 1–12 часов."
    )
    
    # Сбрасываем состояние FSM
    await state.clear()
    
    # Собираем информацию о пользователе
    user_info = {
        'id': message.from_user.id,
        'username': f"@{message.from_user.username}" if message.from_user.username else "Нет",
    }
    
    # Формируем текст заявки для операторов
    support_request_text = (
        "Новая заявка в поддержку\n\n"
        f"👤 Пользователь: {user_info['username']}\n"
        f"🆔 ID: {user_info['id']}\n"
        f"📄 Текст заявки: \"{message.text}\"\n"
    )

    # Создаем кнопку "Ответить"
    builder = InlineKeyboardBuilder()
    builder.button(text="Ответить", callback_data=f"reply_to_support")
    builder.adjust(1)

    # Пересылаем сообщение пользователя в чат поддержки с кнопкой "Ответить"
    for group in ADMIN_GROUPS:
        await message.bot.send_message(
            chat_id=group,
            text=support_request_text,
            reply_markup=builder.as_markup()
        )
    
    # Если пользователь прислал фото, пересылаем его отдельно
    if message.photo:
        for group in ADMIN_GROUPS:
            await message.bot.send_photo(
                chat_id=group,
                photo=message.photo[-1].file_id,
                caption="Скриншоты: [файлы]"
            )

# Обработчик для кнопки "Ответить" в административной группе
@router.callback_query(F.data == 'reply_to_support')
async def reply_handler(callback: CallbackQuery, state: FSMContext) -> None:
    # Просим администратора ввести ID пользователя
    await state.set_state(AdminReplyState.waiting_for_user_id)
    await callback.message.answer(
        "Введите ID пользователя, которому вы хотите ответить."
    )
    await callback.answer()

# Обработчик, который принимает ID пользователя от администратора
@router.message(AdminReplyState.waiting_for_user_id)
async def process_user_id(message: Message, state: FSMContext) -> None:
    user_id_str = message.text.strip()
    try:
        user_id = int(user_id_str)
        await state.update_data(target_user_id=user_id)
        await state.set_state(AdminReplyState.waiting_for_reply_text)
        await message.answer(
            "ID пользователя сохранен. Теперь введите текст ответа."
        )
    except ValueError:
        await message.answer(
            "Неверный ID. Пожалуйста, введите корректный числовой ID."
        )
        
# Обработчик, который принимает текст ответа от администратора и отправляет его пользователю
@router.message(AdminReplyState.waiting_for_reply_text)
async def send_reply_to_user(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    target_user_id = data.get('target_user_id')

    if target_user_id is None:
        await message.answer("Ошибка: не удалось найти ID пользователя. Попробуйте начать заново.")
        await state.clear()
        return
    
    reply_text = message.text
    
    try:
        # Формируем текст ответа для пользователя
        final_text = f"🗣️ Ответ службы поддержки:\n\n{reply_text}"
        await message.bot.send_message(
            chat_id=target_user_id,
            text=final_text
        )
        await message.answer("Ответ успешно отправлен пользователю.")
    except Exception as e:
        await message.answer(f"Не удалось отправить сообщение пользователю: {e}")
    finally:
        await state.clear()
