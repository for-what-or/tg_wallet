from aiogram.fsm.state import State, StatesGroup

# Состояния для процесса регистрации
class RegistrationStates(StatesGroup):
    """
    Состояния, связанные с процессом регистрации пользователя.
    """
    waiting_for_name = State()


# Состояния для добавления/изменения TON-кошелька
class WalletStates(StatesGroup):
    """
    Состояния для добавления/изменения TON-кошелька.
    """
    waiting_for_wallet = State()


# Состояния для добавления/изменения банковской карты
class CardStates(StatesGroup):
    """
    Состояния для добавления/изменения банковской карты.
    """
    waiting_for_card = State()


# Состояния для смены языка
class LanguageStates(StatesGroup):
    """
    Состояния для выбора нового языка.
    """
    choosing_language = State()

