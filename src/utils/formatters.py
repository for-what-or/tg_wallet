# --- Вспомогательные функции для форматирования ---
def format_ton_wallet(wallet_address: str, placeholder: str) -> str:
    """
    Форматирует адрес TON-кошелька для скрытия его части.
    Например: EQAWzE...C6ISgcLo
    """
    # Добавлена проверка на None и пустую строку
    if not wallet_address or wallet_address == 'NULL':
        return placeholder
    
    # Показываем первые 8 и последние 8 символов
    if len(wallet_address) > 16:
        return f"{wallet_address[:8]}...{wallet_address[-8:]}"
    return wallet_address

def format_card_number(card_number: str, placeholder: str) -> str:
    """
    Форматирует номер карты для скрытия его части.
    Например: **** **** **** 1234
    """
    # Добавлена проверка на None и пустую строку
    if not card_number or card_number == 'NULL':
        return placeholder

    # Показываем только последние 4 цифры
    if len(card_number) >= 4:
        return f"**** **** **** {card_number[-4:]}"
    return card_number
