"""Main entry point for the AI face attendance system."""

import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from loguru import logger

from src.attendance_logger import AttendanceLogger
from src.config import get_project_root, load_config
from src.detector import Detector, ZoneChecker
from src.face_db import FaceDatabase
from src.face_recognizer import FaceRecognizer
from src.exception_manager import ExceptionManager
from src.guard_engine import GuardEngine, GuardStatus


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

    # Guard Mode Components
    guard_engine = GuardEngine(config)
    exception_manager = ExceptionManager(db_path=str(root / config["guard_mode"]["exception_db"]))

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

    # Multi-person status messages: list of {"text": str, "color": tuple, "expires_at": float, "y_pos": int}
    active_messages: list[dict] = []

    # FPS tracking
    fps_start = time.time()
    fps_frame_count = 0
    fps_value = 0.0

    # Font configuration (macOS standard Chinese font)
    font_path = "/System/Library/Fonts/STHeiti Medium.ttc"
    font_size = 28
    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        logger.warning("Could not load Chinese font, falling back to default")
        font = ImageFont.load_default()

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
                        
                        # Check cooldown status
                        is_cooldown = (result["status"] != "logged")

                        # Check exception status if guard mode is enabled
                        is_exempted = False
                        if guard_engine.enabled:
                            is_exempted = exception_manager.is_exempted(name)

                        # Determine status via Guard Engine
                        status_obj = guard_engine.get_status(
                            name=name,
                            is_cooldown=is_cooldown,
                            is_exempted=is_exempted
                        )

                        # Add to active messages
                        current_time = time.time()
                        
                        # Filter expired first
                        active_messages = [m for m in active_messages if m["expires_at"] > current_time]
                        
                        # Assign Y position based on stack
                        y_pos = 50
                        for existing in sorted(active_messages, key=lambda m: m["y_pos"]):
                            y_pos = existing["y_pos"] + 60  # Vertical spacing
                        
                        active_messages.append({
                            "text": status_obj.message,
                            "color": status_obj.color,
                            "expires_at": current_time + 5.0,  # Show for 5 seconds
                            "y_pos": y_pos,
                            "is_success": not status_obj.is_abnormal
                        })
                        
                        attempted_ids[track_id] = time.time()

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

            # Draw persistent status messages (multi-person support)
            if active_messages:
                # Filter out expired messages (refresh)
                current_time = time.time()
                active_messages = [
                    msg for msg in active_messages
                    if msg["expires_at"] > current_time
                ]
                
                # Sort by y_pos to draw top to bottom
                active_messages.sort(key=lambda m: m["y_pos"])

                # Convert frame once for PIL
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_frame = Image.fromarray(frame_rgb)
                draw = ImageDraw.Draw(pil_frame)

                # Draw each message
                x_start = 10
                padding = 10

                for msg in active_messages:
                    text = msg["text"]
                    y_pos = msg["y_pos"]
                    # Color comes from status_obj (RGB)
                    border_color = msg.get("color", (0, 255, 0))
                    
                    # Calculate text bounding box
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_w = bbox[2] - bbox[0]
                    text_h = bbox[3] - bbox[1]

                    box_x2 = x_start + text_w + padding * 2
                    box_y2 = y_pos + text_h + padding * 2

                    draw.rectangle([x_start, y_pos, box_x2, box_y2], fill=(0, 0, 0))
                    draw.rectangle([x_start, y_pos, box_x2, box_y2], outline=border_color, width=2)

                    # Draw text
                    draw.text((x_start + padding, y_pos + padding), text, fill=border_color, font=font)

                # Convert back to OpenCV format
                frame = cv2.cvtColor(np.array(pil_frame), cv2.COLOR_RGB2BGR)

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
