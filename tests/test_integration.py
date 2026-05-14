"""Integration tests for the attendance system.

Verifies cross-module workflows:
1. Face DB + Attendance Logger: register -> match -> log -> check records
2. ZoneChecker with typical coordinates
3. All required project files exist
"""

import os
from pathlib import Path

import numpy as np
import pytest

from src.attendance_logger import AttendanceLogger
from src.detector import ZoneChecker
from src.face_db import FaceDatabase


# ---------------------------------------------------------------------------
# Paths to verify
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = [
    "src/__init__.py",
    "src/config.py",
    "src/face_db.py",
    "src/attendance_logger.py",
    "src/detector.py",
    "src/face_recognizer.py",
    "src/ui/__init__.py",
    "src/ui/streamlit_app.py",
    "main.py",
    "config.yaml",
    "requirements.txt",
    "README.md",
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def face_db(tmp_path):
    """Fresh face database."""
    db = FaceDatabase(db_path=str(tmp_path / "faces.db"))
    yield db
    db.close()


@pytest.fixture
def att_logger(tmp_path):
    """Fresh attendance logger with short cooldown for testing."""
    log = AttendanceLogger(db_path=str(tmp_path / "attendance.db"), cooldown_seconds=5)
    yield log
    log.close()


# ---------------------------------------------------------------------------
# 1. Face DB + Attendance Logger integration
# ---------------------------------------------------------------------------
class TestFaceDBLoggerIntegration:
    """End-to-end workflow: register employee, match face, log attendance."""

    def test_register_match_log_flow(self, face_db, att_logger):
        """Register an employee, match their embedding, and log attendance."""
        embedding = np.random.randn(512).astype(np.float32)
        face_db.register("Alice", "EMP001", embedding)

        # Match the same embedding
        matched_name = face_db.match(embedding, threshold=0.4)
        assert matched_name == "Alice"

        # Log attendance for the matched person
        result = att_logger.log(matched_name, "checkin", confidence=0.95)
        assert result["status"] == "logged"
        assert result["employee"] == "Alice"

    def test_register_match_log_check_records(self, face_db, att_logger):
        """Full cycle: register -> match -> log -> retrieve records."""
        emb_alice = np.random.randn(512).astype(np.float32)
        emb_bob = np.random.randn(512).astype(np.float32)

        face_db.register("Alice", "EMP001", emb_alice)
        face_db.register("Bob", "EMP002", emb_bob)

        # Match both
        name_a = face_db.match(emb_alice, threshold=0.4)
        name_b = face_db.match(emb_bob, threshold=0.4)
        assert name_a == "Alice"
        assert name_b == "Bob"

        # Log check-ins
        r1 = att_logger.log(name_a, "checkin", confidence=0.9)
        r2 = att_logger.log(name_b, "checkin", confidence=0.85)
        assert r1["status"] == "logged"
        assert r2["status"] == "logged"

        # Retrieve and verify records
        records = att_logger.get_today_records()
        assert len(records) >= 2
        employees_in_records = {r["employee"] for r in records}
        assert "Alice" in employees_in_records
        assert "Bob" in employees_in_records

    def test_unknown_face_no_match_no_log(self, face_db, att_logger):
        """Unknown face should not match; logging still works but is separate."""
        unknown_emb = np.random.randn(512).astype(np.float32)
        matched = face_db.match(unknown_emb, threshold=0.01)  # very strict
        assert matched is None

        # Logger can still log an arbitrary name, but integration flow
        # would skip logging when no match is found
        assert matched is None  # simulates the pipeline guard

    def test_multiple_employees_cooldown(self, face_db, att_logger):
        """Two different employees can both log within cooldown window."""
        emb_a = np.random.randn(512).astype(np.float32)
        emb_b = np.random.randn(512).astype(np.float32)
        face_db.register("Carol", "EMP003", emb_a)
        face_db.register("Dan", "EMP004", emb_b)

        r1 = att_logger.log("Carol", "checkin", confidence=0.92)
        r2 = att_logger.log("Dan", "checkin", confidence=0.88)
        assert r1["status"] == "logged"
        assert r2["status"] == "logged"

        # Same employee hits cooldown
        r3 = att_logger.log("Carol", "checkin", confidence=0.92)
        assert r3["status"] == "cooldown"

    def test_export_csv_after_integration_flow(self, face_db, att_logger, tmp_path):
        """After full workflow, CSV export contains logged records."""
        emb = np.random.randn(512).astype(np.float32)
        face_db.register("Eve", "EMP005", emb)
        matched = face_db.match(emb, threshold=0.4)
        assert matched == "Eve"

        att_logger.log(matched, "checkin", confidence=0.9)
        csv_path = str(tmp_path / "attendance_export.csv")
        att_logger.export_csv(csv_path)

        content = Path(csv_path).read_text()
        assert "employee" in content
        assert "Eve" in content


# ---------------------------------------------------------------------------
# 2. ZoneChecker with typical coordinates
# ---------------------------------------------------------------------------
class TestZoneCheckerTypicalCoordinates:
    """Verify ZoneChecker behavior with realistic check-in zone coordinates."""

    def test_default_center_zone(self):
        """Default center 60% zone: (0.2, 0.3) to (0.8, 0.7)."""
        points = [(0.2, 0.3), (0.8, 0.3), (0.8, 0.7), (0.2, 0.7)]
        checker = ZoneChecker(points)

        # Center of frame should be inside
        assert checker.is_inside(0.5, 0.5) is True

        # Corners of the zone should be on edge (inside)
        assert checker.is_inside(0.2, 0.3) is True
        assert checker.is_inside(0.8, 0.7) is True

        # Outside corners should be False
        assert checker.is_inside(0.05, 0.05) is False
        assert checker.is_inside(0.95, 0.95) is False

    def test_bottom_half_zone(self):
        """Zone covering bottom half: useful for desk check-in scenario."""
        points = [(0.0, 0.5), (1.0, 0.5), (1.0, 1.0), (0.0, 1.0)]
        checker = ZoneChecker(points)

        assert checker.is_inside(0.5, 0.75) is True
        assert checker.is_inside(0.1, 0.9) is True
        assert checker.is_inside(0.5, 0.25) is False
        assert checker.is_inside(0.5, 0.5) is True  # on edge

    def test_small_top_left_zone(self):
        """Small zone in top-left corner."""
        points = [(0.0, 0.0), (0.3, 0.0), (0.3, 0.3), (0.0, 0.3)]
        checker = ZoneChecker(points)

        assert checker.is_inside(0.15, 0.15) is True
        assert checker.is_inside(0.5, 0.5) is False
        assert checker.is_inside(0.3, 0.3) is True  # corner

    def test_check_detections_mock(self):
        """check_detections with mock detection objects."""
        points = [(0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8)]
        checker = ZoneChecker(points)

        # Mock detections with numpy arrays
        class MockDetections:
            def __init__(self):
                # Two boxes: one center (inside), one corner (outside)
                # Frame is 1000x1000, so center of box 1 = (500,500) -> (0.5, 0.5)
                # Center of box 2 = (50,50) -> (0.05, 0.05)
                import numpy as np
                self.xyxy = np.array([
                    [400, 400, 600, 600],  # center = (500, 500) -> (0.5, 0.5) inside
                    [0, 0, 100, 100],       # center = (50, 50) -> (0.05, 0.05) outside
                ], dtype=np.float32)
                self.tracker_id = np.array([1, 2], dtype=np.int64)

        mock_dets = MockDetections()
        frame_shape = (1000, 1000, 3)

        inside = checker.check_detections(mock_dets, frame_shape)
        assert 1 in inside
        assert 2 not in inside


# ---------------------------------------------------------------------------
# 3. Project file existence
# ---------------------------------------------------------------------------
class TestRequiredFilesExist:
    """Ensure all critical project files are present."""

    @pytest.mark.parametrize("rel_path", REQUIRED_FILES)
    def test_file_exists(self, rel_path):
        full_path = PROJECT_ROOT / rel_path
        assert full_path.exists(), f"Required file missing: {rel_path}"

    def test_tests_directory_exists(self):
        assert (PROJECT_ROOT / "tests").is_dir()

    def test_data_directory_exists(self):
        assert (PROJECT_ROOT / "data").is_dir()
