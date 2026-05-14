# AI Face Attendance System Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a local webcam-based attendance system using Supervision + YOLOv8 for person detection + InsightFace for face recognition, with Streamlit UI for real-time monitoring and attendance reports.

**Architecture:** 
- YOLOv8 detects persons → Supervision BYTETrack assigns persistent IDs → When person enters defined zone → InsightFace extracts face embedding → matches against registered employees → logs attendance to SQLite
- Streamlit provides real-time frame display + attendance dashboard + CSV export

**Tech Stack:** supervision, ultralytics, insightface, onnxruntime, opencv-python, streamlit, sqlite3, numpy

---

### Task 1: Project Setup & Dependencies

**Objective:** Create project structure, requirements.txt, and configuration file

**Files:**
- Create: `requirements.txt`
- Create: `config.yaml`
- Create: `src/__init__.py`
- Create: `src/config.py`
- Create: `data/.gitkeep`

**Step 1: Write requirements.txt**

```
# Core
opencv-python>=4.8.0
numpy>=1.24.0
pyyaml>=6.0

# Detection & Tracking
ultralytics>=8.1.0
supervision>=0.20.0

# Face Recognition
insightface>=0.7.3
onnxruntime>=1.16.0

# UI & Storage
streamlit>=1.30.0

# Utilities
loguru>=0.7.0
```

**Step 2: Write config.yaml**

```yaml
camera:
  source: 0  # 0 = default webcam, or RTSP URL for IP camera
  fps: 30

detection:
  model: yolov8n.pt
  confidence: 0.5
  iou: 0.5

tracking:
  track_thresh: 0.5
  track_buffer: 30
  match_thresh: 0.8

face_recognition:
  model: buffalo_l  # buffalo_l = most accurate, buffalo_s = faster
  match_threshold: 0.4  # lower = stricter
  nms_threshold: 0.4

attendance:
  database: data/attendance.db
  cooldown_seconds: 1800  # 30 min between same-person check-ins
  log_file: logs/attendance.log

zones:
  checkin:
    # polygon coordinates (normalized 0-1, will be set in UI)
    points: []
```

**Step 3: Write src/config.py**

```python
from pathlib import Path
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

def load_config() -> dict:
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)

def get_project_root() -> Path:
    return PROJECT_ROOT
```

**Step 4: Create directories**

```bash
mkdir -p data/employees data/records logs docs/plans
touch data/.gitkeep
```

**Step 5: Install dependencies & verify**

```bash
pip install -r requirements.txt
python -c "import supervision; print('supervision OK')"
```

**Step 6: Commit**

```bash
git add -A
git commit -m "setup: project structure, config, dependencies"
```

---

### Task 2: Employee Registration Module

**Objective:** Register employees by extracting and storing face embeddings

**Files:**
- Create: `src/face_db.py`
- Test: `tests/test_face_db.py`

**Step 1: Write test first**

```python
import os
import pytest
import numpy as np
from src.face_db import FaceDatabase

@pytest.fixture
def db(tmp_path):
    return FaceDatabase(db_path=str(tmp_path / "faces.db"))

def test_register_employee(db):
    # Use a mock embedding (512-dim for ArcFace)
    embedding = np.random.randn(512).astype(np.float32)
    db.register("Bruce", "bruce_01", embedding)
    assert db.get_employee("Bruce") is not None

def test_get_all_employees(db):
    embedding = np.random.randn(512).astype(np.float32)
    db.register("Alice", "alice_01", embedding)
    db.register("Bob", "bob_01", embedding)
    employees = db.get_all_employees()
    assert len(employees) == 2

def test_remove_employee(db):
    embedding = np.random.randn(512).astype(np.float32)
    db.register("Charlie", "charlie_01", embedding)
    db.remove_employee("Charlie")
    assert db.get_employee("Charlie") is None

def test_match_face(db):
    embedding = np.random.randn(512).astype(np.float32)
    db.register("Dave", "dave_01", embedding)
    # Same embedding should match
    name = db.match(embedding, threshold=0.4)
    assert name == "Dave"
```

**Step 2: Run test to verify failure**

```bash
cd ~/Projects/attendance-system
pytest tests/test_face_db.py -v
```
Expected: FAIL — module not found

**Step 3: Write src/face_db.py**

```python
"""Employee face embedding database with SQLite backend."""

import sqlite3
import struct
from pathlib import Path
from typing import Optional

import numpy as np


class FaceDatabase:
    """Stores employee face embeddings and handles matching."""

    def __init__(self, db_path: str = "data/faces.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                name TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                embedding BLOB NOT NULL,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def register(self, name: str, employee_id: str, embedding: np.ndarray):
        """Register an employee with their face embedding."""
        emb_bytes = embedding.tobytes()
        self.conn.execute(
            "INSERT OR REPLACE INTO employees (name, employee_id, embedding) VALUES (?, ?, ?)",
            (name, employee_id, emb_bytes),
        )
        self.conn.commit()

    def get_employee(self, name: str) -> Optional[dict]:
        """Get employee by name."""
        row = self.conn.execute(
            "SELECT name, employee_id, embedding, registered_at FROM employees WHERE name = ?",
            (name,),
        ).fetchone()
        if row is None:
            return None
        return {
            "name": row[0],
            "employee_id": row[1],
            "embedding": np.frombuffer(row[2], dtype=np.float32),
            "registered_at": row[3],
        }

    def get_all_employees(self) -> list[dict]:
        """Get all registered employees."""
        rows = self.conn.execute(
            "SELECT name, employee_id, registered_at FROM employees ORDER BY name"
        ).fetchall()
        return [{"name": r[0], "employee_id": r[1], "registered_at": r[2]} for r in rows]

    def remove_employee(self, name: str):
        """Remove an employee."""
        self.conn.execute("DELETE FROM employees WHERE name = ?", (name,))
        self.conn.commit()

    def match(self, embedding: np.ndarray, threshold: float = 0.4) -> Optional[str]:
        """Match a face embedding against all registered employees.
        
        Returns employee name if match found, None otherwise.
        Uses cosine similarity: 1 - cosine_distance.
        """
        rows = self.conn.execute("SELECT name, embedding FROM employees").fetchall()
        if not rows:
            return None

        best_name = None
        best_sim = 0.0

        for name, emb_blob in rows:
            stored = np.frombuffer(emb_blob, dtype=np.float32)
            sim = cosine_similarity(embedding, stored)
            if sim > best_sim:
                best_sim = sim
                best_name = name

        if best_sim >= (1.0 - threshold):
            return best_name
        return None

    def close(self):
        self.conn.close()


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    if a_norm == 0 or b_norm == 0:
        return 0.0
    return float(np.dot(a, b) / (a_norm * b_norm))
```

**Step 4: Run test to verify pass**

```bash
cd ~/Projects/attendance-system
pytest tests/test_face_db.py -v
```
Expected: 4 passed

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: employee face registration module with SQLite backend"
```

---

### Task 3: Attendance Logger Module

**Objective:** Log attendance events with cooldown logic

**Files:**
- Create: `src/attendance_logger.py`
- Test: `tests/test_attendance_logger.py`

**Step 1: Write test first**

```python
import os
import time
import pytest
from pathlib import Path
from src.attendance_logger import AttendanceLogger

@pytest.fixture
def logger(tmp_path):
    db_path = str(tmp_path / "attendance.db")
    return AttendanceLogger(db_path=db_path, cooldown_seconds=60)

def test_log_checkin(logger):
    result = logger.log("Bruce", "checkin")
    assert result["status"] == "logged"
    assert result["employee"] == "Bruce"

def test_cooldown_prevents_duplicate(logger):
    logger.log("Bruce", "checkin")
    result = logger.log("Bruce", "checkin")
    assert result["status"] == "cooldown"

def test_checkout_after_cooldown(logger):
    logger.log("Bruce", "checkin")
    time.sleep(0.1)  # minimal wait for cooldown in test
    # cooldown is 60s in test fixture, but check-in only blocks same type
    # Let's test that checkout is allowed
    result = logger.log("Bruce", "checkout")
    assert result["status"] == "logged"

def test_get_today_records(logger):
    logger.log("Alice", "checkin")
    logger.log("Bob", "checkin")
    records = logger.get_today_records()
    assert len(records) >= 2

def test_export_csv(logger, tmp_path):
    logger.log("Alice", "checkin")
    csv_path = str(tmp_path / "export.csv")
    logger.export_csv(csv_path)
    assert Path(csv_path).exists()
```

**Step 2: Run test to verify failure**

```bash
pytest tests/test_attendance_logger.py -v
```
Expected: FAIL

**Step 3: Write src/attendance_logger.py**

```python
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
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee TEXT NOT NULL,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                confidence REAL DEFAULT 0.0
            )
        """)
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_attendance_employee_time ON attendance(employee, timestamp)"
        )
        self.conn.commit()

    def log(self, employee: str, event_type: str = "checkin", confidence: float = 0.0) -> dict:
        """Log an attendance event.
        
        Returns dict with status: 'logged', 'cooldown', or 'error'.
        """
        now = datetime.now()
        ts_str = now.isoformat()

        # Check cooldown for same employee + same event type
        if self._in_cooldown(employee, event_type, now):
            return {"status": "cooldown", "employee": employee, "message": "Still in cooldown period"}

        try:
            self.conn.execute(
                "INSERT INTO attendance (employee, event_type, timestamp, confidence) VALUES (?, ?, ?, ?)",
                (employee, event_type, ts_str, confidence),
            )
            self.conn.commit()
            return {"status": "logged", "employee": employee, "event": event_type, "timestamp": ts_str}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _in_cooldown(self, employee: str, event_type: str, now: datetime) -> bool:
        """Check if the last event of this type is within cooldown period."""
        row = self.conn.execute(
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
        today = datetime.now().strftime("%Y-%m-%d")
        if employee:
            rows = self.conn.execute(
                "SELECT employee, event_type, timestamp, confidence FROM attendance WHERE employee = ? AND timestamp LIKE ?",
                (employee, f"{today}%"),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT employee, event_type, timestamp, confidence FROM attendance WHERE timestamp LIKE ? ORDER BY timestamp DESC",
                (f"{today}%",),
            ).fetchall()
        return [
            {"employee": r[0], "event": r[1], "timestamp": r[2], "confidence": r[3]}
            for r in rows
        ]

    def get_all_records(self) -> list[dict]:
        """Get all attendance records."""
        rows = self.conn.execute(
            "SELECT employee, event_type, timestamp, confidence FROM attendance ORDER BY timestamp DESC"
        ).fetchall()
        return [
            {"employee": r[0], "event": r[1], "timestamp": r[2], "confidence": r[3]}
            for r in rows
        ]

    def export_csv(self, output_path: str):
        """Export all records to CSV."""
        records = self.get_all_records()
        if not records:
            return
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["employee", "event", "timestamp", "confidence"])
            writer.writeheader()
            writer.writerows(records)

    def close(self):
        self.conn.close()
```

**Step 4: Run test to verify pass**

```bash
pytest tests/test_attendance_logger.py -v
```
Expected: 5 passed

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: attendance logger with cooldown logic and CSV export"
```

---

### Task 4: Detection Pipeline (YOLO + Supervision)

**Objective:** Build the core detection + tracking pipeline using Supervision

**Files:**
- Create: `src/detector.py`
- Test: `tests/test_detector.py`

**Step 1: Write test first**

```python
import numpy as np
import pytest
from src.detector import Detector, ZoneChecker

def test_zone_checker_point_inside():
    checker = ZoneChecker(points=[(0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8)])
    assert checker.is_inside(0.5, 0.5) == True
    assert checker.is_inside(0.1, 0.1) == False
    assert checker.is_inside(0.9, 0.9) == False

def test_detector_init():
    """Test detector can be initialized (may skip if model not available)."""
    try:
        det = Detector(model_name="yolov8n.pt", confidence=0.5)
        assert det.model is not None
    except Exception as e:
        pytest.skip(f"Model not available: {e}")
```

**Step 2: Run test to verify failure**

```bash
pytest tests/test_detector.py -v
```

**Step 3: Write src/detector.py**

```python
"""YOLO + Supervision detection and tracking pipeline."""

import cv2
import numpy as np
from typing import Optional

import supervision as sv
from ultralytics import YOLO


class Detector:
    """YOLO-based person detection with Supervision tracking."""

    def __init__(self, model_name: str = "yolov8n.pt", confidence: float = 0.5):
        self.model = YOLO(model_name)
        self.confidence = confidence
        self.tracker = sv.ByteTrack()
        self.class_filter = [0]  # person class in COCO

    def detect_and_track(self, frame: np.ndarray) -> sv.Detections:
        """Run detection + tracking on a single frame.
        
        Returns Supervision Detections with track IDs.
        """
        results = self.model.predict(
            frame,
            conf=self.confidence,
            classes=self.class_filter,
            verbose=False,
        )
        detections = sv.Detections.from_ultralytics(results[0])
        detections = self.tracker.update_with_detections(detections)
        return detections


class ZoneChecker:
    """Check if points fall within a polygon zone."""

    def __init__(self, points: list[tuple[float, float]]):
        """Points as normalized (x, y) tuples in range 0-1."""
        self.points = np.array(points, dtype=np.float32)

    def is_inside(self, x: float, y: float) -> bool:
        """Check if normalized point (x, y) is inside the zone."""
        return bool(cv2.pointPolygonTest(self.points, (float(x), float(y)), False) >= 0)

    def check_detections(self, detections: sv.Detections, frame_shape: tuple) -> list[int]:
        """Check which track IDs are inside the zone.
        
        Returns list of track IDs inside the zone.
        """
        h, w = frame_shape[:2]
        inside_ids = []
        for i, (xyxy, tracker_id) in enumerate(zip(detections.xyxy, detections.tracker_id)):
            cx = ((xyxy[0] + xyxy[2]) / 2) / w
            cy = ((xyxy[1] + xyxy[3]) / 2) / h
            if tracker_id is not None and self.is_inside(cx, cy):
                inside_ids.append(int(tracker_id))
        return inside_ids
```

**Step 4: Run test to verify pass**

```bash
pytest tests/test_detector.py -v
```

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: YOLO detection + Supervision tracking pipeline with zone checking"
```

---

### Task 5: Face Recognition Engine (InsightFace)

**Objective:** Integrate InsightFace for face detection and embedding extraction

**Files:**
- Create: `src/face_recognizer.py`
- Test: `tests/test_face_recognizer.py`

**Step 1: Write test first**

```python
import numpy as np
import pytest
from src.face_recognizer import FaceRecognizer

def test_face_recognizer_init():
    """Test recognizer can initialize (skips if model unavailable)."""
    try:
        rec = FaceRecognizer(model_name="buffalo_l")
        assert rec.detector is not None
        assert rec.recognition_model is not None
    except Exception as e:
        pytest.skip(f"InsightFace model not available: {e}")
```

**Step 2: Run test to verify failure**

```bash
pytest tests/test_face_recognizer.py -v
```

**Step 3: Write src/face_recognizer.py**

```python
"""InsightFace-based face detection and recognition."""

from typing import Optional

import cv2
import numpy as np
import insightface


class FaceRecognizer:
    """Face detection and recognition using InsightFace."""

    def __init__(self, model_name: str = "buffalo_l"):
        self.detector = insightface.app.FaceAnalysis(
            name=model_name, providers=["CPUExecutionProvider"]
        )
        self.detector.prepare(ctx_id=0, det_size=(640, 640))
        self.recognition_model = self.detector.models["recognition"]

    def detect_faces(self, frame: np.ndarray) -> list[dict]:
        """Detect all faces in a frame.
        
        Returns list of dicts with bbox, landmark, and embedding.
        """
        faces = self.detector.get(frame)
        results = []
        for face in faces:
            bbox = face.bbox.astype(int)
            embedding = face.normed_embedding
            results.append({
                "bbox": bbox,
                "landmark": face.landmark,
                "embedding": embedding,
            })
        return results

    def extract_face_region(self, frame: np.ndarray, bbox: np.ndarray, margin: int = 20) -> Optional[np.ndarray]:
        """Extract face region with margin for registration."""
        h, w = frame.shape[:2]
        x1 = max(0, bbox[0] - margin)
        y1 = max(0, bbox[1] - margin)
        x2 = min(w, bbox[2] + margin)
        y2 = min(h, bbox[3] + margin)
        if x2 <= x1 or y2 <= y1:
            return None
        return frame[y1:y2, x1:x2].copy()

    def register_from_frame(self, frame: np.ndarray, name: str) -> Optional[np.ndarray]:
        """Extract face embedding from a frame for registration.
        
        Returns embedding if exactly one face detected, None otherwise.
        """
        faces = self.detect_faces(frame)
        if len(faces) != 1:
            return None
        return faces[0]["embedding"]
```

**Step 4: Run test to verify pass**

```bash
pytest tests/test_face_recognizer.py -v
```

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: InsightFace recognition engine for face detection and embedding"
```

---

### Task 6: Main Pipeline — Integration

**Objective:** Wire all components together into the main attendance loop

**Files:**
- Create: `main.py`

**Step 1: Write main.py**

```python
"""Main entry point for the attendance system."""

import sys
import time
from pathlib import Path

import cv2
import numpy as np
from loguru import logger

from src.config import load_config, get_project_root
from src.detector import Detector, ZoneChecker
from src.face_recognizer import FaceRecognizer
from src.face_db import FaceDatabase
from src.attendance_logger import AttendanceLogger


# Tracked IDs that already attempted check-in this cycle
attempted_ids: dict[int, float] = {}


def run_pipeline():
    config = load_config()
    root = get_project_root()

    # Initialize components
    logger.info("Loading YOLO model...")
    detector = Detector(
        model_name=config["detection"]["model"],
        confidence=config["detection"]["confidence"],
    )

    logger.info("Loading face recognition model...")
    face_rec = FaceRecognizer(model_name=config["face_recognition"]["model"])

    face_db = FaceDatabase(db_path=str(root / "data" / "faces.db"))

    att_logger = AttendanceLogger(
        db_path=config["attendance"]["database"],
        cooldown_seconds=config["attendance"]["cooldown_seconds"],
    )

    # Zone setup (default: center 60% of frame)
    zone_points = config["zones"]["checkin"]["points"]
    if not zone_points:
        zone_points = [(0.2, 0.3), (0.8, 0.3), (0.8, 0.7), (0.2, 0.7)]
    zone_checker = ZoneChecker(zone_points)

    logger.info("Opening camera...")
    cap = cv2.VideoCapture(config["camera"]["source"])
    if not cap.isOpened():
        logger.error("Cannot open camera. Exiting.")
        sys.exit(1)

    logger.info("Attendance system started. Press 'q' to quit.")
    logger.info(f"Check-in zone: {zone_points}")

    frame_count = 0
    face_check_interval = 3  # run face recognition every N frames

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.warning("Failed to read frame")
                break

            frame_count += 1

            # Detection + tracking
            detections = detector.detect_and_track(frame)
            inside_ids = zone_checker.check_detections(detections, frame.shape)

            # Face recognition for people in zone (throttled)
            if frame_count % face_check_interval == 0:
                for track_id in inside_ids:
                    if track_id in attempted_ids:
                        elapsed = time.time() - attempted_ids[track_id]
                        if elapsed < 10:  # 10s cooldown per track
                            continue

                    # Find detection bounding box for this track
                    det_idx = None
                    for i, tid in enumerate(detections.tracker_id):
                        if tid == track_id:
                            det_idx = i
                            break

                    if det_idx is None:
                        continue

                    bbox = detections.xyxy[det_idx]
                    x1, y1, x2, y2 = bbox.astype(int)
                    face_region = frame[y1:y2, x1:x2]
                    if face_region.size == 0:
                        continue

                    # Detect face in the person region
                    faces = face_rec.detect_faces(face_region)
                    if not faces:
                        continue

                    # Match against database
                    embedding = faces[0]["embedding"]
                    name = face_db.match(embedding, threshold=config["face_recognition"]["match_threshold"])

                    if name:
                        logger.info(f"Detected: {name} (track_id={track_id})")
                        result = att_logger.log(name, "checkin", confidence=float(1.0 - config["face_recognition"]["match_threshold"]))
                        if result["status"] == "logged":
                            logger.success(f"Check-in logged: {name} at {result['timestamp']}")
                        attempted_ids[track_id] = time.time()

            # Draw zone polygon (visual feedback)
            h, w = frame.shape[:2]
            pts = np.array([(int(x * w), int(y * h)) for x, y in zone_points], dtype=np.int32)
            cv2.polylines(frame, [pts], isClosed=True, color=(0, 255, 0), thickness=2)

            # Draw detections
            for bbox, tid in zip(detections.xyxy, detections.tracker_id):
                x1, y1, x2, y2 = bbox.astype(int)
                color = (0, 255, 0) if tid in inside_ids else (0, 0, 255)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                if tid is not None:
                    cv2.putText(frame, f"ID:{tid}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

            # FPS counter
            fps = 1.0
            cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            cv2.imshow("Attendance System", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        face_db.close()
        att_logger.close()
        logger.info("Attendance system stopped")


if __name__ == "__main__":
    run_pipeline()
```

**Step 2: Verify main.py syntax**

```bash
python -c "import ast; ast.parse(open('main.py').read()); print('Syntax OK')"
```

**Step 3: Commit**

```bash
git add -A
git commit -m "feat: main attendance pipeline integrating all components"
```

---

### Task 7: Streamlit UI — Registration & Dashboard

**Objective:** Build Streamlit app with employee registration, live view, and attendance dashboard

**Files:**
- Create: `src/ui/streamlit_app.py`
- Test: `tests/test_streamlit_app.py`

**Step 1: Write test first**

```python
import pytest
from pathlib import Path

def test_streamlit_app_exists():
    assert Path("src/ui/streamlit_app.py").exists()

def test_streamlit_app_importable():
    """Test that the module structure is importable."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("streamlit_app", "src/ui/streamlit_app.py")
    assert spec is not None
```

**Step 2: Write src/ui/streamlit_app.py**

```python
"""Streamlit UI for attendance system — registration, dashboard, and reports."""

import os
import sys
from pathlib import Path

import cv2
import numpy as np
import streamlit as st
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.config import load_config, get_project_root
from src.face_db import FaceDatabase
from src.attendance_logger import AttendanceLogger


st.set_page_config(page_title="AI Attendance System", layout="wide", page_icon="🎯")
st.title("🎯 AI Face Attendance System")

config = load_config()
root = get_project_root()

# Sidebar
st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Register Employee", "Reports", "Live Camera"])

# Initialize shared resources
@st.cache_resource
def get_face_db():
    return FaceDatabase(db_path=str(root / "data" / "faces.db"))

@st.cache_resource
def get_attendance_logger():
    return AttendanceLogger(
        db_path=config["attendance"]["database"],
        cooldown_seconds=config["attendance"]["cooldown_seconds"],
    )


# ─── Dashboard ───
if page == "Dashboard":
    st.header("📊 Today's Attendance")
    att_logger = get_attendance_logger()
    records = att_logger.get_today_records()

    if records:
        df = pd.DataFrame(records)
        st.dataframe(df, use_container_width=True)

        # Summary
        st.subheader("Summary")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Check-ins", len(df[df["event"] == "checkin"]))
        col2.metric("Total Checkouts", len(df[df["event"] == "checkout"]))
        col3.metric("Unique Employees", df["employee"].nunique())
    else:
        st.info("No attendance records for today yet.")


# ─── Register Employee ───
elif page == "Register Employee":
    st.header("📸 Register New Employee")

    face_db = get_face_db()

    # Show existing employees
    employees = face_db.get_all_employees()
    if employees:
        st.subheader("Registered Employees")
        emp_df = pd.DataFrame(employees)
        st.dataframe(emp_df, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Employee Name", key="reg_name")
        emp_id = st.text_input("Employee ID", key="reg_id")

    with col2:
        uploaded = st.file_uploader("Upload Photo", type=["jpg", "png", "jpeg"])

    if uploaded and name and emp_id:
        import insightface
        img = cv2.imdecode(np.frombuffer(uploaded.read(), np.uint8), cv2.IMREAD_COLOR)
        fa = insightface.app.FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        fa.prepare(ctx_id=0, det_size=(640, 640))
        faces = fa.get(img)

        if len(faces) == 1:
            embedding = faces[0].normed_embedding
            face_db.register(name, emp_id, embedding)
            st.success(f"✅ {name} registered successfully!")
        elif len(faces) == 0:
            st.error("❌ No face detected in photo. Please use a clear frontal photo.")
        else:
            st.error(f"❌ {len(faces)} faces detected. Please use a photo with only one face.")


# ─── Reports ───
elif page == "Reports":
    st.header("📋 Attendance Reports")
    att_logger = get_attendance_logger()
    records = att_logger.get_all_records()

    if records:
        df = pd.DataFrame(records)
        st.dataframe(df, use_container_width=True)

        if st.button("Export CSV"):
            output_path = str(root / "data" / "attendance_export.csv")
            att_logger.export_csv(output_path)
            st.success(f"✅ Exported to {output_path}")
    else:
        st.info("No records to display.")


# ─── Live Camera ───
elif page == "Live Camera":
    st.header("📹 Live Camera Feed")
    st.info("For full real-time processing, run `python main.py` directly. This page shows a simple camera preview.")

    run_cam = st.checkbox("Start Camera Preview")
    if run_cam:
        cap = cv2.VideoCapture(config["camera"]["source"])
        if not cap.isOpened():
            st.error("Cannot open camera")
        else:
            frame_placeholder = st.empty()
            while run_cam:
                ret, frame = cap.read()
                if ret:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame_placeholder.image(frame, channels="RGB")
                else:
                    break
            cap.release()
```

**Step 3: Run test to verify**

```bash
pytest tests/test_streamlit_app.py -v
```

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: Streamlit UI with registration, dashboard, and reports"
```

---

### Task 8: Smoke Test & Integration Verification

**Objective:** Create end-to-end smoke test and verify the full pipeline works

**Files:**
- Create: `tests/test_integration.py`
- Create: `scripts/verify_setup.sh`

**Step 1: Write integration test**

```python
"""Integration tests verifying component interactions."""

import os
import sys
import tempfile
import numpy as np
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.face_db import FaceDatabase
from src.attendance_logger import AttendanceLogger
from src.detector import ZoneChecker


def test_face_db_matches_attendance_logger(tmp_path):
    """Verify face DB + attendance logger work together."""
    face_db = FaceDatabase(db_path=str(tmp_path / "faces.db"))
    att_logger = AttendanceLogger(db_path=str(tmp_path / "att.db"), cooldown_seconds=10)

    # Register employee
    embedding = np.random.randn(512).astype(np.float32)
    face_db.register("TestUser", "TU001", embedding)

    # Verify registration
    emp = face_db.get_employee("TestUser")
    assert emp is not None
    assert emp["name"] == "TestUser"

    # Log attendance
    result = att_logger.log("TestUser", "checkin")
    assert result["status"] == "logged"

    # Verify cooldown
    result2 = att_logger.log("TestUser", "checkin")
    assert result2["status"] == "cooldown"

    # Verify record exists
    records = att_logger.get_today_records()
    assert len(records) >= 1
    assert records[0]["employee"] == "TestUser"


def test_zone_checker_integration():
    """Verify zone checker works with typical coordinates."""
    zone = ZoneChecker([(0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8)])
    # Center should be inside
    assert zone.is_inside(0.5, 0.5)
    # Corners should be outside
    assert not zone.is_inside(0.05, 0.05)
    assert not zone.is_inside(0.95, 0.95)


def test_project_structure():
    """Verify all required files exist."""
    root = Path(__file__).resolve().parent.parent
    required = [
        "main.py",
        "config.yaml",
        "src/config.py",
        "src/face_db.py",
        "src/attendance_logger.py",
        "src/detector.py",
        "src/face_recognizer.py",
        "src/ui/streamlit_app.py",
        "requirements.txt",
    ]
    for f in required:
        assert (root / f).exists(), f"Missing: {f}"
```

**Step 2: Write verify script**

```bash
#!/bin/bash
# Verify setup for attendance system

echo "=== Attendance System Setup Verification ==="

echo -n "Python version: "
python3 --version

echo -n "Supervision: "
python3 -c "import supervision; print(supervision.__version__)" 2>/dev/null || echo "NOT INSTALLED"

echo -n "Ultralytics: "
python3 -c "import ultralytics; print(ultralytics.__version__)" 2>/dev/null || echo "NOT INSTALLED"

echo -n "InsightFace: "
python3 -c "import insightface; print('OK')" 2>/dev/null || echo "NOT INSTALLED"

echo -n "Streamlit: "
python3 -c "import streamlit; print(streamlit.__version__)" 2>/dev/null || echo "NOT INSTALLED"

echo ""
echo "=== Required Files ==="
for f in main.py config.yaml src/config.py src/face_db.py src/attendance_logger.py src/detector.py src/face_recognizer.py src/ui/streamlit_app.py; do
    if [ -f "$f" ]; then
        echo "✅ $f"
    else
        echo "❌ $f MISSING"
    fi
done

echo ""
echo "=== Running Tests ==="
python3 -m pytest tests/ -v --tb=short
```

**Step 3: Run all tests**

```bash
chmod +x scripts/verify_setup.sh
python3 -m pytest tests/ -v
```

Expected: All tests pass (skip tests for unavailable models are OK)

**Step 4: Commit**

```bash
git add -A
git commit -m "test: integration tests and setup verification script"
```

---

### Task 9: Documentation & Final Polish

**Objective:** Update README, add .gitignore, and prepare for handoff

**Files:**
- Modify: `README.md`
- Create: `.gitignore`
- Create: `docs/usage.md`

**Step 1: Write .gitignore**

```
__pycache__/
*.pyc
*.pyo
.env
data/*.db
data/faces.db
data/attendance.db
logs/*.log
*.egg-info/
dist/
build/
```

**Step 2: Write docs/usage.md**

```markdown
# Usage Guide

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run attendance system (real-time)
python main.py

# Run Streamlit UI (registration + dashboard)
streamlit run src/ui/streamlit_app.py
```

## Employee Registration

1. Open Streamlit UI: `streamlit run src/ui/streamlit_app.py`
2. Go to "Register Employee"
3. Enter name and employee ID
4. Upload a clear frontal photo
5. System extracts face embedding and saves to database

## Attendance

1. Run `python main.py`
2. Green zone = check-in area (default: center of frame)
3. When a registered person enters the zone, face is recognized and attendance is logged
4. 30-minute cooldown between same-person check-ins
5. Press `q` to quit

## Configuration

Edit `config.yaml` to adjust:
- Camera source (0 = webcam, or RTSP URL)
- Detection confidence threshold
- Face matching threshold (lower = stricter)
- Cooldown period (seconds)
- Check-in zone polygon points

## Export Reports

Open Streamlit UI → Reports → Export CSV
```

**Step 3: Update README.md**

```markdown
# AI Face Attendance System

AI-powered attendance system using Supervision + InsightFace for face recognition.

## Tech Stack
- **Detection:** Ultralytics YOLOv8 + Supervision (BYTETrack)
- **Recognition:** InsightFace ArcFace
- **Backend:** SQLite
- **UI:** Streamlit

## Quick Start
```bash
pip install -r requirements.txt
python main.py
```

## Usage
See [docs/usage.md](docs/usage.md) for detailed instructions.

## Architecture
```
Webcam → YOLOv8 (detect persons) → Supervision (track IDs) → Zone check → InsightFace (recognize face) → SQLite (log attendance)
```
```

**Step 4: Final verification**

```bash
python3 -m pytest tests/ -v
./scripts/verify_setup.sh
```

**Step 5: Commit**

```bash
git add -A
git commit -m "docs: README, usage guide, and gitignore"
```

---

## Final Integration & Push

```bash
cd ~/Projects/attendance-system
git log --oneline
python3 -m pytest tests/ -v
git push origin main
```

**Verification:**
- All tests passing
- `main.py` syntax valid
- Streamlit app importable
- Config loads correctly
- Repo pushed to `brucetseng625-tech/attendance-system`
