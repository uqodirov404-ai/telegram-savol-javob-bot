import psycopg2
import psycopg2.extras
from datetime import datetime
from config import DATABASE_URL


def get_connection():
    """PostgreSQL ulanishini qaytaradi."""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL topilmadi! Baza manzili noto'g'ri.")
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def init_db():
    """Bazani ishga tushiradi va jadvallarni yaratadi."""
    conn = get_connection()
    cursor = conn.cursor()

    # Tasdiqlangan guruhlar jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS approved_groups (
            chat_id BIGINT PRIMARY KEY,
            group_name TEXT,
            status TEXT DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
            requested_at TEXT NOT NULL
        )
    """)

    # Sessiyalar jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id SERIAL PRIMARY KEY,
            chat_id BIGINT NOT NULL,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)

    # Xabarlar jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            session_id INTEGER NOT NULL REFERENCES sessions(id),
            chat_id BIGINT NOT NULL,
            user_id BIGINT NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            sent_at TEXT NOT NULL
        )
    """)

    # Guruh a'zolari jadvali — xabar yozgan barcha foydalanuvchilar
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS group_members (
            id SERIAL PRIMARY KEY,
            chat_id BIGINT NOT NULL,
            user_id BIGINT NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            last_seen TEXT NOT NULL,
            UNIQUE(chat_id, user_id)
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()


def get_group_status(chat_id: int) -> str | None:
    """Guruhning holatini qaytaradi ('pending', 'approved', 'rejected' yoki None)."""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT status FROM approved_groups WHERE chat_id = %s", (chat_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row["status"] if row else None


def request_group_approval(chat_id: int, group_name: str):
    """Yangi guruh ruxsat so'rab bazaga yoziladi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO approved_groups (chat_id, group_name, status, requested_at)
        VALUES (%s, %s, 'pending', %s)
        ON CONFLICT(chat_id) DO NOTHING
    """, (chat_id, group_name, datetime.now().isoformat()))
    conn.commit()
    cursor.close()
    conn.close()


def set_group_status(chat_id: int, status: str):
    """Guruhning ruxsat holatini yangilaydi ('approved' yoki 'rejected')."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE approved_groups SET status = %s WHERE chat_id = %s
    """, (status, chat_id))
    conn.commit()
    cursor.close()
    conn.close()


def start_session(chat_id: int) -> int:
    """Yangi sessiyani boshlaydi. Sessiya ID sini qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE sessions SET is_active = 0, ended_at = %s
        WHERE chat_id = %s AND is_active = 1
    """, (datetime.now().isoformat(), chat_id))

    cursor.execute("""
        INSERT INTO sessions (chat_id, started_at, is_active)
        VALUES (%s, %s, 1)
        RETURNING id
    """, (chat_id, datetime.now().isoformat()))

    session_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    return session_id


def end_session(chat_id: int) -> dict | None:
    """Aktiv sessiyani to'xtatadi. Sessiya ma'lumotlarini qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cursor.execute("""
        SELECT * FROM sessions WHERE chat_id = %s AND is_active = 1
    """, (chat_id,))
    session = cursor.fetchone()

    if not session:
        cursor.close()
        conn.close()
        return None

    ended_at = datetime.now().isoformat()
    cursor.execute("""
        UPDATE sessions SET is_active = 0, ended_at = %s
        WHERE id = %s
    """, (ended_at, session["id"]))

    conn.commit()
    result = dict(session)
    result["ended_at"] = ended_at
    cursor.close()
    conn.close()
    return result


def get_active_session(chat_id: int) -> dict | None:
    """Guruhning aktiv sessiyasini qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("""
        SELECT * FROM sessions WHERE chat_id = %s AND is_active = 1
    """, (chat_id,))
    row = cursor.fetchone()
    cursor.close()
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
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT(chat_id, user_id) DO UPDATE SET
            username   = excluded.username,
            first_name = excluded.first_name,
            last_name  = excluded.last_name,
            last_seen  = excluded.last_seen
    """, (chat_id, user_id, username, first_name, last_name, datetime.now().isoformat()))
    conn.commit()
    cursor.close()
    conn.close()


def record_message(session_id: int, chat_id: int, user_id: int,
                   username: str | None, first_name: str | None, last_name: str | None):
    """Sessiya davomida yuborilgan xabarni saqlaydi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO messages (session_id, chat_id, user_id, username, first_name, last_name, sent_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (session_id, chat_id, user_id, username, first_name, last_name, datetime.now().isoformat()))
    conn.commit()
    cursor.close()
    conn.close()


def get_session_stats(session_id: int) -> list[dict]:
    """Sessiyada qatnashganlar va ularning xabar sonini qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("""
        SELECT
            user_id,
            username,
            first_name,
            last_name,
            COUNT(*) AS message_count
        FROM messages
        WHERE session_id = %s
        GROUP BY user_id, username, first_name, last_name
        ORDER BY message_count DESC
    """, (session_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(row) for row in rows]


def get_session_total_messages(session_id: int) -> int:
    """Sessiyada jami xabarlar sonini qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM messages WHERE session_id = %s", (session_id,))
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return count


def get_absent_members(chat_id: int, session_id: int) -> list[dict]:
    """
    Guruhda avval xabar yozgan, lekin bu sessiyada qatnashmagan
    foydalanuvchilar ro'yxatini qaytaradi.
    """
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("""
        SELECT gm.user_id, gm.username, gm.first_name, gm.last_name
        FROM group_members gm
        WHERE gm.chat_id = %s
          AND gm.user_id NOT IN (
              SELECT DISTINCT user_id FROM messages WHERE session_id = %s
          )
        ORDER BY gm.first_name, gm.username
    """, (chat_id, session_id))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(row) for row in rows]
