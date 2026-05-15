"""User Password Manager for Attendance System."""

import sqlite3
import hashlib
from pathlib import Path

ROOT = Path(__file__).parent.parent / "data"
DB_PATH = ROOT / "users.db"

class UserManager:
    ADMIN_USERNAME = "__admin__"

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

    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()

    def check_password(self, username: str, password: str) -> bool:
        """Verify if password matches stored hash."""
        stored_hash = self._get_stored_hash(username)
        
        # If no password set in DB, use defaults
        if stored_hash is None:
            if username == self.ADMIN_USERNAME:
                return password == "admin"  # Default admin password
            return password == "1234"  # Default employee password
        
        return stored_hash == self._hash_password(password)

    def check_admin_password(self, password: str) -> bool:
        """Verify admin password."""
        return self.check_password(self.ADMIN_USERNAME, password)

    def set_admin_password(self, new_password: str) -> bool:
        """Update admin password (hashed)."""
        return self.set_password(self.ADMIN_USERNAME, new_password)

    def _get_stored_hash(self, username: str) -> str | None:
        conn = sqlite3.connect(str(DB_PATH))
        try:
            cursor = conn.execute(
                "SELECT password FROM user_passwords WHERE username = ?",
                (username,)
            )
            row = cursor.fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def set_password(self, username: str, new_password: str) -> bool:
        """Update or insert user password (hashed)."""
        hashed_pw = self._hash_password(new_password)
        conn = sqlite3.connect(str(DB_PATH))
        try:
            conn.execute(
                """INSERT OR REPLACE INTO user_passwords (username, password) 
                   VALUES (?, ?)""",
                (username, hashed_pw)
            )
            conn.commit()
            return True
        finally:
            conn.close()
