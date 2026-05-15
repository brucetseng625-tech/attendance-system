"""Silent Liveness Detection Module.

Uses Mini-FASNet to determine if a face is real or a spoof (photo/screen).
"""
import cv2
import numpy as np
import onnxruntime as ort
from pathlib import Path
from typing import Optional

# Standard input size for FASNet
INPUT_SIZE = (80, 80)

class LivenessDetector:
    """Detects liveness (Real vs Spoof) using ONNX model."""

    def __init__(self, model_path: str = "models/fasnet.onnx", providers: list = None):
        self.model_path = model_path
        
        if not Path(model_path).exists():
            raise FileNotFoundError(
                f"Liveness model not found at {model_path}.\n"
                "Please run: python scripts/download_models.py"
            )

        if providers is None:
            # Auto-detect best available provider
            providers = ["CPUExecutionProvider"]
            if "CUDAExecutionProvider" in ort.get_available_providers():
                providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]

        self.session = ort.InferenceSession(model_path, providers=providers)
        self.input_name = self.session.get_inputs()[0].name
        print(f"✅ Liveness Detector loaded ({providers[0]})")

    def preprocess(self, face_img: np.ndarray) -> np.ndarray:
        """Resize and normalize face image for the model."""
        # Resize to 80x80
        img = cv2.resize(face_img, INPUT_SIZE, interpolation=cv2.INTER_LINEAR)
        # HWC -> CHW
        img = img.transpose(2, 0, 1)
        # Normalize (standard for Mini-FASNet)
        img = (img.astype(np.float32) / 255.0 - 0.5) * 2.0
        # Add batch dimension: (1, 3, 80, 80)
        return np.expand_dims(img, axis=0)

    def predict(self, face_img: np.ndarray) -> float:
        """Run inference. Returns probability of being REAL."""
        input_tensor = self.preprocess(face_img)
        
        # Run model
        outputs = self.session.run(None, {self.input_name: input_tensor})
        
        # Output shape is usually [1, 3] for MiniFASNet (Real, Spoof1, Spoof2)
        scores = outputs[0][0]
        
        # Apply softmax if scores are logits
        scores = np.exp(scores) / np.sum(np.exp(scores))
        
        # Class 0 is typically Real in minivision-ai models
        real_score = scores[0]
        
        return float(real_score)

    def is_real(self, face_img: np.ndarray, threshold: float = 0.8) -> bool:
        """Check if the face is real based on threshold."""
        try:
            score = self.predict(face_img)
            return score > threshold
        except Exception as e:
            print(f"⚠️ Liveness check failed: {e}")
            return False # Fail closed for security
