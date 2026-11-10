"""Identification service.

Demo mode uses the trained synthetic-signature model through separate plant and
animal pipelines. Weights mode loads a PyTorch checkpoint and fails clearly if
that checkpoint is missing. Neither mode invents a label when it cannot score an image.
"""

from __future__ import annotations

from fastapi import HTTPException
from PIL import Image

from app.ai.models.animal_classifier import AnimalClassifier
from app.ai.models.object_detector import ObjectDetector
from app.ai.models.plant_classifier import PlantClassifier
from app.core.config import get_settings


def identify_image(image: Image.Image, category: str | None, threshold: float) -> dict:
    mode = get_settings().inference_mode
    if mode == "weights":
        result = _predict_weights(image, category, threshold)
    elif category == "plant":
        result = PlantClassifier().predict(image, threshold)
    elif category == "animal":
        result = AnimalClassifier().predict(image, threshold)
    elif category in (None, ""):
        plant = PlantClassifier().predict(image, threshold)
        animal = AnimalClassifier().predict(image, threshold)
        result = plant if plant["confidence"] >= animal["confidence"] else animal
        result["pipeline"] = "plant_and_animal"
    else:
        raise HTTPException(status_code=400, detail="Species category must be plant or animal.")
    result["detections"] = ObjectDetector().detect(image)
    result["preprocessing"] = "Pillow RGB resize and OpenCV Gaussian blur when OpenCV is installed."
    return result


def _predict_weights(image: Image.Image, category: str | None, threshold: float) -> dict:
    try:
        from app.ai.torch_classifier import load_torch_classifier

        return load_torch_classifier().predict(image, category, threshold)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
