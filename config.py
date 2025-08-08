from os import getenv
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

load_dotenv(override=True)
BOT_TOKEN = getenv("BOT_TOKEN")
ADMINS_LIST = list(map(int, getenv("ADMINS_LIST").split(",")))

dp = Dispatcher()
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

async def on_error(update, exception):
    for ADMIN in ADMINS_LIST:
        await bot.send_message(chat_id=ADMIN, text=f"Update {update} caused error {exception}")