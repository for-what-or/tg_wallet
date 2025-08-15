import re
from aiogram import F, Router, html, Bot
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram import types
from aiogram.enums.chat_type import ChatType

from src.locales import translator
from src.database import db
from src.states import *
from src.config import ADMIN_GROUPS
# Импортируем клавиатуры из нового файла
from src.utils.keyboards import get_main_menu_keyboard, get_register_keyboard
# Импортируем хелперы из нового файла

from src.bot_commands import set_bot_commands # Импортируем новую функцию для установки команд

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
            await update.answer(text=text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await update.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    else:
        # Для незарегистрированных пользователей всегда используем русский
        text = translator.get_message('ru', 'first_message')
        keyboard = get_register_keyboard('ru')
        
        if isinstance(update, types.Message):
            await update.answer(text=text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await update.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
        
        # Используем translator для формирования текста о новом пользователе
        new_user_text = translator.get_message(
            'ru', 
            'new_user_notification',
            user_id=user_id,
            full_name=update.from_user.full_name,
            username=update.from_user.username or 'N/A'
        )
        
        for group in ADMIN_GROUPS:
            await update.bot.send_message(
                chat_id=group,
                text=new_user_text,
                parse_mode="HTML"
            )

@router.callback_query(F.data == 'register')
async def register_handler(callback: CallbackQuery, state: FSMContext) -> None:
    lang = db.get_user_language(callback.from_user.id) if db.user_exists(callback.from_user.id) else 'ru'

    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'use_profile_name'), callback_data="use_profile_name")
    builder.adjust(1)

    text = translator.get_message(lang, 'register')
    
    await callback.message.edit_text(
        text=text,
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
    user_name = callback.from_user.username
    user_full_name = callback.from_user.full_name
    lang = db.get_user_language(user_id) if db.user_exists(user_id) else 'ru'

    db.register_new_user(user_id, user_name, user_full_name, lang)
    await state.clear()
    await command_start_handler(callback, state)

# --- Команда /id ---
@router.message(Command("id"))
async def command_id_handler(message: Message) -> None:
    """
    Обработчик, который реагирует на команду /id.
    В личных сообщениях возвращает ID пользователя,
    в групповых чатах - ID чата.
    """
    chat_type = message.chat.type
    if chat_type == ChatType.PRIVATE:
        user_id = message.from_user.id
        response_text = f"Your user ID: <code>{user_id}</code>"
    elif chat_type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        chat_id = message.chat.id
        response_text = f"Chat ID: <code>{chat_id}</code>"
    else:
        # Для других типов чатов
        response_text = "I can't provide an ID for this chat type."

    await message.answer(
        response_text,
        parse_mode="HTML"
    )
# --- Команда /balance (для пользователей) ---
@router.message(Command("balance"))
async def handle_balance_command(message: Message) -> None:
    """
    Обработчик для команды /balance.
    Показывает текущий баланс пользователя.
    Изменение баланса разрешено только пользователям с соответствующими правами.
    """
    user_id = message.from_user.id
    
    # Получаем язык пользователя. Если пользователь не зарегистрирован,
    # используем русский язык по умолчанию.
    try:
        user_data = db.get_user_data(user_id)
        lang = user_data.get('language', 'ru')
    except (NameError, AttributeError):
        lang = 'ru'

    args = message.text.split()

    # Если команда без аргументов, показываем текущий баланс
    if len(args) == 1:
        current_balance = db.get_user_balance(user_id)
        text = translator.get_message(lang, 'current_balance', value=current_balance)
        await message.answer(text)
        return

    # Если есть аргументы, проверяем, есть ли у пользователя права на изменение баланса
    if not db.check_balance_permission(user_id):
        text = translator.get_message(lang, 'no_balance_permission')
        await message.answer(text)
        return

    # Если у пользователя есть права, пробуем изменить баланс
    try:
        amount_str = args[1]
        
        # Проверяем, начинается ли строка с "+" или "-"
        if amount_str.startswith('+'):
            amount = float(amount_str[1:])
        elif amount_str.startswith('-'):
            amount = -float(amount_str[1:])
        else:
            # Если нет знака, считаем это ошибкой
            await message.answer(
                "Неверный формат. Используйте /balance <сумма> "
                "(например, /balance +100 или /balance -50)."
            )
            return
            
        current_balance = db.get_user_balance(user_id)
        new_balance = current_balance + amount

        # Проверка, чтобы баланс не стал отрицательным
        if new_balance < 0:
            await message.answer("Недостаточно средств. Баланс не может быть отрицательным.")
            return

        # Обновляем баланс
        db.update_user_balance(user_id, amount)
        current_balance = db.get_user_balance(user_id)
        
        await message.answer(f"Ваш баланс изменен. Теперь он составляет: {current_balance} TON")

    except (ValueError, IndexError):
        await message.answer(
            "Неверный формат. Используйте /balance <сумма> "
            "(например, /balance +100 или /balance -50)."
        )



# --- Новая команда /help ---
@router.message(Command("help"))
async def command_help_handler(message: Message) -> None:
    """
    Обработчик для команды /help.
    Отправляет пользователю список всех доступных команд.
    """
    help_text = (
        "<b>Доступные команды:</b>\n\n"
        "/start - Запустить бота и вернуться в главное меню\n"
        "/help - Показать список команд и их описание\n"
        "/balance - Показать текущий баланс или изменить его (например, /balance +100)\n"
        "/id - Показать ваш уникальный ID\n"
        "/addvip - Выдать разрешение на пополнение баланса (только для админов)"
    )
    await message.answer(help_text, parse_mode="HTML")
