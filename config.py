import os
from dotenv import load_dotenv

load_dotenv()

# Telegram bot tokeni — .env faylidan o'qiladi
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN .env faylida topilmadi! .env.example faylini ko'ring.")

# SQLite bazasi fayli
DB_PATH = os.getenv("DB_PATH", "sessions.db")
