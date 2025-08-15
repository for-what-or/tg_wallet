from os import getenv
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

load_dotenv(override=True)
BOT_TOKEN = getenv("BOT_TOKEN")
ADMINS_LIST = list(map(int, getenv("ADMINS_LIST").split(",")))
ADMIN_GROUPS = list(map(int, getenv("ADMIN_GROUPS").split(",")))
CAN_EDIT_USERS = False
PHOTO_PATH = "pics/photo_1.jpg"

storage = MemoryStorage()

dp = Dispatcher(storage=storage)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))