import re
import datetime

from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, FSInputFile, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

from src.locales import translator
from src.database import db
from src.states import *
from src.utils.formatters import format_ton_wallet
from src.config import ADMIN_GROUPS, PHOTO_PATH

router = Router()

@router.callback_query(F.data.in_({'create_deal'}))
async def handle_wallet_required_action(callback: CallbackQuery, state: FSMContext) -> None:
    user_data = db.get_user_data(callback.from_user.id)
    lang = user_data.get('language', 'ru')

    # Проверка наличия TON-кошелька
    if not user_data.get('ton_wallet'):
        builder = InlineKeyboardBuilder()
        builder.button(text=translator.get_button(lang, 'add_wallet'), callback_data="add_change_wallet")
        builder.adjust(1)
        await callback.answer(translator.get_message(lang, 'wallet_not_added_warning'), show_alert=True)
        return
    
    user_data = db.get_user_data(callback.from_user.id)
    lang = user_data.get('language', 'ru')
    
    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'add_ton_wallet'), callback_data="add_recipient_ton_wallet")
    builder.button(text=translator.get_button(lang, 'add_card'), callback_data="add_recipient_card")
    builder.button(text=translator.get_button(lang, 'back'), callback_data="back_to_main")
    builder.adjust(1)
    
    # Редактируем сообщение, заменяя его на фото с новым текстом
    photo = FSInputFile(PHOTO_PATH)
    await callback.message.edit_media(
        media=InputMediaPhoto(media=photo, caption=translator.get_message(lang, 'p2p_enter_recipient_type')),
        reply_markup=builder.as_markup()
    )

    await state.set_state(P2PStates.waiting_for_recipient_type)
    await callback.answer()


@router.callback_query(P2PStates.waiting_for_recipient_type, F.data == "add_recipient_ton_wallet")
async def add_recipient_ton_wallet_handler(callback: CallbackQuery, state: FSMContext) -> None:
    user_data = db.get_user_data(callback.from_user.id)
    lang = user_data.get('language', 'ru')

    # Создаем клавиатуру с кнопкой "Назад", которая возвращает на экран выбора типа получателя
    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'back'), callback_data="create_deal")
    builder.adjust(1)

    # Редактируем подпись (caption) сообщения
    await callback.message.edit_caption(
        caption=translator.get_message(lang, 'p2p_enter_recipient_wallet'),
        reply_markup=builder.as_markup()
    )
    
    await state.set_state(P2PStates.waiting_for_recipient_wallet)
    await state.update_data(recipient_type='ton_wallet')
    await callback.answer()

@router.callback_query(P2PStates.waiting_for_recipient_type, F.data == "add_recipient_card")
async def add_recipient_card_handler(callback: CallbackQuery, state: FSMContext) -> None:
    user_data = db.get_user_data(callback.from_user.id)
    lang = user_data.get('language', 'ru')
    
    # Создаем клавиатуру с кнопкой "Назад", которая возвращает на экран выбора типа получателя
    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'back'), callback_data="create_deal")
    builder.adjust(1)

    # Редактируем подпись (caption) сообщения
    await callback.message.edit_caption(
        caption=translator.get_message(lang, 'p2p_enter_recipient_card'),
        reply_markup=builder.as_markup()
    )
    
    await state.set_state(P2PStates.waiting_for_recipient_card)
    await state.update_data(recipient_type='card')
    await callback.answer()

@router.message(P2PStates.waiting_for_recipient_wallet, F.text)
async def process_recipient_ton_wallet(message: Message, state: FSMContext) -> None:
    user_data = db.get_user_data(message.from_user.id)
    lang = user_data.get('language', 'ru')
    wallet_address = message.text
    
    if not re.match(r'^[a-zA-Z0-9_-]{48}$', wallet_address):
        await message.answer(translator.get_message(lang, 'wallet_validation_error'))
        return
    
    await state.update_data(recipient_address=wallet_address)
    await message.answer(translator.get_message(lang, 'p2p_wallet_added_success'))
    
    # Теперь запрашиваем сумму в TON
    await message.answer(translator.get_message(lang, 'p2p_enter_ton_amount'))
    
    await state.set_state(P2PStates.waiting_for_amount)

@router.message(P2PStates.waiting_for_recipient_card, F.text)
async def process_recipient_card(message: Message, state: FSMContext) -> None:
    user_data = db.get_user_data(message.from_user.id)
    lang = user_data.get('language', 'ru')
    card_number = message.text.replace(' ', '')
    
    if not re.match(r'^\d{16}$', card_number):
        await message.answer(translator.get_message(lang, 'card_validation_error'))
        return

    await state.update_data(recipient_address=card_number)
    await message.answer(translator.get_message(lang, 'p2p_card_added_success'))
    
    # Теперь запрашиваем сумму в RUB
    await message.answer(translator.get_message(lang, 'p2p_enter_rub_amount'))
    
    await state.set_state(P2PStates.waiting_for_amount)


@router.message(P2PStates.waiting_for_amount, F.text)
async def process_deal_amount(message: Message, state: FSMContext) -> None:
    user_data = db.get_user_data(message.from_user.id)
    lang = user_data.get('language', 'ru')
    
    try:
        amount = float(message.text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer(translator.get_message(lang, 'p2p_invalid_amount'))
        return
    
    # Проверка баланса
    user_balance = float(user_data.get('balance', 0))
    if amount > user_balance:
        await message.answer(translator.get_message(lang, 'p2p_insufficient_balance'))
        return

    await state.update_data(amount=amount)
    data = await state.get_data()

    # Определяем валюту для отображения
    currency_symbol = 'TON' if data.get('recipient_type') == 'ton_wallet' else translator.get_message(lang, 'rub_symbol')
    
    # Формируем текст подтверждения
    confirmation_text = translator.get_message(lang, 'p2p_confirm_deal_header') + "\n\n"
    confirmation_text += f"**{translator.get_message(lang, 'p2p_recipient_type')}:** {data['recipient_type'].replace('ton_wallet', translator.get_button(lang, 'add_ton_wallet')).replace('card', translator.get_button(lang, 'add_card'))}\n"
    confirmation_text += f"**{translator.get_message(lang, 'p2p_recipient_address')}:** `{data['recipient_address']}`\n"
    confirmation_text += f"**{translator.get_message(lang, 'p2p_transfer_amount')}:** {data['amount']} {currency_symbol}"
    
    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'p2p_confirm'), callback_data="confirm_deal")
    builder.button(text=translator.get_button(lang, 'p2p_decline'), callback_data="decline_deal")
    builder.adjust(2)
    
    photo = FSInputFile(PHOTO_PATH)
    await message.answer_photo(
        photo=photo,
        caption=confirmation_text,
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

    await state.set_state(P2PStates.waiting_for_confirmation)

@router.callback_query(P2PStates.waiting_for_confirmation, F.data == "confirm_deal")
async def confirm_deal_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Обработчик, который срабатывает после того, как пользователь подтвердил сделку.
    Списывает средства, создает заявку и отправляет ее администраторам.
    """
    user_data = db.get_user_data(callback.from_user.id)
    lang = user_data.get('language', 'ru')
    data = await state.get_data()
    
    current_balance = float(user_data.get('balance', 0))
    amount_to_deduct = data.get('amount')
    
    if amount_to_deduct is None or current_balance < amount_to_deduct:
        # --- ИЗМЕНЕНИЕ: Используем edit_caption для обновления фото-сообщения ---
        await callback.message.edit_caption(caption=translator.get_message(lang, 'p2p_insufficient_balance'))
        await state.clear()
        await callback.answer()
        return

    # 1. Списываем средства с баланса пользователя (они "замораживаются")
    new_balance = current_balance - amount_to_deduct
    db.update_user_data(callback.from_user.id, {'balance': new_balance})

    # Определяем валюту
    currency = 'TON' if data['recipient_type'] == 'ton_wallet' else 'RUB'

    # 2. Создаем запись о сделке в БД со статусом 'pending'
    deal_id = db.create_deal(
        sender_id=callback.from_user.id,
        recipient_address=data['recipient_address'],
        recipient_type=data['recipient_type'],
        amount=amount_to_deduct,
        currency=currency
    )

    # 3. Формируем и отправляем заявку администраторам
    admin_builder = InlineKeyboardBuilder()
    admin_builder.button(text=translator.get_button('ru', 'p2p_confirm'), callback_data=f"admin_confirm_deal:{deal_id}")
    admin_builder.button(text=translator.get_button('ru', 'p2p_decline'), callback_data=f"admin_decline_deal:{deal_id}")
    admin_builder.adjust(2)
    
    admin_text = translator.get_message('ru', 'admin_new_withdrawal_request',
        username=callback.from_user.username or 'N/A',
        user_id=callback.from_user.id,
        amount=amount_to_deduct,
        currency=currency,
        recipient_type=data['recipient_type'],
        recipient_address=data['recipient_address']
    )

    for group_id in ADMIN_GROUPS:
        try:
            await callback.bot.send_message(
                chat_id=group_id,
                text=admin_text,
                reply_markup=admin_builder.as_markup(),
            )
        except Exception as e:
            print(translator.get_message('ru', 'admin_send_message_error', group_id=group_id, error=e))

    # 4. Отправляем подтверждение пользователю
    # --- ИЗМЕНЕНИЕ: Используем edit_caption для обновления фото-сообщения ---
    await callback.message.edit_caption(
        caption=translator.get_message(lang, 'p2p_request_sent_to_admins')
    )
    
    await state.clear()
    await callback.answer()

# --- НОВЫЕ ХЭНДЛЕРЫ ДЛЯ АДМИНОВ ---
@router.callback_query(F.data.startswith("admin_confirm_deal:"))
async def admin_confirm_deal_handler(callback: CallbackQuery) -> None:
    """
    Обработчик для кнопки 'Подтвердить перевод' в чате администратора.
    """
    deal_id = int(callback.data.split(':')[1])
    deal_data = db.get_deal_by_id(deal_id)

    if not deal_data or deal_data['status'] != 'pending':
        await callback.answer(translator.get_message('ru', 'admin_request_already_processed'), show_alert=True)
        return

    # 1. Обновляем статус сделки в БД
    db.update_deal_status(deal_id, 'confirmed')
    
    # Обновляем счетчик сделок у пользователя
    sender_data = db.get_user_data(deal_data['sender_id'])
    new_deals_count = sender_data.get('deals_count', 0) + 1
    db.update_user_data(deal_data['sender_id'], {'deals_count': new_deals_count})


    # 2. Уведомляем администратора
    await callback.message.edit_text(
        translator.get_message('ru', 'admin_request_confirmed',
            sender_id=deal_data['sender_id'],
            amount=deal_data['amount'],
            currency=deal_data['currency'],
            username=callback.from_user.username or 'N/A'
        )
    )
    await callback.answer(translator.get_message('ru', 'admin_request_confirmed_alert'))

    # 3. Уведомляем отправителя
    try:
        await callback.bot.send_message(
            chat_id=deal_data['sender_id'],
            text=translator.get_message('ru', 'user_request_confirmed',
                amount=deal_data['amount'],
                currency=deal_data['currency'],
                recipient_address=deal_data['recipient_address']
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        print(translator.get_message('ru', 'admin_notify_sender_error', user_id=deal_data['sender_id'], error=e))

    # 4. Пытаемся уведомить получателя, если он есть в нашей БД
    recipient_user = db.find_user_by_wallet_or_card(deal_data['recipient_address'])
    if recipient_user:
        try:
            # Увеличиваем баланс получателя на сумму сделки
            db.update_user_balance(recipient_user['user_id'], deal_data['amount'])
            
            # Получаем данные отправителя, чтобы указать его ник в сообщении получателю
            sender_username = sender_data.get('username', translator.get_message('ru', 'anonymous_user'))
            # Экранируем символы подчеркивания для корректного отображения в Markdown
            escaped_username = sender_username.replace('_', '\\_')
            
            # Получаем текущую дату и форматируем кошелек
            current_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
            formatted_wallet = format_ton_wallet(deal_data.get('recipient_address', 'N/A'), 'N/A')

            await callback.bot.send_message(
                chat_id=recipient_user['user_id'],
                text=translator.get_message('ru', 'user_transfer_received',
                    sender_username=escaped_username,
                    amount=deal_data['amount'],
                    currency=deal_data['currency'],
                    date=current_date,
                    recipient_address=formatted_wallet,
                    deal_id=deal_id
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            print(translator.get_message('ru', 'admin_notify_recipient_error', user_id=recipient_user['user_id'], error=e))


@router.callback_query(F.data.startswith("admin_decline_deal:"))
async def admin_decline_deal_handler(callback: CallbackQuery) -> None:
    """
    Обработчик для кнопки 'Отклонить' в чате администратора.
    Возвращает средства на баланс отправителя.
    """
    deal_id = int(callback.data.split(':')[1])
    deal_data = db.get_deal_by_id(deal_id)

    if not deal_data or deal_data['status'] != 'pending':
        await callback.answer(translator.get_message('ru', 'admin_request_already_processed'), show_alert=True)
        return

    # 1. Обновляем статус сделки в БД
    db.update_deal_status(deal_id, 'declined')

    # 2. ВОЗВРАЩАЕМ СРЕДСТВА НА БАЛАНС ОТПРАВИТЕЛЯ
    db.update_user_balance(deal_data['sender_id'], deal_data['amount'])

    # 3. Уведомляем администратора
    await callback.message.edit_text(
        translator.get_message('ru', 'admin_request_declined',
            sender_id=deal_data['sender_id'],
            amount=deal_data['amount'],
            currency=deal_data['currency'],
            username=callback.from_user.username or 'N/A'
        )
    )
    await callback.answer(translator.get_message('ru', 'admin_request_declined_alert'))

    # 4. Уведомляем отправителя
    try:
        current_balance = db.get_user_balance(deal_data['sender_id'])
        await callback.bot.send_message(
            chat_id=deal_data['sender_id'],
            text=translator.get_message('ru', 'user_request_declined',
                amount=deal_data['amount'],
                currency=deal_data['currency'],
                current_balance=current_balance
            )
        )
    except Exception as e:
        print(translator.get_message('ru', 'admin_notify_sender_error', user_id=deal_data['sender_id'], error=e))


@router.callback_query(P2PStates.waiting_for_confirmation, F.data == "decline_deal")
async def decline_deal_handler(callback: CallbackQuery, state: FSMContext) -> None:
    # --- ИЗМЕНЕНИЕ: Используем edit_caption для обновления фото-сообщения ---
    user_data = db.get_user_data(callback.from_user.id)
    lang = user_data.get('language', 'ru')
    await callback.message.edit_caption(caption=translator.get_message(lang, 'p2p_deal_canceled'))
    await state.clear()
    await callback.answer()
