import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/conversations.db")


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role      TEXT NOT NULL,
                content   TEXT NOT NULL,
                ts        TEXT NOT NULL
            )
        """)


def save_message(session_id: str, role: str, content: str) -> None:
    with _conn() as con:
        con.execute(
            "INSERT INTO messages (session_id, role, content, ts) VALUES (?,?,?,?)",
            (session_id, role, content, datetime.now().isoformat(timespec="seconds")),
        )


def get_sessions(limit: int = 200) -> list[dict]:
    with _conn() as con:
        rows = con.execute("""
            SELECT
                session_id,
                MIN(ts)  AS started,
                MAX(ts)  AS last_msg,
                COUNT(*) AS msg_count
            FROM messages
            GROUP BY session_id
            ORDER BY last_msg DESC
            LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_messages(session_id: str) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT role, content, ts FROM messages WHERE session_id=? ORDER BY id",
            (session_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_stats() -> dict:
    with _conn() as con:
        today = datetime.now().date().isoformat()
        total_sessions = con.execute("SELECT COUNT(DISTINCT session_id) FROM messages").fetchone()[0]
        today_sessions = con.execute(
            "SELECT COUNT(DISTINCT session_id) FROM messages WHERE ts LIKE ?",
            (f"{today}%",),
        ).fetchone()[0]
        total_messages = con.execute("SELECT COUNT(*) FROM messages WHERE role='user'").fetchone()[0]
    return {
        "total_sessions": total_sessions,
        "today_sessions": today_sessions,
        "total_messages": total_messages,
    }
