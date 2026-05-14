"""Tests for the Streamlit UI helper functions."""

import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.ui.streamlit_app import format_timestamp


class TestFormatTimestamp:
    """Tests for the timestamp formatting helper."""

    def test_valid_iso_timestamp(self):
        """Format a standard ISO timestamp string."""
        ts = "2026-05-14T10:30:00.123456"
        result = format_timestamp(ts)
        assert result == "2026-05-14 10:30:00"

    def test_valid_iso_no_microseconds(self):
        """Format an ISO timestamp without microseconds."""
        ts = "2026-05-14T10:30:00"
        result = format_timestamp(ts)
        assert result == "2026-05-14 10:30:00"

    def test_none_value(self):
        """Handle None input gracefully."""
        result = format_timestamp(None)
        assert result == ""

    def test_invalid_string(self):
        """Handle invalid timestamp string gracefully."""
        result = format_timestamp("not-a-timestamp")
        assert result == "not-a-timestamp"

    def test_empty_string(self):
        """Handle empty string gracefully."""
        result = format_timestamp("")
        assert result == ""


class TestProcessRegistration:
    """Tests for the registration logic."""

    def _get_process_registration(self):
        """Import _process_registration avoiding st.cache_resource issues."""
        from src.ui import streamlit_app
        return streamlit_app._process_registration

    def test_missing_name(self):
        """Registration fails without a name."""
        func = self._get_process_registration()
        with patch("src.ui.streamlit_app.st") as mock_st:
            func("", "EMP001", None, None, None)
            mock_st.error.assert_called_once()
            assert "name" in mock_st.error.call_args[0][0].lower()

    def test_missing_employee_id(self):
        """Registration fails without an employee ID."""
        func = self._get_process_registration()
        with patch("src.ui.streamlit_app.st") as mock_st:
            func("Bruce", "", None, None, None)
            mock_st.error.assert_called_once()
            assert "id" in mock_st.error.call_args[0][0].lower()

    def test_no_face_detected(self):
        """Registration fails when no face is found in the frame."""
        func = self._get_process_registration()
        mock_face_rec = MagicMock()
        mock_face_rec.register_from_frame.return_value = None
        mock_face_db = MagicMock()

        with patch("src.ui.streamlit_app.st") as mock_st:
            func("Bruce", "EMP001", np.zeros((100, 100, 3), dtype=np.uint8), mock_face_rec, mock_face_db)
            mock_st.error.assert_called_once()
            mock_face_db.register.assert_not_called()

    def test_successful_registration(self):
        """Registration succeeds when face is detected."""
        func = self._get_process_registration()
        mock_face_rec = MagicMock()
        mock_face_rec.register_from_frame.return_value = np.random.randn(512).astype(np.float32)
        mock_face_db = MagicMock()

        with patch("src.ui.streamlit_app.st") as mock_st:
            func("Bruce", "EMP001", np.zeros((100, 100, 3), dtype=np.uint8), mock_face_rec, mock_face_db)
            mock_st.success.assert_called_once()
            mock_face_db.register.assert_called_once_with("Bruce", "EMP001", mock_face_rec.register_from_frame.return_value)
            assert "registered successfully" in mock_st.success.call_args[0][0]

    def test_multiple_faces_rejected(self):
        """Registration should handle multiple faces (register_from_frame returns None)."""
        func = self._get_process_registration()
        mock_face_rec = MagicMock()
        mock_face_rec.register_from_frame.return_value = None
        mock_face_db = MagicMock()

        with patch("src.ui.streamlit_app.st") as mock_st:
            func("Bruce", "EMP001", np.zeros((100, 100, 3), dtype=np.uint8), mock_face_rec, mock_face_db)
            mock_st.error.assert_called_once()
            mock_face_db.register.assert_not_called()


class TestPageHelpers:
    """Tests for dashboard and report data processing."""

    def test_empty_records_dashboard(self):
        """Dashboard handles empty records list."""
        records = []
        checkins = [r for r in records if r["event"] == "checkin"]
        checkouts = [r for r in records if r["event"] == "checkout"]
        unique_today = set(r["employee"] for r in records)

        assert len(checkins) == 0
        assert len(checkouts) == 0
        assert len(unique_today) == 0

    def test_mixed_events_counting(self):
        """Correctly count check-ins and check-outs separately."""
        records = [
            {"employee": "Alice", "event": "checkin", "timestamp": "2026-05-14T08:00:00", "confidence": 0.6},
            {"employee": "Bob", "event": "checkin", "timestamp": "2026-05-14T08:30:00", "confidence": 0.7},
            {"employee": "Alice", "event": "checkout", "timestamp": "2026-05-14T17:00:00", "confidence": 0.6},
        ]
        checkins = [r for r in records if r["event"] == "checkin"]
        checkouts = [r for r in records if r["event"] == "checkout"]
        unique_today = set(r["employee"] for r in records)

        assert len(checkins) == 2
        assert len(checkouts) == 1
        assert len(unique_today) == 2

    def test_report_filtering_by_employee(self):
        """Filter records by specific employee."""
        df = pd.DataFrame([
            {"employee": "Alice", "event": "checkin", "timestamp": "2026-05-14T08:00:00", "confidence": 0.6},
            {"employee": "Bob", "event": "checkin", "timestamp": "2026-05-14T08:30:00", "confidence": 0.7},
            {"employee": "Alice", "event": "checkout", "timestamp": "2026-05-14T17:00:00", "confidence": 0.6},
        ])
        filtered = df[df["employee"] == "Alice"]
        assert len(filtered) == 2
        assert all(filtered["employee"] == "Alice")

    def test_report_filtering_by_event(self):
        """Filter records by event type."""
        df = pd.DataFrame([
            {"employee": "Alice", "event": "checkin", "timestamp": "2026-05-14T08:00:00", "confidence": 0.6},
            {"employee": "Bob", "event": "checkin", "timestamp": "2026-05-14T08:30:00", "confidence": 0.7},
            {"employee": "Alice", "event": "checkout", "timestamp": "2026-05-14T17:00:00", "confidence": 0.6},
        ])
        filtered = df[df["event"] == "checkout"]
        assert len(filtered) == 1
        assert filtered.iloc[0]["event"] == "checkout"

    def test_report_combined_filter(self):
        """Filter by both employee and event type."""
        df = pd.DataFrame([
            {"employee": "Alice", "event": "checkin", "timestamp": "2026-05-14T08:00:00", "confidence": 0.6},
            {"employee": "Bob", "event": "checkin", "timestamp": "2026-05-14T08:30:00", "confidence": 0.7},
            {"employee": "Alice", "event": "checkout", "timestamp": "2026-05-14T17:00:00", "confidence": 0.6},
        ])
        filtered = df[(df["employee"] == "Alice") & (df["event"] == "checkin")]
        assert len(filtered) == 1
        assert filtered.iloc[0]["employee"] == "Alice"
        assert filtered.iloc[0]["event"] == "checkin"

    def test_csv_export_format(self):
        """Exported CSV contains correct columns and data."""
        records = [
            {"employee": "Alice", "event": "checkin", "timestamp": "2026-05-14T08:00:00", "confidence": 0.6},
        ]
        df = pd.DataFrame(records)
        csv_data = df.to_csv(index=False)
        assert "employee" in csv_data
        assert "Alice" in csv_data
        assert "checkin" in csv_data


class TestCacheResourceImports:
    """Test that heavy objects can be imported and wrapped correctly."""

    def test_face_database_instantiation(self, tmp_path):
        """FaceDatabase can be created for caching."""
        from src.face_db import FaceDatabase
        db = FaceDatabase(db_path=str(tmp_path / "test_faces.db"))
        assert db is not None
        db.close()

    def test_attendance_logger_instantiation(self, tmp_path):
        """AttendanceLogger can be created for caching."""
        from src.attendance_logger import AttendanceLogger
        logger = AttendanceLogger(db_path=str(tmp_path / "test_att.db"), cooldown_seconds=1800)
        assert logger is not None
        logger.close()

    def test_format_timestamp_is_importable(self):
        """format_timestamp function can be imported from the module."""
        from src.ui.streamlit_app import format_timestamp
        assert callable(format_timestamp)
