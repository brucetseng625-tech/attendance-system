"""Exception Manager for Guard Mode (Leave/Business requests)."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger


class ExceptionManager:
    """Manages approved exceptions (leave, business trips) for access control."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Create the exceptions table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS exceptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id TEXT NOT NULL,
                    type TEXT NOT NULL CHECK(type IN ('leave', 'business')),
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    reason TEXT,
                    status TEXT DEFAULT 'approved' CHECK(status IN ('pending', 'approved', 'rejected')),
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Index for faster lookups
            conn.execute("CREATE INDEX IF NOT EXISTS idx_employee_time ON exceptions(employee_id, start_time, end_time)")
            conn.commit()
        finally:
            conn.close()

    def add_exception(
        self,
        employee_id: str,
        exception_type: str,
        start_time: str,
        end_time: str,
        reason: Optional[str] = None,
        status: str = "approved",
    ) -> int:
        """Add a new exception record. Returns the new ID."""
        conn = sqlite3.connect(self.db_path)
        # Use local time for created_at
        local_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            cursor = conn.execute(
                """INSERT INTO exceptions (employee_id, type, start_time, end_time, reason, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (employee_id, exception_type, start_time, end_time, reason, status, local_now),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_active_exceptions(self, employee_id: str, current_time: Optional[datetime] = None) -> list[dict]:
        """Get currently valid exceptions for an employee."""
        if current_time is None:
            current_time = datetime.now()
        now_str = current_time.strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                """SELECT * FROM exceptions 
                   WHERE employee_id = ? 
                   AND status = 'approved'
                   AND start_time <= ? 
                   AND end_time >= ?
                   ORDER BY start_time DESC""",
                (employee_id, now_str, now_str),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def is_exempted(self, employee_id: str, current_time: Optional[datetime] = None) -> bool:
        """Check if employee is currently exempted from standard rules."""
        exceptions = self.get_active_exceptions(employee_id, current_time)
        return len(exceptions) > 0

    def get_all_exceptions(self, limit: int = 100) -> list[dict]:
        """Get all exception records."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                "SELECT * FROM exceptions ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_pending_exceptions(self) -> list[dict]:
        """Get all pending exception records."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                "SELECT * FROM exceptions WHERE status = 'pending' ORDER BY created_at ASC"
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_exceptions_by_employee(self, employee_id: str) -> list[dict]:
        """Get all exceptions for a specific employee."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                "SELECT * FROM exceptions WHERE employee_id = ? ORDER BY created_at DESC",
                (employee_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def update_status(self, exception_id: int, status: str) -> bool:
        """Update the status of an exception (approve/reject)."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "UPDATE exceptions SET status = ? WHERE id = ?",
                (status, exception_id)
            )
            conn.commit()
            return True
        finally:
            conn.close()
