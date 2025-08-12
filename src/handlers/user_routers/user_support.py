from aiogram import F, Router, types
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Предполагается, что эти модули доступны
from src.database import db
from src.locales import translator

router = Router()

# Создаем группу состояний для диалога с поддержкой
class SupportState(StatesGroup):
    waiting_for_message = State()

# ID чата, куда будут пересылаться заявки. Замените на реальный ID.
SUPPORT_CHAT_ID = 1289335419

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

    # Пересылаем сообщение пользователя в чат поддержки
    # Это позволяет операторам видеть оригинальное сообщение, включая вложения
    await message.bot.send_message(
        chat_id=SUPPORT_CHAT_ID,
        text=support_request_text,
    )
    
    # Если пользователь прислал фото, пересылаем его отдельно
    if message.photo:
        await message.bot.send_photo(
            chat_id=SUPPORT_CHAT_ID,
            photo=message.photo[-1].file_id,
            caption="Скриншоты: [файлы]"
        )

