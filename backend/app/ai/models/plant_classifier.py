"""Plant-only classification pipeline.

The demo implementation filters the trained signature model to plant classes.
Load a plant-specific checkpoint by setting INFERENCE_MODE=weights and providing
ml/models/torch_species.pt trained with the plant and animal label map.
"""

from __future__ import annotations

from PIL import Image

from app.ai.demo_model import predict_image


class PlantClassifier:
    pipeline = "plant"

    def predict(self, image: Image.Image, threshold: float = 0.45) -> dict:
        result = predict_image(image, category="plant", threshold=threshold)
        result["pipeline"] = self.pipeline
        return result
