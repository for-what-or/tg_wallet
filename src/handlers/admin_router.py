# admin_router.py

from aiogram import html, F, Router
from aiogram.filters import BaseFilter, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.config import ADMINS_LIST
from src.database import db # Импортируем наш объект БД
from src.states import AdminP2PStates # Импортируем состояния

admin_router = Router()

class IsAdmin(BaseFilter):
    def __init__(self) -> None:
        self.admin_ids = ADMINS_LIST
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in self.admin_ids

"""@admin_router.message(IsAdmin(), Command('start'))
async def admin_start_handler(message: Message) -> None:
    await message.answer(f"Привет, администратор {html.bold(message.from_user.full_name)}!")"""

@admin_router.message(IsAdmin(), Command('admin'))
async def admin_handler(message: Message) -> None:
    builder = InlineKeyboardBuilder()
    builder.button(text="Управление P2P", callback_data="admin_p2p_manage")
    # Сюда можно добавить другие админские кнопки
    builder.adjust(1)
    await message.answer("Админ панель:", reply_markup=builder.as_markup())

# --- Управление P2P ---

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

@admin_router.callback_query(IsAdmin(), F.data == "back_to_admin_panel")
async def back_to_admin_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await admin_handler(callback.message) # Вызываем главный обработчик админки
    await callback.answer()


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
    # Возвращаемся в меню управления P2P
    # Для этого нам нужен объект CallbackQuery, но у нас его нет.
    # Поэтому просто вызовем меню заново.
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
    await state.set_state(AdminP2PStates.waiting_for_pair_to_remove)
    await callback.message.edit_text("Выберите пару для удаления:", reply_markup=builder.as_markup())

@admin_router.callback_query(IsAdmin(), AdminP2PStates.waiting_for_pair_to_remove, F.data.startswith("confirm_remove_pair_"))
async def remove_pair_confirm(callback: CallbackQuery, state: FSMContext):
    pair_name = callback.data.split('_', 3)[-1]
    db.remove_p2p_pair(pair_name)
    await callback.answer(f"Пара {pair_name} и все ее листинги удалены.", show_alert=True)
    await state.clear()
    # Обновляем меню
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
    await state.set_state(AdminP2PStates.choosing_pair_for_listing)
    await callback.message.edit_text("Выберите пару для управления листингами:", reply_markup=builder.as_markup())

@admin_router.callback_query(IsAdmin(), AdminP2PStates.choosing_pair_for_listing, F.data.startswith("select_listing_pair_"))
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
    
    # Возвращаемся в меню управления листингами для этой пары
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
    
    # Возвращаемся в меню управления листингами для этой пары
    await select_listing_pair(callback, state)