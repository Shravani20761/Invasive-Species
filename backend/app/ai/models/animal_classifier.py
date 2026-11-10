"""Animal-only classification pipeline."""

from __future__ import annotations

from PIL import Image

from app.ai.demo_model import predict_image


class AnimalClassifier:
    pipeline = "animal"

    def predict(self, image: Image.Image, threshold: float = 0.45) -> dict:
        result = predict_image(image, category="animal", threshold=threshold)
        result["pipeline"] = self.pipeline
        return result
