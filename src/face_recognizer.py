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
