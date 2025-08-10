from os import getenv
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

load_dotenv(override=True)
BOT_TOKEN = getenv("BOT_TOKEN")
ADMINS_LIST = list(map(int, getenv("ADMINS_LIST").split(",")))
storage = MemoryStorage()

dp = Dispatcher(storage=storage)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))