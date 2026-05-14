"""YOLO + Supervision detection and tracking pipeline."""

import cv2
import numpy as np
from typing import Optional


class ZoneChecker:
    """Check if points fall within a polygon zone."""

    def __init__(self, points: list[tuple[float, float]]):
        """Points as normalized (x, y) tuples in range 0-1."""
        self.points = np.array(points, dtype=np.float32)

    def is_inside(self, x: float, y: float) -> bool:
        """Check if normalized point (x, y) is inside the zone."""
        return bool(cv2.pointPolygonTest(self.points, (float(x), float(y)), False) >= 0)

    def check_detections(self, detections, frame_shape: tuple) -> list[int]:
        """Check which track IDs are inside the zone.

        Args:
            detections: sv.Detections with xyxy and tracker_id attributes
            frame_shape: (height, width, ...) from frame.shape

        Returns list of track IDs inside the zone.
        """
        h, w = frame_shape[:2]
        inside_ids = []
        for xyxy, tracker_id in zip(detections.xyxy, detections.tracker_id):
            cx = ((xyxy[0] + xyxy[2]) / 2) / w
            cy = ((xyxy[1] + xyxy[3]) / 2) / h
            if tracker_id is not None and self.is_inside(cx, cy):
                inside_ids.append(int(tracker_id))
        return inside_ids


class Detector:
    """YOLO-based person detection with Supervision tracking."""

    def __init__(self, model_name: str = "yolov8n.pt", confidence: float = 0.5):
        import supervision as sv
        from ultralytics import YOLO

        self.model = YOLO(model_name)
        self.confidence = confidence
        self.tracker = sv.ByteTrack()
        self.class_filter = [0]  # person class in COCO

    def detect_and_track(self, frame: np.ndarray):
        """Run detection + tracking on a single frame.

        Returns Supervision Detections with track IDs.
        """
        import supervision as sv

        results = self.model.predict(
            frame,
            conf=self.confidence,
            classes=self.class_filter,
            verbose=False,
        )
        detections = sv.Detections.from_ultralytics(results[0])
        detections = self.tracker.update_with_detections(detections)
        return detections
