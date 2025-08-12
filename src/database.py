# database.py

from typing import Dict, Optional, List
import sqlite3
from pathlib import Path

class UserDatabase:
    """
    Класс для управления базой данных пользователей и P2P-обменника.
    """
    def __init__(self, db_path: str = "users.db"):
        self.db_path = db_path
        self._init_db()
        self._init_p2p_tables() # Инициализируем таблицы для P2P

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

    def _init_p2p_tables(self):
        """Создает таблицы для P2P-обменника, если они не существуют."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Таблица для валютных пар
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS p2p_pairs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
                )
            """)
            # Таблица для листингов (предложений)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS p2p_listings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pair_id INTEGER NOT NULL,
                    nickname TEXT NOT NULL,
                    price TEXT NOT NULL,
                    "limit" TEXT NOT NULL,
                    action TEXT NOT NULL,
                    FOREIGN KEY (pair_id) REFERENCES p2p_pairs (id) ON DELETE CASCADE
                )
            """)
            conn.commit()
            
    # --- Методы для P2P ---

    def add_p2p_pair(self, pair_name: str) -> bool:
        """Добавляет новую валютную пару."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO p2p_pairs (name) VALUES (?)", (pair_name,))
                conn.commit()
            return True
        except sqlite3.IntegrityError: # Если пара уже существует
            return False

    def remove_p2p_pair(self, pair_name: str):
        """Удаляет валютную пару и все связанные с ней листинги."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Включаем поддержку внешних ключей для каскадного удаления
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("DELETE FROM p2p_pairs WHERE name = ?", (pair_name,))
            conn.commit()

    def get_all_p2p_pairs(self) -> List[str]:
        """Возвращает список всех валютных пар."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM p2p_pairs ORDER BY name")
            return [row[0] for row in cursor.fetchall()]

    def add_p2p_listing(self, pair_name: str, nickname: str, price: str, limit: str, action: str):
        """Добавляет новый листинг в указанную валютную пару."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM p2p_pairs WHERE name = ?", (pair_name,))
            pair_id_row = cursor.fetchone()
            if not pair_id_row:
                return # Пара не найдена
            
            pair_id = pair_id_row[0]
            cursor.execute("""
                INSERT INTO p2p_listings (pair_id, nickname, price, "limit", action)
                VALUES (?, ?, ?, ?, ?)
            """, (pair_id, nickname, price, limit, action))
            conn.commit()

    def remove_p2p_listing(self, listing_id: int):
        """Удаляет листинг по его ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM p2p_listings WHERE id = ?", (listing_id,))
            conn.commit()

    def get_p2p_listings(self, pair_name: str) -> List[Dict]:
        """Возвращает все листинги для указанной валютной пары."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT l.id, l.nickname, l.price, l."limit", l.action
                FROM p2p_listings l
                JOIN p2p_pairs p ON l.pair_id = p.id
                WHERE p.name = ?
            """, (pair_name,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
    # --- Методы для пользователей ---
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
            
    def update_user_data(self, user_id: int, data: Dict):
        """Обновляет данные пользователя на основе переданного словаря."""
        if not data:
            return
        
        set_clause = ", ".join([f"{key} = ?" for key in data.keys()])
        values = list(data.values())
        values.append(user_id)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE users SET {set_clause} WHERE user_id = ?", tuple(values))
            conn.commit()

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

    def get_p2p_listing_by_id(self, listing_id: int) -> Optional[Dict]:
        """Возвращает данные одного листинга по его ID, включая название пары."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT l.id, l.nickname, l.price, l."limit", l.action, p.name as pair_name
                FROM p2p_listings l
                JOIN p2p_pairs p ON l.pair_id = p.id
                WHERE l.id = ?
            """, (listing_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

# Инициализация базы данных
db = UserDatabase()