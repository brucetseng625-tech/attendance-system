"""Attendance logging with cooldown and CSV export."""

import csv
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional


class AttendanceLogger:
    """Records attendance events with cooldown logic."""

    def __init__(self, db_path: str = "data/attendance.db", cooldown_seconds: int = 1800):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self.cooldown = cooldown_seconds
        self._init_db()

    def _get_conn(self):
        """Get a new connection for thread safety."""
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_db(self):
        conn = self._get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    confidence REAL DEFAULT 0.0
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_attendance_emp_time "
                "ON attendance(employee, timestamp)"
            )
            conn.commit()
        finally:
            conn.close()

    def log(self, employee: str, event_type: str = "checkin", confidence: float = 0.0) -> dict:
        """Log an attendance event.

        Returns dict with status: 'logged', 'cooldown', or 'error'.
        """
        conn = self._get_conn()
        try:
            now = datetime.now()
            ts_str = now.isoformat()

            if self._in_cooldown(conn, employee, event_type, now):
                return {
                    "status": "cooldown",
                    "employee": employee,
                    "message": "Still in cooldown period",
                }

            conn.execute(
                "INSERT INTO attendance (employee, event_type, timestamp, confidence) VALUES (?, ?, ?, ?)",
                (employee, event_type, ts_str, confidence),
            )
            conn.commit()
            return {
                "status": "logged",
                "employee": employee,
                "event": event_type,
                "timestamp": ts_str,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            conn.close()

    def _in_cooldown(self, conn, employee: str, event_type: str, now: datetime) -> bool:
        """Check if the last event of this type is within cooldown period."""
        row = conn.execute(
            "SELECT timestamp FROM attendance WHERE employee = ? AND event_type = ? ORDER BY timestamp DESC LIMIT 1",
            (employee, event_type),
        ).fetchone()
        if row is None:
            return False

        last_ts = datetime.fromisoformat(row[0])
        elapsed = (now - last_ts).total_seconds()
        return elapsed < self.cooldown

    def get_today_records(self, employee: Optional[str] = None) -> list[dict]:
        """Get today's attendance records."""
        conn = self._get_conn()
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            if employee:
                rows = conn.execute(
                    "SELECT employee, event_type, timestamp, confidence FROM attendance WHERE employee = ? AND timestamp LIKE ?",
                    (employee, f"{today}%"),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT employee, event_type, timestamp, confidence FROM attendance WHERE timestamp LIKE ? ORDER BY timestamp DESC",
                    (f"{today}%",),
                ).fetchall()
            return [
                {"employee": r[0], "event": r[1], "timestamp": r[2], "confidence": r[3]}
                for r in rows
            ]
        finally:
            conn.close()

    def get_all_records(self) -> list[dict]:
        """Get all attendance records."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT employee, event_type, timestamp, confidence FROM attendance ORDER BY timestamp DESC"
            ).fetchall()
            return [
                {"employee": r[0], "event": r[1], "timestamp": r[2], "confidence": r[3]}
                for r in rows
            ]
        finally:
            conn.close()

    def get_employee_records(self, employee: str) -> list[dict]:
        """Get all attendance records for a specific employee."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT employee, event_type, timestamp, confidence FROM attendance WHERE employee = ? ORDER BY timestamp DESC",
                (employee,),
            ).fetchall()
            return [
                {"employee": r[0], "event": r[1], "timestamp": r[2], "confidence": r[3]}
                for r in rows
            ]
        finally:
            conn.close()

    def get_last_event_type(self, employee: str) -> str | None:
        """Get the last event type (checkin/checkout) for an employee today."""
        from datetime import timedelta

        conn = self._get_conn()
        try:
            today_str = datetime.now().strftime("%Y-%m-%d")
            tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            cursor = conn.execute(
                """SELECT event_type FROM attendance
                   WHERE employee = ? AND timestamp >= ? AND timestamp < ?
                   ORDER BY timestamp DESC LIMIT 1""",
                (employee, today_str, tomorrow_str),
            )
            row = cursor.fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def export_csv(self, output_path: str):
        """Export all records to CSV."""
        records = self.get_all_records()
        if not records:
            return
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["employee", "event", "timestamp", "confidence"])
            writer.writeheader()
            writer.writerows(records)

    def close(self):
        """Close database connection."""
        self.conn.close()
