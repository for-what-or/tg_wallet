from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram import types

from src.database import db
from src.locales import translator

router = Router()

@router.callback_query(F.data == 'about_us')
async def about_us_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик, который срабатывает при нажатии на кнопку 'О нас'.
    Отправляет информацию о боте с четырьмя кнопками.
    """
    # Получаем язык пользователя из базы данных, если доступно.
    # Если нет, используем русский язык по умолчанию.
    try:
        user_data = db.get_user_data(callback.from_user.id)
        lang = user_data.get('language', 'ru')
    except NameError:
        # Если 'db' не определена, используем русский язык по умолчанию.
        lang = 'ru'
        
    # Создаем клавиатуру с кнопками.
    builder = InlineKeyboardBuilder()
    
    # 1. Кнопка "Гарантии и Безопасность".
    builder.add(types.InlineKeyboardButton(
        text="🛡 Гарантии и Безопасность",
        callback_data="guarantees_and_security"
    ))

    # 2. Кнопка "Как это работает".
    builder.add(types.InlineKeyboardButton(
        text="📖 Как это работает",
        callback_data="how_it_works"
    ))

    # 3. Кнопка "Правила сервиса".
    builder.add(types.InlineKeyboardButton(
        text="🧾 Правила сервиса",
        callback_data="service_rules"
    ))
    
    # 4. Кнопка для возврата в главное меню.
    builder.add(types.InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="back_to_main"
    ))

    # Размещаем кнопки в один столбец.
    builder.adjust(1, 1, 1, 1)

    # Получаем текст из локализации.
    about_us_text = translator.get_message(lang, 'about_us_text')

    # Отправляем сообщение.
    await callback.message.edit_text(
        about_us_text,
        reply_markup=builder.as_markup()
    )
    
    # Отвечаем на callback, чтобы убрать "часики".
    await callback.answer()

@router.callback_query(F.data == 'guarantees_and_security')
async def guarantees_and_security_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик, который отображает информацию о гарантиях и безопасности.
    """
    # Получаем язык пользователя.
    try:
        user_data = db.get_user_data(callback.from_user.id)
        lang = user_data.get('language', 'ru')
    except NameError:
        lang = 'ru'
    
    # Создаем клавиатуру с кнопкой "Назад".
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="about_us"
    ))
    builder.adjust(1)
    
    # Текст для раздела "Гарантии и Безопасность".
    text = (
        "🛡 Гарантии и Безопасность\n\n"
        "Мы понимаем, что при работе с криптовалютой важно быть уверенным в защите своих средств.\n"
        "Наш сервис построен так, чтобы исключить риск мошенничества и обеспечить прозрачность каждой операции.\n\n"
        "Как мы защищаем пользователей:\n"
        "• Эскроу-система — средства блокируются на счёте сервиса до выполнения условий сделки обеими сторонами.\n"
        "• Подтверждённые пользователи — каждый участник проходит проверку и верификацию аккаунта.\n"
        "• Защита данных — все операции и личная информация передаются через зашифрованные каналы.\n"
        "• 24/7 поддержка — наши операторы готовы оперативно помочь в любой ситуации.\n"
        "• Прозрачная история сделок — вы всегда можете проверить все свои операции в личном кабинете.\n\n"
        "Наш приоритет — ваша безопасность.\n"
        "Мы не храним ваши пароли и приватные ключи, а все переводы проходят только через защищённые смарт-контракты."
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data == 'how_it_works')
async def how_it_works_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик, который отображает информацию о том, как работает сервис.
    """
    # Получаем язык пользователя.
    try:
        user_data = db.get_user_data(callback.from_user.id)
        lang = user_data.get('language', 'ru')
    except NameError:
        lang = 'ru'
    
    # Создаем клавиатуру с кнопкой "Назад".
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="about_us"
    ))
    builder.adjust(1)
    
    # Текст для раздела "Как это работает".
    text = (
        "📖 Как это работает\n\n"
        "Наш сервис позволяет безопасно покупать и продавать криптовалюту напрямую между пользователями через Telegram.\n\n"
        "Пошагово:\n"
        "1️⃣ Выбор операции — выбираете, что хотите сделать: пополнить кошелёк или вывести средства.\n"
        "2️⃣ Создание сделки — указываете сумму и валюту (например, TON).\n"
        "3️⃣ Эскроу-защита — средства блокируются у сервиса до выполнения условий сделки обеими сторонами.\n"
        "4️⃣ Подтверждение перевода — после получения оплаты или криптовалюты обе стороны подтверждают сделку.\n"
        "5️⃣ Завершение — сервис разблокирует средства и они поступают на ваш баланс.\n\n"
        "💡 Важно: все переводы проходят через зашифрованные каналы, а приватные ключи остаются только у вас."
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data == 'service_rules')
async def service_rules_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик, который отображает правила сервиса.
    """
    # Получаем язык пользователя.
    try:
        user_data = db.get_user_data(callback.from_user.id)
        lang = user_data.get('language', 'ru')
    except NameError:
        lang = 'ru'
    
    # Создаем клавиатуру с кнопкой "Назад".
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="about_us"
    ))
    builder.adjust(1)
    
    # Текст для раздела "Правила сервиса".
    text = (
        "🧾 Правила сервиса\n\n"
        "1️⃣ Только честные сделки — запрещены мошенничество, обман или попытки обойти правила.\n"
        "2️⃣ Корректные данные — указывайте только верные реквизиты. Мы не несём ответственность за ошибки при вводе адресов или карт.\n"
        "3️⃣ Сроки зачисления — переводы обрабатываются в течение 1–24 часов в зависимости от загрузки сети.\n"
        "4️⃣ Комиссии — комиссия сервиса списывается автоматически и зависит от типа операции.\n"
        "5️⃣ Запрет на незаконные операции — сделки с запрещёнными товарами или услугами блокируются.\n"
        "6️⃣ Конфиденциальность — мы не передаём ваши данные третьим лицам.\n"
        "7️⃣ Решение спорных ситуаций — споры рассматриваются поддержкой на основе переписки и доказательств.\n"
        "8️⃣ Соблюдение законодательства — пользователь несёт ответственность за соблюдение законов своей страны.\n\n"
        "💡 Используя сервис, вы соглашаетесь с данными правилами."
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup()
    )
    await callback.answer()
