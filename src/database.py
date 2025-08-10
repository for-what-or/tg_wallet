from typing import Dict, Optional
import sqlite3
from pathlib import Path

class UserDatabase:
    """
    Класс для управления базой данных пользователей.
    """
    def __init__(self, db_path: str = "users.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Создает таблицу users, если она не существует."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    ton_wallet TEXT,
                    ton_wallet_test TEXT,
                    card_number TEXT,
                    language TEXT DEFAULT 'ru',
                    balance REAL DEFAULT 0,
                    deals_count INTEGER DEFAULT 0,
                    ref_count INTEGER DEFAULT 0
                )
            """)
            conn.commit()

    def register_new_user(self, user_id: int, username: str, full_name: str, language: str = 'ru'):
        """Регистрирует нового пользователя, если он не существует."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO users (user_id, username, full_name, language)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, full_name, language))
            conn.commit()

    def get_user_data(self, user_id: int) -> Optional[Dict]:
        """Возвращает все данные пользователя по ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_ton_wallet(self, user_id: int, wallet_address: str):
        """Обновляет адрес TON-кошелька пользователя."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET ton_wallet = ? WHERE user_id = ?",
                           (wallet_address, user_id))
            conn.commit()

    def update_card_number(self, user_id: int, card_number: str):
        """Обновляет номер банковской карты пользователя."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET card_number = ? WHERE user_id = ?",
                           (card_number, user_id))
            conn.commit()

    def update_language(self, user_id: int, language: str):
        """Обновляет язык пользователя."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET language = ? WHERE user_id = ?",
                           (language, user_id))
            conn.commit()

    def get_user_language(self, user_id: int) -> str:
        """Возвращает язык пользователя или 'ru' по умолчанию."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            return result[0] if result else 'ru'
    
    def user_exists(self, user_id: int) -> bool:
        """Проверяет, существует ли пользователь в базе данных."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
            return cursor.fetchone() is not None

# Инициализация базы данных
db = UserDatabase()
