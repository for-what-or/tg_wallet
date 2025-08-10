import json
from pathlib import Path
from typing import Dict, Any

class Translator:
    def __init__(self):
        self.locales: Dict[str, Dict[str, Any]] = {}
        self.load_locales()
    
    def load_locales(self):
        locales_dir = Path(__file__).parent
        for file in locales_dir.glob("*.json"):
            lang = file.stem
            with open(file, 'r', encoding='utf-8') as f:
                self.locales[lang] = json.load(f)
    
    def get_message(self, lang: str, key: str, **kwargs) -> str:
        """Получает сообщение с подстановкой переменных"""
        message = self.locales.get(lang, {}).get('messages', {}).get(key, key)
        return message.format(**kwargs)
    
    def get_button(self, lang: str, key: str) -> str:
        """Получает текст для кнопки"""
        return self.locales.get(lang, {}).get('buttons', {}).get(key, key)

translator = Translator()