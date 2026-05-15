"""End-to-end tests for v2.2.0 new features."""

import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from src.attendance_logger import AttendanceLogger
from src.user_manager import UserManager


class TestAttendanceLoggerNewMethods:
    """Test get_employee_records and get_last_event_type."""

    @pytest.fixture
    def logger(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        log = AttendanceLogger(db_path=db_path, cooldown_seconds=0)
        yield log
        os.unlink(db_path)

    def test_get_last_event_type_no_records(self, logger):
        assert logger.get_last_event_type("Alice") is None

    def test_get_last_event_type_returns_checkin(self, logger):
        logger.log("Alice", "checkin")
        assert logger.get_last_event_type("Alice") == "checkin"

    def test_get_last_event_type_returns_checkout(self, logger):
        logger.log("Alice", "checkin")
        logger.log("Alice", "checkout")
        assert logger.get_last_event_type("Alice") == "checkout"

    def test_get_last_event_type_ignores_yesterday(self, logger):
        # Directly insert a yesterday record
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        conn = logger._get_conn()
        conn.execute(
            "INSERT INTO attendance (employee, event_type, timestamp, confidence) VALUES (?, ?, ?, ?)",
            ("Bob", "checkin", yesterday, 0.95),
        )
        conn.commit()
        conn.close()

        # Today should return None
        assert logger.get_last_event_type("Bob") is None

    def test_get_last_event_type_tomorrow_boundary(self, logger):
        # Insert a record at 23:59:59 today
        now = datetime.now()
        today_2359 = now.replace(hour=23, minute=59, second=59).strftime("%Y-%m-%d %H:%M:%S")
        conn = logger._get_conn()
        conn.execute(
            "INSERT INTO attendance (employee, event_type, timestamp, confidence) VALUES (?, ?, ?, ?)",
            ("Charlie", "checkout", today_2359, 0.9),
        )
        conn.commit()
        conn.close()

        assert logger.get_last_event_type("Charlie") == "checkout"

    def test_get_employee_records_returns_all(self, logger):
        logger.log("Dave", "checkin")
        logger.log("Dave", "checkout")
        records = logger.get_employee_records("Dave")
        assert len(records) == 2
        assert records[0]["event"] == "checkout"  # DESC order
        assert records[1]["event"] == "checkin"

    def test_get_employee_records_empty(self, logger):
        assert logger.get_employee_records("Nobody") == []

    def test_cooldown_blocks_rapid_toggle(self, logger):
        """Cooldown applies to ALL events for an employee, preventing rapid toggles."""
        # Create a logger with a longer cooldown for testing
        logger2 = AttendanceLogger(db_path=logger.db_path, cooldown_seconds=60)
        logger2.log("Eve", "checkin")
        
        # checkout should be blocked because checkin was just logged (within 60s)
        result = logger2.log("Eve", "checkout")
        assert result["status"] == "cooldown"


class TestUserManagerAdminPassword:
    """Test admin password management."""

    @pytest.fixture
    def um(self):
        """Create UserManager with isolated DB."""
        import importlib
        import src.user_manager as um_mod
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        # Patch the module-level DB_PATH
        old_path = um_mod.DB_PATH
        um_mod.DB_PATH = db_path

        # Re-initialize
        instance = UserManager()
        yield instance

        # Restore
        um_mod.DB_PATH = old_path
        os.unlink(db_path)
        # Clear module cache for next test
        importlib.reload(um_mod)

    def test_default_admin_password(self, um):
        assert um.check_admin_password("admin") is True
        assert um.check_admin_password("wrong") is False

    def test_set_and_verify_admin_password(self, um):
        um.set_admin_password("my_new_secret_pw")
        assert um.check_admin_password("my_new_secret_pw") is True
        assert um.check_admin_password("admin") is False

    def test_employee_default_unchanged(self, um):
        assert um.check_password("some_employee", "1234") is True
        assert um.check_password("some_employee", "admin") is False

    def test_passwords_are_hashed(self, um):
        um.set_admin_password("hashed_test_pw")
        stored_hash = um._get_stored_hash("__admin__")
        assert stored_hash is not None
        assert stored_hash != "hashed_test_pw"
        assert len(stored_hash) == 64


class TestAutoToggleLogic:
    """Test the checkin/checkout toggle logic (simulated from main.py)."""

    @pytest.fixture
    def logger(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        log = AttendanceLogger(db_path=db_path, cooldown_seconds=0)
        yield log
        os.unlink(db_path)

    def test_first_detection_is_checkin(self, logger):
        """No prior record -> should checkin."""
        last = logger.get_last_event_type("Alice")
        assert last is None
        event_type = "checkout" if last == "checkin" else "checkin"
        assert event_type == "checkin"
        logger.log("Alice", event_type)

    def test_second_detection_is_checkout(self, logger):
        """Already checked in -> should checkout."""
        logger.log("Alice", "checkin")
        last = logger.get_last_event_type("Alice")
        assert last == "checkin"
        event_type = "checkout" if last == "checkin" else "checkin"
        assert event_type == "checkout"

    def test_third_detection_is_checkin(self, logger):
        """Already checked out -> should checkin again (return to office)."""
        logger.log("Alice", "checkin")
        logger.log("Alice", "checkout")
        last = logger.get_last_event_type("Alice")
        assert last == "checkout"
        event_type = "checkout" if last == "checkin" else "checkin"
        assert event_type == "checkin"

    def test_toggle_preserves_across_days(self, logger):
        """New day should start fresh with checkin (yesterday's records ignored)."""
        # Simulate yesterday's checkout by inserting a past timestamp
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        conn = logger._get_conn()
        conn.execute(
            "INSERT INTO attendance (employee, event_type, timestamp, confidence) VALUES (?, ?, ?, ?)",
            ("Bob", "checkout", yesterday, 0.95),
        )
        conn.commit()
        conn.close()

        # get_last_event_type should return None for today
        last = logger.get_last_event_type("Bob")
        assert last is None

        # So the next event should be checkin
        event_type = "checkout" if last == "checkin" else "checkin"
        assert event_type == "checkin"


class TestExceptionManagerLocalTime:
    """Test that exception_manager uses local time."""

    @pytest.fixture
    def exc_mgr(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        from src.exception_manager import ExceptionManager
        mgr = ExceptionManager(db_path=db_path)
        yield mgr
        os.unlink(db_path)

    def test_created_at_is_local_time(self, exc_mgr):
        before = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        exc_mgr.add_exception("TestUser", "leave", "2026-05-15 09:00:00", "2026-05-15 18:00:00", "Testing", status="pending")
        after = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        pending = exc_mgr.get_pending_exceptions()
        assert len(pending) == 1
        created_at = pending[0]["created_at"]
        # Should be between before and after
        assert before <= created_at <= after
        # Should NOT contain 'Z' or timezone offset
        assert "Z" not in created_at
        assert "+" not in created_at.split(":")[-1]  # No timezone suffix on seconds


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
