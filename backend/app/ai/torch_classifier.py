"""Optional PyTorch classifier.

Used only when INFERENCE_MODE=weights and ml/models/torch_species.pt exists.
If the checkpoint or PyTorch is missing, the service returns an error.
It does not invent a prediction.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from app.ai.features import preprocess
from app.core.config import get_settings


class TorchSpeciesClassifier:
    def __init__(self, weights_path: Path):
        import torch
        import torch.nn as nn

        checkpoint = torch.load(weights_path, map_location="cpu", weights_only=False)
        labels: list[str] = checkpoint["labels"]
        model = _build_model(nn, len(labels), checkpoint.get("backbone", "tiny"))
        model.load_state_dict(checkpoint["state_dict"])
        model.eval()
        self.torch = torch
        self.model = model
        self.labels = labels
        self.categories = checkpoint.get("categories", {})
        self.metadata = checkpoint.get("metadata", {})

    def predict(self, image: Image.Image, category: str | None, threshold: float) -> dict:
        tensor = self._tensor(image)
        with self.torch.no_grad():
            logits = self.model(tensor)
            probabilities = self.torch.softmax(logits, dim=1)[0].cpu().numpy()
        allowed = np.ones(len(self.labels), dtype=bool)
        if category:
            allowed = np.array([self.categories.get(label) == category for label in self.labels])
            if not allowed.any():
                raise ValueError(f"Checkpoint has no classes for category '{category}'.")
        masked = probabilities.copy()
        masked[~allowed] = 0.0
        masked = masked / masked.sum()
        index = int(np.argmax(masked))
        confidence = float(masked[index])
        insufficient = confidence < threshold
        return {
            "inference_mode": "weights",
            "model_name": self.metadata.get("name", "torch-species-classifier"),
            "model_version": self.metadata.get("version", "unversioned"),
            "demo_notice": self.metadata.get(
                "limitation",
                "Prediction from the configured PyTorch checkpoint.",
            ),
            "predicted_common_name": self.labels[index],
            "scientific_name": self.labels[index],
            "category": self.categories.get(self.labels[index]),
            "classification": "unknown" if insufficient else self.metadata.get("classifications", {}).get(self.labels[index], "unknown"),
            "catalogue_classification": self.metadata.get("classifications", {}).get(self.labels[index], "unknown"),
            "confidence": round(confidence, 4),
            "confidence_percent": round(confidence * 100, 1),
            "insufficient_confidence": insufficient,
            "risk_level": None if insufficient else self.metadata.get("risk_levels", {}).get(self.labels[index]),
            "description": self.metadata.get("descriptions", {}).get(self.labels[index], ""),
            "characteristics": "",
            "distribution": "",
            "recommended_verification_status": "manual_review_required" if insufficient else "priority_review",
            "message": "PyTorch checkpoint prediction. Verify it before using it in monitoring.",
            "alternatives": [],
            "raw_scores": {"probabilities": {self.labels[i]: round(float(masked[i]), 4) for i in range(len(self.labels)) if allowed[i]}},
            "pipeline": category or "both",
        }

    def _tensor(self, image: Image.Image):
        array = preprocess(image).astype("float32") / 255.0
        tensor = self.torch.from_numpy(array).permute(2, 0, 1).unsqueeze(0)
        return tensor


def _build_model(nn, n_classes: int, backbone: str):
    if backbone == "tiny":
        return nn.Sequential(
            nn.Conv2d(3, 16, 3, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(16, 32, 3, stride=2, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((1, 1)),
            nn.Flatten(),
            nn.Linear(32, n_classes),
        )
    raise ValueError(f"Unsupported checkpoint backbone '{backbone}'.")


_TORCH_MODEL: TorchSpeciesClassifier | None = None


def load_torch_classifier() -> TorchSpeciesClassifier:
    global _TORCH_MODEL
    if _TORCH_MODEL is not None:
        return _TORCH_MODEL
    path = Path(get_settings().torch_weights_path)
    if not path.exists():
        raise FileNotFoundError(
            f"INFERENCE_MODE=weights but no checkpoint was found at {path}. "
            "Train one with ml/training/train_torch_classifier.py or switch INFERENCE_MODE=demo."
        )
    try:
        _TORCH_MODEL = TorchSpeciesClassifier(path)
    except ImportError as exc:
        raise RuntimeError("PyTorch is not installed. Install backend/requirements-ml.txt.") from exc
    return _TORCH_MODEL
