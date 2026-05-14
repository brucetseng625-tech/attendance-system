"""Tests for the configuration loader."""

import pytest
from src.config import load_config, get_project_root


def test_load_config_returns_dict():
    """load_config returns a dictionary."""
    config = load_config()
    assert isinstance(config, dict)


def test_load_config_has_all_sections():
    """Config contains all expected top-level sections."""
    config = load_config()
    for key in ["camera", "detection", "tracking", "face_recognition", "attendance", "zones"]:
        assert key in config, f"Missing section: {key}"


def test_load_config_camera_fields():
    """Camera section has source and fps."""
    config = load_config()
    assert "source" in config["camera"]
    assert "fps" in config["camera"]


def test_load_config_detection_fields():
    """Detection section has model, confidence, iou."""
    config = load_config()
    assert "model" in config["detection"]
    assert "confidence" in config["detection"]


def test_load_config_attendance_fields():
    """Attendance section has database path and cooldown."""
    config = load_config()
    assert "database" in config["attendance"]
    assert "cooldown_seconds" in config["attendance"]


def test_get_project_root():
    """get_project_root returns a Path with the project name."""
    root = get_project_root()
    assert root.name == "attendance-system"
