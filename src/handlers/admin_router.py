from aiogram import html, F, Router
from aiogram.filters import BaseFilter, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from src.locales import translator

# --- ИЗМЕНЕНИЕ 1: Добавлен импорт нового разрешения ---
from src.config import ADMINS_LIST, ADMIN_GROUPS, CAN_EDIT_USERS
from src.database import db # Импортируем наш объект БД
from src.states import AdminP2PStates, AdminUserManagement # Импортируем оба класса состояний

admin_router = Router()

class IsAdmin(BaseFilter):
    def __init__(self) -> None:
        self.admin_ids = ADMINS_LIST
        self.admin_groups = ADMIN_GROUPS
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user_id = event.from_user.id
        chat_id = 0
        if isinstance(event, Message) and event.chat:
            chat_id = event.chat.id
        elif isinstance(event, CallbackQuery) and event.message and event.message.chat:
            chat_id = event.message.chat.id
        return user_id in self.admin_ids or chat_id in self.admin_groups


@admin_router.message(IsAdmin(), Command('admin'))
@admin_router.callback_query(IsAdmin(), F.data == "back_to_admin_panel")
async def admin_handler(event: Message | CallbackQuery, state: FSMContext):
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.button(text="Управление P2P", callback_data="admin_p2p_manage")
    builder.button(text="👥 Управление пользователями", callback_data="admin_user_manage")
    builder.adjust(1)
    
    text = "Админ панель:"
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=builder.as_markup())
        await event.answer()
    else:
        await event.answer(text, reply_markup=builder.as_markup())


# ######################################################################
# <<< БЛОК УПРАВЛЕНИЯ ПОЛЬЗОВАТЕЛЯМИ >>>
# ######################################################################

@admin_router.callback_query(IsAdmin(), F.data == "admin_user_manage")
async def user_manage_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminUserManagement.waiting_for_user_id)
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="back_to_admin_panel")
    await callback.message.edit_text(
        "Введите Telegram ID пользователя для просмотра.",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@admin_router.message(IsAdmin(), AdminUserManagement.waiting_for_user_id)
async def user_id_received(message: Message, state: FSMContext):
    if not message.text or not message.text.isdigit():
        await message.answer("❗️ Ошибка: ID должен быть числом. Попробуйте еще раз.")
        return

    user_id = int(message.text)
    user_data = db.get_user_data(user_id)

    if not user_data:
        await message.answer(f"❗️ Пользователь с ID `{user_id}` не найден. Попробуйте еще раз.")
        return
    
    await state.update_data(current_user_id=user_id)
    await show_user_profile(message, state, user_id)


async def show_user_profile(event: Message | CallbackQuery, state: FSMContext, user_id: int):
    """Хелпер для отображения профиля пользователя и кнопок редактирования."""
    user_data = db.get_user_data(user_id)
    if not user_data:
        text_error = f"❗️ Не удалось получить данные для пользователя {user_id}."
        if isinstance(event, Message):
            await event.answer(text_error)
        else:
            await event.message.edit_text(text_error)
        return
    
    escaped_username = user_data.get('username', 'N/A').replace('_', '\\_')

    profile_text = f"👤 Профиль пользователя: `{user_data['user_id']}`\n\n"
    profile_text += f"▪️ Username: @{escaped_username}\n"
    profile_text += f"▪️ Full Name: {html.quote(user_data.get('full_name', 'N/A'))}\n"
    profile_text += f"▪️ Язык: {user_data.get('language', 'N/A')}\n"
    profile_text += f"💰 Баланс: `{user_data.get('balance', 0)}`\n"
    profile_text += f"🤝 Сделок: `{user_data.get('deals_count', 0)}`\n"
    profile_text += f"🗣️ Рефералов: `{user_data.get('ref_count', 0)}`\n"
    profile_text += f"💳 Карта: `{user_data.get('card_number') or 'не указана'}`\n"
    profile_text += f"💎 TON Mainnet: `{user_data.get('ton_wallet') or 'не указан'}`\n"

    builder = InlineKeyboardBuilder()
    
    # --- ИЗМЕНЕНИЕ 2: Кнопки редактирования добавляются только при наличии разрешения ---
    if CAN_EDIT_USERS:
        fields_to_edit = {
            "balance": "💰 Баланс", "deals_count": "🤝 Сделки", "ref_count": "🗣️ Рефералы",
            "card_number": "💳 Карта", "ton_wallet": "💎 TON Mainnet", "ton_wallet_test": "🧪 TON Testnet",
            "language": "🌐 Язык"
        }
        for field, text in fields_to_edit.items():
            builder.button(text=f"✏️ {text}", callback_data=f"edit_user_{field}")
        builder.adjust(2)

    builder.row(InlineKeyboardButton(text="⬅️ Назад к вводу ID", callback_data="admin_user_manage"))

    await state.set_state(AdminUserManagement.viewing_user_profile)
    
    if isinstance(event, Message):
        await event.answer(profile_text, reply_markup=builder.as_markup(), parse_mode='Markdown')
    elif isinstance(event, CallbackQuery):
        await event.message.edit_text(profile_text, reply_markup=builder.as_markup(), parse_mode='Markdown')
        await event.answer()


@admin_router.callback_query(IsAdmin(), AdminUserManagement.viewing_user_profile, F.data.startswith("edit_user_"))
async def edit_user_field_start(callback: CallbackQuery, state: FSMContext):
    # --- ИЗМЕНЕНИЕ 3: Проверка разрешения перед началом редактирования ---
    if not CAN_EDIT_USERS:
        await callback.answer("⛔️ Редактирование пользователей отключено.", show_alert=True)
        return

    field_to_edit = callback.data.split("edit_user_")[-1]
    
    await state.update_data(field_to_edit=field_to_edit)
    await state.set_state(AdminUserManagement.editing_field)

    prompts = {
        "balance": "Введите новый баланс (число):",
        "deals_count": "Введите новое количество сделок (целое число):",
        "ref_count": "Введите новое количество рефералов (целое число):",
        "card_number": "Введите новый номер карты (или 'None' для очистки):",
        "ton_wallet": "Введите новый адрес кошелька TON Mainnet (или 'None' для очистки):",
        "ton_wallet_test": "Введите новый адрес кошелька TON Testnet (или 'None' для очистки):",
        "language": "Введите новый язык (например, ru или en):"
    }
    
    builder = InlineKeyboardBuilder()
    data = await state.get_data()
    builder.button(text="⬅️ Отмена", callback_data=f"cancel_edit_{data.get('current_user_id')}")

    await callback.message.edit_text(
        f"✏️ {prompts.get(field_to_edit, 'Введите новое значение:')}",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@admin_router.callback_query(IsAdmin(), AdminUserManagement.editing_field, F.data.startswith("cancel_edit_"))
async def edit_user_field_cancel(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split('_')[-1])
    await callback.answer("Редактирование отменено.")
    await show_user_profile(callback, state, user_id)


@admin_router.message(IsAdmin(), AdminUserManagement.editing_field)
async def edit_user_field_process(message: Message, state: FSMContext):
    # --- ИЗМЕНЕНИЕ 4: Дополнительная проверка разрешения ---
    if not CAN_EDIT_USERS:
        return # Просто игнорируем, если редактирование отключено

    data = await state.get_data()
    user_id = data.get("current_user_id")
    field = data.get("field_to_edit")
    new_value_str = message.text

    if new_value_str.lower() == 'none':
        new_value = None
    else:
        new_value = new_value_str

    if field in ["balance"] and new_value is not None:
        try:
            new_value = float(new_value_str)
        except ValueError:
            await message.answer("❗️ Ошибка: Баланс должен быть числом. Попробуйте еще раз.")
            return
    elif field in ["deals_count", "ref_count"] and new_value is not None:
        if not new_value_str.isdigit():
            await message.answer("❗️ Ошибка: Это поле должно быть целым числом. Попробуйте еще раз.")
            return
        new_value = int(new_value_str)

    db.update_user_data(user_id, {field: new_value})
    
    await message.answer(f"✅ Поле `{field}` для пользователя `{user_id}` успешно обновлено.")
    
    await show_user_profile(message, state, user_id)


# ######################################################################
# <<< КОНЕЦ БЛОКА УПРАВЛЕНИЯ ПОЛЬЗОВАТЕЛЯМИ >>>
# ######################################################################


# --- Управление P2P ---
# (остальной код без изменений)

@admin_router.callback_query(IsAdmin(), F.data == "admin_p2p_manage")
async def p2p_manage_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить пару", callback_data="admin_p2p_add_pair")
    builder.button(text="➖ Удалить пару", callback_data="admin_p2p_remove_pair")
    builder.button(text="📊 Управление листингами", callback_data="admin_p2p_manage_listings")
    builder.button(text="⬅️ Назад в админ-панель", callback_data="back_to_admin_panel")
    builder.adjust(2, 1, 1)
    await callback.message.edit_text("Управление P2P-обменником:", reply_markup=builder.as_markup())


# --- Добавление пары ---

@admin_router.callback_query(IsAdmin(), F.data == "admin_p2p_add_pair")
async def add_pair_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminP2PStates.waiting_for_pair_to_add)
    await callback.message.edit_text("Введите название новой пары в формате ВАЛЮТА1_ВАЛЮТА2 (например, TON_RUB).")
    await callback.answer()

@admin_router.message(IsAdmin(), AdminP2PStates.waiting_for_pair_to_add)
async def add_pair_process(message: Message, state: FSMContext):
    pair_name = message.text.upper()
    if db.add_p2p_pair(pair_name):
        await message.answer(f"✅ Пара {pair_name} успешно добавлена.")
    else:
        await message.answer(f"⚠️ Пара {pair_name} уже существует.")
    await state.clear()
    
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад в меню P2P", callback_data="admin_p2p_manage")
    await message.answer("Выберите следующее действие:", reply_markup=builder.as_markup())


# --- Удаление пары ---

@admin_router.callback_query(IsAdmin(), F.data == "admin_p2p_remove_pair")
async def remove_pair_start(callback: CallbackQuery, state: FSMContext):
    pairs = db.get_all_p2p_pairs()
    if not pairs:
        await callback.answer("Нет созданных пар для удаления.", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    for pair in pairs:
        builder.button(text=f"❌ {pair}", callback_data=f"confirm_remove_pair_{pair}")
    builder.button(text="⬅️ Отмена", callback_data="admin_p2p_manage")
    builder.adjust(1)
    await callback.message.edit_text("Выберите пару для удаления:", reply_markup=builder.as_markup())

@admin_router.callback_query(IsAdmin(), F.data.startswith("confirm_remove_pair_"))
async def remove_pair_confirm(callback: CallbackQuery, state: FSMContext):
    pair_name = callback.data.split('_', 3)[-1]
    db.remove_p2p_pair(pair_name)
    await callback.answer(f"Пара {pair_name} и все ее листинги удалены.", show_alert=True)
    await state.clear()
    await p2p_manage_menu(callback, state)


# --- Управление листингами ---

@admin_router.callback_query(IsAdmin(), F.data == "admin_p2p_manage_listings")
async def manage_listings_start(callback: CallbackQuery, state: FSMContext):
    pairs = db.get_all_p2p_pairs()
    if not pairs:
        await callback.answer("Сначала создайте хотя бы одну валютную пару.", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for pair in pairs:
        builder.button(text=pair, callback_data=f"select_listing_pair_{pair}")
    builder.button(text="⬅️ Назад", callback_data="admin_p2p_manage")
    builder.adjust(2)
    await callback.message.edit_text("Выберите пару для управления листингами:", reply_markup=builder.as_markup())

@admin_router.callback_query(IsAdmin(), F.data.startswith("select_listing_pair_"))
async def select_listing_pair(callback: CallbackQuery, state: FSMContext):
    pair_name = callback.data.split('_', 3)[-1]
    await state.update_data(current_pair=pair_name)
    
    listings = db.get_p2p_listings(pair_name)
    text = f"Управление листингами для пары *{pair_name}*\n\n"
    if not listings:
        text += "Пока нет активных листингов."
    else:
        text += "Текущие листинги:\n"
        for l in listings:
            text += f"ID: `{l['id']}` | {l['nickname']} | {l['action']} | {l['price']} | Лимит: {l['limit']}\n"
            
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить листинг", callback_data="add_listing_start")
    builder.button(text="➖ Удалить листинг", callback_data="remove_listing_start")
    builder.button(text="⬅️ Выбрать другую пару", callback_data="admin_p2p_manage_listings")
    builder.adjust(2, 1)
    
    await state.set_state(AdminP2PStates.choosing_listing_action)
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")


# --- Удаление листинга ---

@admin_router.callback_query(IsAdmin(), AdminP2PStates.choosing_listing_action, F.data == "remove_listing_start")
async def remove_listing_start(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    pair_name = data.get("current_pair")
    listings = db.get_p2p_listings(pair_name)
    
    if not listings:
        await callback.answer("Нет листингов для удаления в этой паре.", show_alert=True)
        return
        
    builder = InlineKeyboardBuilder()
    for l in listings:
        builder.button(
            text=f"❌ ID: {l['id']} ({l['nickname']})", 
            callback_data=f"confirm_remove_listing_{l['id']}"
        )
    builder.button(text="⬅️ Назад", callback_data=f"select_listing_pair_{pair_name}")
    builder.adjust(1)
    
    await state.set_state(AdminP2PStates.waiting_for_listing_to_remove)
    await callback.message.edit_text("Выберите листинг для удаления:", reply_markup=builder.as_markup())


@admin_router.callback_query(IsAdmin(), AdminP2PStates.waiting_for_listing_to_remove, F.data.startswith("confirm_remove_listing_"))
async def remove_listing_confirm(callback: CallbackQuery, state: FSMContext):
    listing_id = int(callback.data.split('_')[-1])
    db.remove_p2p_listing(listing_id)
    await callback.answer("Листинг удален.", show_alert=True)
    
    await select_listing_pair(callback, state)


# --- Добавление листинга (цепочка FSM) ---

@admin_router.callback_query(IsAdmin(), AdminP2PStates.choosing_listing_action, F.data == "add_listing_start")
async def add_listing_nickname(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminP2PStates.waiting_for_listing_nickname)
    await callback.message.edit_text("Шаг 1/4: Введите никнейм продавца/покупателя.")
    await callback.answer()

@admin_router.message(IsAdmin(), AdminP2PStates.waiting_for_listing_nickname)
async def add_listing_price(message: Message, state: FSMContext):
    await state.update_data(nickname=message.text)
    await state.set_state(AdminP2PStates.waiting_for_listing_price)
    await message.answer("Шаг 2/4: Введите цену (например, '4.40594$' или '0.0001 BTC').")

@admin_router.message(IsAdmin(), AdminP2PStates.waiting_for_listing_price)
async def add_listing_limit(message: Message, state: FSMContext):
    await state.update_data(price=message.text)
    await state.set_state(AdminP2PStates.waiting_for_listing_limit)
    await message.answer("Шаг 3/4: Введите лимит (например, '10 TON').")

@admin_router.message(IsAdmin(), AdminP2PStates.waiting_for_listing_limit)
async def add_listing_action(message: Message, state: FSMContext):
    await state.update_data(limit=message.text)
    await state.set_state(AdminP2PStates.waiting_for_listing_action)
    builder = InlineKeyboardBuilder()
    builder.button(text="Продажа", callback_data="add_listing_action_продажа")
    builder.button(text="Покупка", callback_data="add_listing_action_покупка")
    await message.answer("Шаг 4/4: Выберите действие:", reply_markup=builder.as_markup())

@admin_router.callback_query(IsAdmin(), AdminP2PStates.waiting_for_listing_action, F.data.startswith("add_listing_action_"))
async def add_listing_finish(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split('_')[-1]
    await state.update_data(action=action)
    
    data = await state.get_data()
    db.add_p2p_listing(
        pair_name=data['current_pair'],
        nickname=data['nickname'],
        price=data['price'],
        limit=data['limit'],
        action=data['action']
    )
    
    await callback.message.edit_text(f"✅ Листинг для пары {data['current_pair']} успешно добавлен.")
    await callback.answer()
    
    await select_listing_pair(callback, state)

# --- Команда /addvip (для администраторов) ---
@admin_router.message(Command("addvip"))
async def grant_balance_access(message: Message) -> None:
    """
    Обработчик для команды /addvip, доступной только администраторам.
    Выдает пользователю разрешение на пополнение баланса на определенное время.
    """
    user_id = message.from_user.id
    # Проверяем, является ли пользователь администратором
    if user_id not in ADMINS_LIST:
        return

    args = message.text.split()
    if len(args) != 3:
        await message.answer("Использование: /addvip <user_id> <длительность_в_днях>")
        return

    try:
        target_user_id = int(args[1])
        duration_days = int(args[2])
    except ValueError:
        await message.answer("Неверный формат. ID пользователя и длительность должны быть числами.")
        return

    # Выдача разрешения через базу данных
    db.grant_balance_permission(target_user_id, duration_days)

    # Уведомление администратора
    await message.answer(f"Пользователю с ID {target_user_id} выдано разрешение на пополнение баланса на {duration_days} д.")

    # Уведомление пользователя
    try:
        notification_text = translator.get_message('ru', 'balance_permission_granted', duration=duration_days)
        await message.bot.send_message(
            chat_id=target_user_id,
            text=notification_text,
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"Не удалось уведомить пользователя {target_user_id}: {e}")

# --- Команда /rmvip (для администраторов) ---
@admin_router.message(Command("rmvip"))
async def revoke_balance_access(message: Message) -> None:
    """
    Обработчик для команды /rmvip, доступной только администраторам.
    Забирает у пользователя разрешение на пополнение баланса.
    """
    user_id = message.from_user.id
    # Проверяем, является ли пользователь администратором
    if user_id not in ADMINS_LIST:
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("Использование: /rmvip <user_id>")
        return

    try:
        target_user_id = int(args[1])
    except ValueError:
        await message.answer("Неверный формат. ID пользователя должен быть числом.")
        return

    # Отзыв разрешения через базу данных
    db.revoke_balance_permission(target_user_id)

    # Уведомление администратора
    await message.answer(f"У пользователя с ID {target_user_id} отозвано разрешение на пополнение баланса.")

    # Уведомление пользователя
    try:
        notification_text = translator.get_message('ru', 'balance_permission_revoked')
        await message.bot.send_message(
            chat_id=target_user_id,
            text=notification_text,
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"Не удалось уведомить пользователя {target_user_id}: {e}")
