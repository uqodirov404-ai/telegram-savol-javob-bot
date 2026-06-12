import sqlite3
from datetime import datetime
from config import DB_PATH


def get_connection():
    """SQLite ulanishini qaytaradi."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Bazani ishga tushiradi va jadvallarni yaratadi."""
    conn = get_connection()
    cursor = conn.cursor()

    # Sessiyalar jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)

    # Xabarlar jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            sent_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)

    # Guruh a'zolari jadvali — xabar yozgan barcha foydalanuvchilar
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS group_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            last_seen TEXT NOT NULL,
            UNIQUE(chat_id, user_id)
        )
    """)

    conn.commit()
    conn.close()


def start_session(chat_id: int) -> int:
    """Yangi sessiyani boshlaydi. Sessiya ID sini qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE sessions SET is_active = 0, ended_at = ?
        WHERE chat_id = ? AND is_active = 1
    """, (datetime.now().isoformat(), chat_id))

    cursor.execute("""
        INSERT INTO sessions (chat_id, started_at, is_active)
        VALUES (?, ?, 1)
    """, (chat_id, datetime.now().isoformat()))

    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id


def end_session(chat_id: int) -> dict | None:
    """Aktiv sessiyani to'xtatadi. Sessiya ma'lumotlarini qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM sessions WHERE chat_id = ? AND is_active = 1
    """, (chat_id,))
    session = cursor.fetchone()

    if not session:
        conn.close()
        return None

    ended_at = datetime.now().isoformat()
    cursor.execute("""
        UPDATE sessions SET is_active = 0, ended_at = ?
        WHERE id = ?
    """, (ended_at, session["id"]))

    conn.commit()
    result = dict(session)
    result["ended_at"] = ended_at
    conn.close()
    return result


def get_active_session(chat_id: int) -> dict | None:
    """Guruhning aktiv sessiyasini qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM sessions WHERE chat_id = ? AND is_active = 1
    """, (chat_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def upsert_member(chat_id: int, user_id: int, username: str | None,
                  first_name: str | None, last_name: str | None):
    """
    Guruh a'zosini bazaga qo'shadi yoki yangilaydi.
    Har qanday xabar kelganda chaqiriladi (sessiyadan tashqarida ham).
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO group_members (chat_id, user_id, username, first_name, last_name, last_seen)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(chat_id, user_id) DO UPDATE SET
            username   = excluded.username,
            first_name = excluded.first_name,
            last_name  = excluded.last_name,
            last_seen  = excluded.last_seen
    """, (chat_id, user_id, username, first_name, last_name, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def record_message(session_id: int, chat_id: int, user_id: int,
                   username: str | None, first_name: str | None, last_name: str | None):
    """Sessiya davomida yuborilgan xabarni saqlaydi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO messages (session_id, chat_id, user_id, username, first_name, last_name, sent_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (session_id, chat_id, user_id, username, first_name, last_name, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_session_stats(session_id: int) -> list[dict]:
    """Sessiyada qatnashganlar va ularning xabar sonini qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            user_id,
            username,
            first_name,
            last_name,
            COUNT(*) AS message_count
        FROM messages
        WHERE session_id = ?
        GROUP BY user_id
        ORDER BY message_count DESC
    """, (session_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_session_total_messages(session_id: int) -> int:
    """Sessiyada jami xabarlar sonini qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM messages WHERE session_id = ?", (session_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_absent_members(chat_id: int, session_id: int) -> list[dict]:
    """
    Guruhda avval xabar yozgan, lekin bu sessiyada qatnashmagan
    foydalanuvchilar ro'yxatini qaytaradi.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT gm.user_id, gm.username, gm.first_name, gm.last_name
        FROM group_members gm
        WHERE gm.chat_id = ?
          AND gm.user_id NOT IN (
              SELECT DISTINCT user_id FROM messages WHERE session_id = ?
          )
        ORDER BY gm.first_name, gm.username
    """, (chat_id, session_id))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
