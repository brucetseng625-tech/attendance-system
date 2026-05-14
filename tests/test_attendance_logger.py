"""Tests for the attendance logger."""

import os
import time
from pathlib import Path

import pytest
from src.attendance_logger import AttendanceLogger


@pytest.fixture
def logger(tmp_path):
    db_path = str(tmp_path / "attendance.db")
    return AttendanceLogger(db_path=db_path, cooldown_seconds=5)


def test_log_checkin(logger):
    """Log a check-in event."""
    result = logger.log("Bruce", "checkin")
    assert result["status"] == "logged"
    assert result["employee"] == "Bruce"


def test_cooldown_prevents_duplicate(logger):
    """Same employee same event within cooldown returns cooldown status."""
    logger.log("Bruce", "checkin")
    result = logger.log("Bruce", "checkin")
    assert result["status"] == "cooldown"


def test_different_event_not_blocked(logger):
    """Different event type (checkout) should not be blocked by check-in cooldown."""
    logger.log("Bruce", "checkin")
    result = logger.log("Bruce", "checkout")
    assert result["status"] == "logged"


def test_different_employee_not_blocked(logger):
    """Different employee should not be blocked."""
    logger.log("Bruce", "checkin")
    result = logger.log("Alice", "checkin")
    assert result["status"] == "logged"


def test_cooldown_expires(logger):
    """After cooldown period, logging should succeed."""
    logger.log("Bruce", "checkin")
    time.sleep(5.1)  # Wait for cooldown to expire
    result = logger.log("Bruce", "checkin")
    assert result["status"] == "logged"


def test_get_today_records(logger):
    """Get today's attendance records."""
    logger.log("Alice", "checkin")
    logger.log("Bob", "checkin")
    records = logger.get_today_records()
    assert len(records) >= 2
    names = [r["employee"] for r in records]
    assert "Alice" in names
    assert "Bob" in names


def test_export_csv(logger, tmp_path):
    """Export records to CSV file."""
    logger.log("Alice", "checkin")
    logger.log("Bob", "checkout")
    csv_path = str(tmp_path / "export.csv")
    logger.export_csv(csv_path)
    assert Path(csv_path).exists()
    content = Path(csv_path).read_text()
    assert "employee" in content
    assert "Alice" in content


def test_get_all_records(logger):
    """Get all attendance records ordered by timestamp."""
    logger.log("Alice", "checkin")
    logger.log("Bob", "checkin")
    records = logger.get_all_records()
    assert len(records) >= 2
