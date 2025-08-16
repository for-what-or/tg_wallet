from aiogram.fsm.state import State, StatesGroup

class RegistrationStates(StatesGroup):
    """
    FSM-состояния для процесса регистрации.
    """
    waiting_for_name = State()

class WalletStates(StatesGroup):
    """
    FSM-состояния для добавления TON-кошелька.
    """
    waiting_for_wallet = State()

class CardStates(StatesGroup):
    """
    FSM-состояния для добавления банковской карты.
    """
    waiting_for_card = State()

class LanguageStates(StatesGroup):
    """
    FSM-состояния для выбора языка.
    """
    choosing_language = State()

class P2PStates(StatesGroup):
    """
    FSM-состояния для процесса P2P-сделки (со стороны пользователя).
    """
    waiting_for_recipient_type = State()
    waiting_for_recipient_wallet = State()
    waiting_for_recipient_card = State()
    waiting_for_amount = State()
    waiting_for_confirmation = State()

class AdminP2PStates(StatesGroup):
    """
    FSM-состояния для админ-панели управления P2P.
    """
    choosing_action = State() # Выбор действия (пары/листинги)
    
    # Состояния для пар
    waiting_for_pair_to_add = State()
    waiting_for_pair_to_remove = State()
    
    # Состояния для листингов
    choosing_pair_for_listing = State() # Выбор пары для управления листингами
    choosing_listing_action = State() # Добавить/удалить листинг
    waiting_for_listing_to_remove = State()
    
    # Цепочка добавления листинга
    waiting_for_listing_nickname = State()
    waiting_for_listing_price = State()
    waiting_for_listing_limit = State()
    waiting_for_listing_action = State()

class TopUpStates(StatesGroup):
    """
    FSM-состояния для процесса пополнения кошелька.
    """
    waiting_for_confirmation = State()
    waiting_for_amount = State()

# --- НОВЫЙ КЛАСС ДЛЯ УПРАВЛЕНИЯ ПОЛЬЗОВАТЕЛЯМИ ---
class AdminUserManagement(StatesGroup):
    """
    FSM-состояния для админ-панели управления пользователями.
    """
    waiting_for_user_id = State()      # Ожидание ввода ID пользователя
    viewing_user_profile = State()     # Просмотр профиля конкретного пользователя
    editing_field = State()            # Ожидание нового значения для поля

class SupportState(StatesGroup):
    waiting_for_message = State()

# Создаем группу состояний для диалога с администратором по поводу ответа
class AdminReplyState(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_reply_text = State()
