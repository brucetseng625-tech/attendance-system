"""Main entry point for the AI face attendance system."""

import sys
import time
from pathlib import Path

import cv2
import numpy as np
from loguru import logger

from src.attendance_logger import AttendanceLogger
from src.config import get_project_root, load_config
from src.detector import Detector, ZoneChecker
from src.face_db import FaceDatabase
from src.face_recognizer import FaceRecognizer


def setup_logging(config: dict) -> None:
    """Configure loguru to write to console and file."""
    log_file = config["attendance"].get("log_file", "logs/attendance.log")
    root = get_project_root()
    log_path = root / log_file
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger.remove()
    logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}")
    logger.add(str(log_path), level="DEBUG", rotation="1 day", retention="7 days")


def run_pipeline() -> None:
    """Run the main attendance pipeline loop."""
    config = load_config()
    root = get_project_root()

    setup_logging(config)

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
        db_path=str(root / config["attendance"]["database"]),
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

    # Tracking state
    attempted_ids: dict[int, float] = {}
    face_check_interval = 3
    frame_count = 0

    # FPS tracking
    fps_start = time.time()
    fps_frame_count = 0
    fps_value = 0.0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.warning("Failed to read frame")
                break

            # Flip frame horizontally (non-mirror mode, like a real mirror)
            frame = cv2.flip(frame, 1)

            frame_count += 1

            # Detection + tracking
            detections = detector.detect_and_track(frame)
            inside_ids = zone_checker.check_detections(detections, frame.shape)

            # Status message to display on video
            status_msg = ""

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
                            status_msg = f"{name} - 打卡成功!"
                        else:
                            status_msg = f"{name} - 偵測中 (冷卻中)"
                        attempted_ids[track_id] = time.time()

            # Draw status message on video
            if status_msg:
                # Background for text
                (w, h), _ = cv2.getTextSize(status_msg, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
                cv2.rectangle(frame, (10, 40), (w + 20, 40 + h + 20), (0, 0, 0), -1)
                cv2.putText(frame, status_msg, (15, 40 + h + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            # Draw zone polygon
            h, w = frame.shape[:2]
            pts = np.array([(int(x * w), int(y * h)) for x, y in zone_points], dtype=np.int32)
            cv2.polylines(frame, [pts], isClosed=True, color=(0, 255, 0), thickness=2)

            # Draw detections
            for bbox, tid in zip(detections.xyxy, detections.tracker_id):
                x1, y1, x2, y2 = bbox.astype(int)
                color = (0, 255, 0) if tid in inside_ids else (0, 0, 255)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                if tid is not None:
                    label = f"ID:{tid}"
                    cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

            # FPS calculation (smoothed over 1 second)
            fps_frame_count += 1
            fps_elapsed = time.time() - fps_start
            if fps_elapsed >= 1.0:
                fps_value = fps_frame_count / fps_elapsed
                fps_frame_count = 0
                fps_start = time.time()
            cv2.putText(frame, f"FPS: {fps_value:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

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
