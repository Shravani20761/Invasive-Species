"""Catalogue ranking with BioCLIP.

BioCLIP is a vision model trained on TreeOfLife-10M, a dataset of biological
photographs labelled by taxon. This module scores an uploaded photo against the
demonstration catalogue. The score is a ranking among those species, not an
open-world identification, and a low score is not a species determination.
"""

from __future__ import annotations

import threading

import numpy as np
from PIL import Image

from app.ai.catalog import CATALOG

MODEL_NAME = "bioclip-treeoflife-10m"
MODEL_ID = "hf-hub:imageomics/bioclip"
MODEL_VERSION = "imageomics/bioclip"
NOTICE = (
    "BioCLIP score against the demonstration catalogue. The model was trained on "
    "TreeOfLife-10M biological photographs. The percentage is how this photo ranks "
    "among those catalogue species, not a certified field identification."
)
_LOCK = threading.Lock()
_STATE: tuple | None = None
_TEXT: dict[str, tuple[list[dict], object]] = {}


def _load():
    global _STATE
    if _STATE is not None:
        return _STATE
    with _LOCK:
        if _STATE is not None:
            return _STATE
        try:
            import torch
            import open_clip
        except ImportError as exc:
            raise RuntimeError(
                "BioCLIP is not installed. Install torch and open_clip_torch, or use INFERENCE_MODE=demo."
            ) from exc
        torch.set_num_threads(1)
        if hasattr(open_clip, "create_model_from_pretrained"):
            model, preprocess = open_clip.create_model_from_pretrained(MODEL_ID)
        else:
            model, _train_preprocess, preprocess = open_clip.create_model_and_transforms(MODEL_ID)
        tokenizer = open_clip.get_tokenizer(MODEL_ID)
        model.eval()
        _STATE = (model, preprocess, tokenizer, torch)
        return _STATE


def _catalogue(category: str | None) -> list[dict]:
    if category in (None, ""):
        return list(CATALOG)
    entries = [entry for entry in CATALOG if entry["category"] == category]
    if not entries:
        raise ValueError(f"No catalogue classes are available for category '{category}'.")
    return entries


def _text_features(category: str | None, model, tokenizer, torch):
    key = category or "both"
    cached = _TEXT.get(key)
    if cached is not None:
        return cached
    entries = _catalogue(category)
    tokens = tokenizer([entry["scientific_name"] for entry in entries])
    with torch.no_grad():
        features = model.encode_text(tokens)
        features = features / features.norm(dim=-1, keepdim=True)
    _TEXT[key] = (entries, features)
    return _TEXT[key]


def predict_image(image: Image.Image, category: str | None = None, threshold: float = 0.45) -> dict:
    model, preprocess, tokenizer, torch = _load()
    entries, text_features = _text_features(category, model, tokenizer, torch)
    prepared = preprocess(image.convert("RGB")).unsqueeze(0)
    with torch.no_grad():
        image_features = model.encode_image(prepared)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        scale = model.logit_scale.exp() if hasattr(model, "logit_scale") else 1.0
        probabilities = torch.softmax(scale * image_features @ text_features.T, dim=-1)[0]
    scores = probabilities.detach().cpu().numpy().astype(float)
    order = np.argsort(scores)[::-1]
    top = int(order[0])
    runner_up = float(scores[int(order[1])]) if len(order) > 1 else 0.0
    margin = float(scores[top] - runner_up)
    confidence = float(scores[top] * (1.0 if margin >= 0.08 else margin / 0.08))
    insufficient = confidence < threshold
    entry = entries[top]
    alternatives = []
    for index in order[:3]:
        alternative = entries[int(index)]
        alternatives.append(
            {
                "scientific_name": alternative["scientific_name"],
                "common_name": alternative["common_name"],
                "category": alternative["category"],
                "confidence": round(float(scores[int(index)]), 4),
            }
        )
    if insufficient:
        message = (
            "Confidence is below the configured threshold. The closest catalogue species "
            "is shown for review only and is not a species determination."
        )
        classification = "unknown"
        risk_level = None
        recommended = "manual_review_required"
    else:
        message = (
            "BioCLIP ranked this photograph among the demonstration-catalogue species. "
            "A person still needs to verify the record before it is treated as a detection."
        )
        classification = entry["classification"]
        risk_level = entry["risk_level"]
        recommended = "priority_review" if classification == "invasive" else "standard_review"
    return {
        "inference_mode": "bioclip",
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "demo_notice": NOTICE,
        "predicted_common_name": entry["common_name"],
        "scientific_name": entry["scientific_name"],
        "category": entry["category"],
        "classification": classification,
        "catalogue_classification": entry["classification"],
        "confidence": round(confidence, 4),
        "confidence_percent": round(confidence * 100, 1),
        "insufficient_confidence": insufficient,
        "risk_level": risk_level,
        "description": entry["description"],
        "characteristics": entry["characteristics"],
        "distribution": entry["distribution"],
        "recommended_verification_status": recommended,
        "message": message,
        "alternatives": alternatives,
        "pipeline": "plant_and_animal" if category in (None, "") else category,
        "raw_scores": {
            "class_probability": round(float(scores[top]), 4),
            "margin": round(margin, 4),
            "dataset": "TreeOfLife-10M",
            "probabilities": {
                entries[int(index)]["scientific_name"]: round(float(scores[int(index)]), 4) for index in order
            },
        },
    }
