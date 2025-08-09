# database.py
from typing import Dict, Optional
import sqlite3
from pathlib import Path

class UserDatabase:
    def __init__(self, db_path: str = "users.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    ton_wallet TEXT,
                    card_number TEXT,
                    language TEXT DEFAULT 'ru',
                    balance REAL DEFAULT 0,
                    deals_count INTEGER DEFAULT 0,
                    ref_count INTEGER DEFAULT 0
                )
            """)
            conn.commit()

    def add_user(self, user_id: int, username: str, full_name: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO users (user_id, username, full_name)
                VALUES (?, ?, ?)
            """, (user_id, username, full_name))
            conn.commit()

    def get_user(self, user_id: int) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            return dict(cursor.fetchone()) if cursor.fetchone() else None

    def update_ton_wallet(self, user_id: int, wallet_address: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET ton_wallet = ?
                WHERE user_id = ?
            """, (wallet_address, user_id))
            conn.commit()

    def update_card(self, user_id: int, card_number: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET card_number = ?
                WHERE user_id = ?
            """, (card_number, user_id))
            conn.commit()

    def update_language(self, user_id: int, language: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET language = ?
                WHERE user_id = ?
            """, (language, user_id))
            conn.commit()

    def increment_deals(self, user_id: int):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET deals_count = deals_count + 1
                WHERE user_id = ?
            """, (user_id,))
            conn.commit()

    def increment_refs(self, user_id: int):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET ref_count = ref_count + 1
                WHERE user_id = ?
            """, (user_id,))
            conn.commit()

# Инициализация базы данных
db = UserDatabase()