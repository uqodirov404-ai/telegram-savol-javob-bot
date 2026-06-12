import os
from dotenv import load_dotenv

load_dotenv()

# Telegram bot tokeni — .env faylidan o'qiladi
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN .env faylida topilmadi! .env.example faylini ko'ring.")

# PostgreSQL bazasi URL manzili
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Asosiy admin (bot egasi) ID si
ADMIN_ID = os.environ.get("ADMIN_ID", "")
if ADMIN_ID:
    ADMIN_ID = int(ADMIN_ID)
