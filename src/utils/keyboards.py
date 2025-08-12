from aiogram.types import InlineKeyboardMarkup
from src.locales import translator
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру главного меню.
    """
    builder_start = InlineKeyboardBuilder()
    builder_start.button(text=translator.get_button(lang, 'profile'), callback_data="profile")
    #builder_start.button(text=translator.get_button(lang, 'add_wallet'), callback_data="add_change_wallet")
    builder_start.button(text=translator.get_button(lang, 'create_deal'), callback_data="create_deal")
    #builder_start.button(text=translator.get_button(lang, 'ref_link'), callback_data="ref_link")
    # Новая кнопка для P2P-обмена
    builder_start.button(text=translator.get_button(lang, 'p2p'), callback_data="p2p")
    builder_start.button(text=translator.get_button(lang, 'support'), callback_data="support")
    builder_start.button(text=translator.get_button(lang, 'about_us'), callback_data="about_us")
    builder_start.button(text=translator.get_button(lang, 'change_language'), callback_data="change_language")
    builder_start.adjust(1)
    return builder_start.as_markup()

def get_register_keyboard(lang: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для регистрации.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text=translator.get_button(lang, 'start_registration'), callback_data="register")
    builder.adjust(1)
    return builder.as_markup()
