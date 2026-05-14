"""Tests for the InsightFace face recognition engine."""

import numpy as np
import pytest
from src.face_recognizer import FaceRecognizer


@pytest.fixture
def recognizer():
    """Create a FaceRecognizer, skipping if model unavailable."""
    try:
        rec = FaceRecognizer(model_name="buffalo_l")
        return rec
    except Exception as e:
        pytest.skip(f"InsightFace model not available: {e}")


def test_face_recognizer_init():
    """Test recognizer can initialize (skips if model unavailable)."""
    try:
        rec = FaceRecognizer(model_name="buffalo_l")
        assert rec.detector is not None
        assert rec.recognition_model is not None
    except Exception as e:
        pytest.skip(f"InsightFace model not available: {e}")


def test_detect_faces_no_faces(recognizer):
    """Detecting faces in a blank image returns empty list."""
    blank = np.zeros((100, 100, 3), dtype=np.uint8)
    faces = recognizer.detect_faces(blank)
    assert isinstance(faces, list)
    assert len(faces) == 0


def test_detect_faces_returns_correct_structure(recognizer):
    """Verify detected face dicts contain expected keys."""
    # Create a simple image that might or might not have faces
    img = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
    faces = recognizer.detect_faces(img)
    # We don't assert len > 0 since random noise won't produce faces
    # But if any are found, verify structure
    for face in faces:
        assert "bbox" in face
        assert "landmark" in face
        assert "embedding" in face
        assert isinstance(face["embedding"], np.ndarray)


def test_register_from_frame_no_face(recognizer):
    """Registration from blank frame returns None."""
    blank = np.zeros((100, 100, 3), dtype=np.uint8)
    result = recognizer.register_from_frame(blank, "Nobody")
    assert result is None


def test_extract_face_region_valid(recognizer):
    """Extract a valid face region from a frame."""
    frame = np.random.randint(0, 255, (400, 400, 3), dtype=np.uint8)
    bbox = np.array([100, 100, 200, 200])
    region = recognizer.extract_face_region(frame, bbox, margin=10)
    assert region is not None
    # Region should be bbox + margin on each side
    assert region.shape[0] == 120  # (200 - 100) + 2*10
    assert region.shape[1] == 120


def test_extract_face_region_clamped(recognizer):
    """Extract region when bbox extends beyond frame boundaries."""
    frame = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    bbox = np.array([80, 80, 120, 120])  # extends beyond frame
    region = recognizer.extract_face_region(frame, bbox, margin=10)
    assert region is not None
    assert region.shape[0] <= 30  # clamped to frame
    assert region.shape[1] <= 30


def test_extract_face_region_invalid(recognizer):
    """Extract region with invalid bbox returns None."""
    frame = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    bbox = np.array([200, 200, 210, 210])  # completely outside frame
    region = recognizer.extract_face_region(frame, bbox, margin=0)
    assert region is None
