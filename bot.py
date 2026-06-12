"""
Telegram Savol-Javob Bot
========================
Guruhda sessiya davomida kim necha marta xabar yuborganini kuzatadi.
Sessiya tugaganda qatnashganlar va qatnashmaganlar statistikasi chiqariladi.

Buyruqlar:
  /boshladik  — Admin, sessiyani boshlaydi
  /yakunladik — Admin, sessiyani to'xtatadi va statistikani chiqaradi
  /holat      — Admin, joriy holat
"""

import logging
import html
import os
import threading
from datetime import datetime

from flask import Flask
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ChatMemberStatus, ParseMode

from config import BOT_TOKEN
import database as db

# -----------------------------------------------------------------
# Logging
# -----------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------
# Health check server (Render uxlab qolmasligi uchun)
# -----------------------------------------------------------------
flask_app = Flask(__name__)

@flask_app.route("/health")
def health():
    return "OK", 200

@flask_app.route("/")
def index():
    return "Bot ishlayapti! ✅", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)


# -----------------------------------------------------------------
# Yordamchi funksiyalar
# -----------------------------------------------------------------

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Xabar yuboruvchi guruh admin yoki egasimi tekshiradi."""
    member = await context.bot.get_chat_member(
        update.effective_chat.id,
        update.effective_user.id,
    )
    return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)


def esc(text: str) -> str:
    """HTML maxsus belgilarini xavfsiz ko'rinishga o'tkazadi."""
    return html.escape(str(text))


def format_username(row: dict) -> str:
    """Foydalanuvchi nomini formatlaydi: @username yoki Ism Familiya."""
    if row.get("username"):
        return f"@{esc(row['username'])}"
    parts = []
    if row.get("first_name"):
        parts.append(esc(row["first_name"]))
    if row.get("last_name"):
        parts.append(esc(row["last_name"]))
    return " ".join(parts) if parts else f"User#{row['user_id']}"


def duration_text(started_at: str, ended_at: str) -> str:
    """Sessiya davomiyligini o'qiladigan matn ko'rinishida qaytaradi."""
    fmt = "%Y-%m-%dT%H:%M:%S.%f"
    try:
        start = datetime.strptime(started_at[:26], fmt)
        end = datetime.strptime(ended_at[:26], fmt)
    except ValueError:
        fmt2 = "%Y-%m-%dT%H:%M:%S"
        start = datetime.strptime(started_at[:19], fmt2)
        end = datetime.strptime(ended_at[:19], fmt2)

    delta = end - start
    total_seconds = int(delta.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if hours:
        parts.append(f"{hours} soat")
    if minutes:
        parts.append(f"{minutes} daqiqa")
    if seconds or not parts:
        parts.append(f"{seconds} soniya")
    return " ".join(parts)


MEDALS = ["🥇", "🥈", "🥉"]

OGOHLANTIRISH = """⚠️ <b>Online darsdagi ishtirok bo'yicha ogohlantirish</b>

Hurmatli darsda qatnashmaganlar,

Bugungi online darsda ishtirok etmaganingiz aniqlandi. O'quv jarayonidagi uzilishlar o'zlashtirish darajasiga salbiy ta'sir ko'rsatishi va akademik natijalaringizni pasaytirishi mumkinligini eslatib o'tmoqchiman.

Dars qoldirishning uzrli sababi bo'lsa, tegishli ma'lumotlarni taqdim etishingizni, aks holda, kelgusida bunday holat takrorlanmasligi kerakligini ma'lum qilaman. O'tkazib yuborilgan mavzularni mustaqil o'zlashtirib olishingiz va topshiriqlarni belgilangan muddatda topshirishingiz shart."""


def build_stats_message(session: dict, stats: list[dict],
                        total: int, absent: list[dict]) -> str:
    """Statistika xabarini HTML formatda tuzadi."""
    dur = duration_text(session["started_at"], session["ended_at"])
    participant_count = len(stats)

    lines = [
        "📊 <b>Sessiya Statistikasi</b>",
        f"⏱ Dars davomiyligi: <b>{dur}</b>",
        "",
        "🏆 <b>Eng faol ishtirokchilar:</b>",
    ]

    for i, row in enumerate(stats):
        medal = MEDALS[i] if i < len(MEDALS) else f"{i + 1}."
        name = format_username(row)
        lines.append(f"{medal} {name} — <b>{row['message_count']}</b>")

    lines += [
        "",
        f"👥 Jami ishtirokchilar: <b>{participant_count}</b> nafar",
    ]

    if absent:
        lines.append("")
        lines.append(f"😶 <b>Darsda ishtirok etmaganlar ({len(absent)} nafar):</b>")
        for row in absent:
            name = format_username(row)
            lines.append(f"• {name}")

    lines += [
        "",
        "📌 <i>Qatnashmaganlar diqqatiga: Natija osmondan tushmaydi.</i>",
    ]

    return "\n".join(lines)


# -----------------------------------------------------------------
# Handler-lar
# -----------------------------------------------------------------

async def cmd_boshladik(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text("❗ Bu buyruq faqat guruhlarda ishlaydi.")
        return

    if not await is_admin(update, context):
        await update.message.reply_text("❌ Faqat guruh adminlari sessiyani boshlay oladi.")
        return

    existing = db.get_active_session(chat.id)
    if existing:
        await update.message.reply_text(
            "⚠️ Sessiya allaqachon boshlangan!\n"
            "To'xtatish uchun /yakunladik deb yozing."
        )
        return

    db.start_session(chat.id)
    logger.info("Sessiya boshlandi: chat_id=%s, admin=%s", chat.id, user.id)

    await update.message.reply_text(
        "✅ <b>Sessiya boshlandi!</b>\n\n"
        "Endi barcha xabarlar hisoblanadi.\n"
        "To'xtatish uchun /yakunladik deb yozing.",
        parse_mode=ParseMode.HTML,
    )


async def cmd_yakunladik(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text("❗ Bu buyruq faqat guruhlarda ishlaydi.")
        return

    if not await is_admin(update, context):
        await update.message.reply_text("❌ Faqat guruh adminlari sessiyani yakunlay oladi.")
        return

    session = db.end_session(chat.id)
    if not session:
        await update.message.reply_text(
            "⚠️ Hozir aktiv sessiya yo'q.\n"
            "Boshlash uchun /boshladik deb yozing."
        )
        return

    logger.info("Sessiya yakunlandi: chat_id=%s, session_id=%s", chat.id, session["id"])

    stats = db.get_session_stats(session["id"])
    total = db.get_session_total_messages(session["id"])
    absent = db.get_absent_members(chat.id, session["id"])

    if not stats:
        await update.message.reply_text(
            "📊 Sessiya yakunlandi, lekin hech kim xabar yozmadi."
        )
        return

    message = build_stats_message(session, stats, total, absent)
    await update.message.reply_text(message, parse_mode=ParseMode.HTML)

    if absent:
        await update.message.reply_text(OGOHLANTIRISH, parse_mode=ParseMode.HTML)


async def cmd_holat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text("❗ Bu buyruq faqat guruhlarda ishlaydi.")
        return

    if not await is_admin(update, context):
        await update.message.reply_text("❌ Faqat guruh adminlari holatni ko'ra oladi.")
        return

    session = db.get_active_session(chat.id)
    if not session:
        await update.message.reply_text(
            "🔴 Hozir aktiv sessiya yo'q.\n"
            "Boshlash uchun /boshladik deb yozing."
        )
        return

    total = db.get_session_total_messages(session["id"])
    stats = db.get_session_stats(session["id"])
    participant_count = len(stats)

    await update.message.reply_text(
        f"🟢 <b>Sessiya faol</b>\n"
        f"👥 Ishtirokchilar: <b>{participant_count}</b> nafar\n"
        f"💬 Xabarlar: <b>{total}</b> ta",
        parse_mode=ParseMode.HTML,
    )


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if chat.type not in ("group", "supergroup"):
        return

    if user is None or user.is_bot:
        return

    if message and message.text and message.text.startswith("/"):
        return

    db.upsert_member(
        chat_id=chat.id,
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
    )

    session = db.get_active_session(chat.id)
    if not session:
        return

    db.record_message(
        session_id=session["id"],
        chat_id=chat.id,
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
    )


# -----------------------------------------------------------------
# Asosiy funksiya
# -----------------------------------------------------------------

def main():
    db.init_db()
    logger.info("Baza tayyor. Bot ishga tushmoqda...")

    # Flask health serverini alohida threadda ishga tushiramiz
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Health server ishga tushdi.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("boshladik", cmd_boshladik))
    app.add_handler(CommandHandler("yakunladik", cmd_yakunladik))
    app.add_handler(CommandHandler("holat", cmd_holat))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    logger.info("Bot ishga tushdi. To'xtatish uchun Ctrl+C bosing.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
