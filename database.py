import sqlite3
import logging
from datetime import datetime
from config import DATABASE_PATH

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.db_path = DATABASE_PATH

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    language TEXT DEFAULT 'hinglish',
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_searches INTEGER DEFAULT 0,
                    is_banned INTEGER DEFAULT 0,
                    ban_reason TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS searches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    query TEXT,
                    source TEXT,
                    results_count INTEGER,
                    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS broadcasts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message TEXT,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sent_to INTEGER DEFAULT 0
                )
            """)
            conn.commit()
        logger.info("Database initialized")

    def add_or_update_user(self, user_id: int, username: str, first_name: str):
        with sqlite3.connect(self.db_path) as conn:
            existing = conn.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if existing:
                conn.execute(
                    "UPDATE users SET username=?, first_name=?, last_seen=? WHERE user_id=?",
                    (username, first_name, datetime.now(), user_id)
                )
            else:
                conn.execute(
                    "INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                    (user_id, username, first_name)
                )
            conn.commit()

    def is_banned(self, user_id: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,)).fetchone()
            return bool(row and row[0])

    def ban_user(self, user_id: int, reason: str = ""):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE users SET is_banned=1, ban_reason=? WHERE user_id=?",
                (reason, user_id)
            )
            conn.commit()

    def unban_user(self, user_id: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE users SET is_banned=0, ban_reason='' WHERE user_id=?", (user_id,))
            conn.commit()

    def log_search(self, user_id: int, query: str, source: str, count: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO searches (user_id, query, source, results_count) VALUES (?, ?, ?, ?)",
                (user_id, query, source, count)
            )
            conn.execute(
                "UPDATE users SET total_searches = total_searches + 1 WHERE user_id = ?",
                (user_id,)
            )
            conn.commit()

    def get_all_users(self) -> list:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            return [dict(r) for r in conn.execute("SELECT * FROM users WHERE is_banned = 0").fetchall()]

    def get_stats(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            active = conn.execute("SELECT COUNT(*) FROM users WHERE is_banned = 0").fetchone()[0]
            banned = conn.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1").fetchone()[0]
            searches = conn.execute("SELECT COUNT(*) FROM searches").fetchone()[0]
            today = conn.execute(
                "SELECT COUNT(*) FROM users WHERE date(joined_at) = date('now')"
            ).fetchone()[0]
            top_queries = conn.execute(
                "SELECT query, COUNT(*) as cnt FROM searches GROUP BY query ORDER BY cnt DESC LIMIT 5"
            ).fetchall()
            return {
                'total_users': total,
                'active_users': active,
                'banned_users': banned,
                'total_searches': searches,
                'new_today': today,
                'top_queries': top_queries
            }

    def get_user_list(self, limit: int = 20, offset: int = 0) -> list:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            return [dict(r) for r in conn.execute(
                "SELECT user_id, username, first_name, total_searches, joined_at, is_banned FROM users LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()]

    def set_language(self, user_id: int, lang: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE users SET language=? WHERE user_id=?", (lang, user_id))
            conn.commit()

    def get_language(self, user_id: int) -> str:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT language FROM users WHERE user_id=?", (user_id,)).fetchone()
            return row[0] if row else 'hinglish'
