"""User Password Manager for Attendance System."""

import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent.parent / "data"
DB_PATH = ROOT / "users.db"

class UserManager:
    def __init__(self):
        ROOT.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(str(DB_PATH))
        try:
            # Table to store user passwords
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_passwords (
                    username TEXT PRIMARY KEY,
                    password TEXT NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def get_password(self, username: str) -> str:
        """Get password for a user. Default is '1234' if not found."""
        conn = sqlite3.connect(str(DB_PATH))
        try:
            cursor = conn.execute(
                "SELECT password FROM user_passwords WHERE username = ?",
                (username,)
            )
            row = cursor.fetchone()
            return row[0] if row else "1234"
        finally:
            conn.close()

    def set_password(self, username: str, new_password: str) -> bool:
        """Update or insert user password."""
        conn = sqlite3.connect(str(DB_PATH))
        try:
            conn.execute(
                """INSERT OR REPLACE INTO user_passwords (username, password) 
                   VALUES (?, ?)""",
                (username, new_password)
            )
            conn.commit()
            return True
        finally:
            conn.close()
