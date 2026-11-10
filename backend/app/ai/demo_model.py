"""Demo species classifier.

The model is a scikit-learn logistic regression trained on colour and texture
signatures rendered from the demonstration catalogue. It is a real trained model.
It is not a field-trained species identifier, and it must not be described as one.

Production use requires species-specific weights and INFERENCE_MODE=weights.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from app.ai.catalog import CATALOG, by_scientific_name
from app.ai.features import FEATURE_VERSION, extract_features, preprocess
from app.ai.rendering import render_signature
from app.core.config import get_settings

MODEL_NAME = "synthetic-signature-logistic-regression"
MODEL_VERSION = "1.0.0"
_CACHED: dict | None = None


def train_bundle(samples_per_class: int = 36, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    features: list[np.ndarray] = []
    labels: list[str] = []
    for entry in CATALOG:
        for _ in range(samples_per_class):
            prepared = preprocess(Image.fromarray(render_signature(entry, rng)))
            features.append(extract_features(prepared))
            labels.append(entry["scientific_name"])
    x_train = np.vstack(features)
    y_train = np.array(labels)
    scaler = StandardScaler()
    scaled = scaler.fit_transform(x_train)
    classifier = LogisticRegression(max_iter=2000, random_state=seed)
    classifier.fit(scaled, y_train)
    centroids: dict[str, np.ndarray] = {}
    typical: dict[str, float] = {}
    for label in classifier.classes_:
        points = scaled[y_train == label]
        centroid = points.mean(axis=0)
        distances = np.linalg.norm(points - centroid, axis=1)
        centroids[str(label)] = centroid
        typical[str(label)] = float(np.percentile(distances, 90) + 1e-3)
    bundle = {
        "scaler": scaler,
        "classifier": classifier,
        "centroids": centroids,
        "typical_distance": typical,
        "metadata": {
            "name": MODEL_NAME,
            "version": MODEL_VERSION,
            "feature_version": FEATURE_VERSION,
            "inference_mode": "demo",
            "trained_on": "Synthetic colour and texture signatures generated from the demonstration catalogue. Not field photographs.",
            "limitation": "This model cannot reliably identify invasive species in real photographs. Replace it with trained weights for production monitoring.",
            "classes": [str(label) for label in classifier.classes_],
            "metrics": {},
        },
    }
    metrics = evaluate_bundle(bundle, seed=99)
    if metrics["accuracy"] < 0.9:
        raise RuntimeError(
            f"Demo classifier hold-out accuracy was {metrics['accuracy']:.2f}. "
            "Refusing to save a model that cannot separate its own synthetic signatures."
        )
    bundle["metadata"]["metrics"] = metrics
    return bundle


def evaluate_bundle(bundle: dict, seed: int = 99, samples_per_class: int = 12) -> dict:
    rng = np.random.default_rng(seed)
    correct = 0
    total = 0
    per_class: dict[str, list[int]] = {}
    for entry in CATALOG:
        hits = 0
        for _ in range(samples_per_class):
            rendered = preprocess(Image.fromarray(render_signature(entry, rng)))
            prediction = predict_array(rendered, bundle, threshold=0.0)
            total += 1
            matched = prediction["scientific_name"] == entry["scientific_name"]
            correct += int(matched)
            hits += int(matched)
        per_class[entry["scientific_name"]] = [hits, samples_per_class]
    return {
        "accuracy": correct / total if total else 0.0,
        "samples": total,
        "per_class": {key: value[0] / value[1] for key, value in per_class.items()},
        "holdout_seed": seed,
        "note": "Accuracy is measured on held-out synthetic signatures, not on field photographs.",
    }


def train_and_save(path: str | None = None) -> Path:
    settings = get_settings()
    target = Path(path or settings.model_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    bundle = train_bundle()
    joblib.dump(bundle, target)
    global _CACHED
    _CACHED = bundle
    return target


def load_bundle() -> dict:
    global _CACHED
    if _CACHED is not None:
        return _CACHED
    path = Path(get_settings().model_path)
    if not path.exists():
        train_and_save(str(path))
    _CACHED = joblib.load(path)
    return _CACHED


def clear_model_cache() -> None:
    global _CACHED
    _CACHED = None


def predict_array(rgb: np.ndarray, bundle: dict | None = None, category: str | None = None, threshold: float = 0.45) -> dict:
    bundle = bundle or load_bundle()
    features = extract_features(rgb).reshape(1, -1)
    scaled = bundle["scaler"].transform(features)[0]
    classifier = bundle["classifier"]
    probabilities = classifier.predict_proba(scaled.reshape(1, -1))[0]
    classes = [str(label) for label in classifier.classes_]
    catalogue = by_scientific_name()
    allowed = np.ones(len(classes), dtype=bool)
    if category:
        allowed = np.array([catalogue[label]["category"] == category for label in classes])
    masked = probabilities.copy()
    masked[~allowed] = 0.0
    if float(masked.sum()) <= 0:
        raise ValueError(f"No catalogue classes are available for category '{category}'.")
    conditional = masked / masked.sum()
    order = np.argsort(conditional)[::-1]
    top_index = int(order[0])
    label = classes[top_index]
    centroid = bundle["centroids"][label]
    distance = float(np.linalg.norm(scaled - centroid))
    typical = float(bundle["typical_distance"][label])
    similarity = float(np.exp(-max(0.0, distance - typical) / typical))
    confidence = float(conditional[top_index] * similarity)
    insufficient = confidence < threshold
    entry = catalogue[label]
    alternatives = []
    for index in order[:3]:
        alternative = classes[int(index)]
        alt_distance = float(np.linalg.norm(scaled - bundle["centroids"][alternative]))
        alt_typical = float(bundle["typical_distance"][alternative])
        alt_similarity = float(np.exp(-max(0.0, alt_distance - alt_typical) / alt_typical))
        alt_confidence = float(conditional[int(index)] * alt_similarity)
        alternatives.append(
            {
                "scientific_name": alternative,
                "common_name": catalogue[alternative]["common_name"],
                "category": catalogue[alternative]["category"],
                "confidence": round(alt_confidence, 4),
            }
        )
    if insufficient:
        message = (
            "Confidence is below the configured threshold. The closest demonstration-catalogue "
            "signature is shown for review only and is not a species determination."
        )
        classification = "unknown"
        risk_level = None
        recommended = "manual_review_required"
    else:
        message = (
            "Demo classifier match against a synthetic colour signature. "
            "This is not a field-trained identification and still requires researcher verification."
        )
        classification = entry["classification"]
        risk_level = entry["risk_level"]
        recommended = "priority_review" if classification == "invasive" else "standard_review"
    return {
        "inference_mode": "demo",
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "demo_notice": bundle["metadata"]["limitation"],
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
        "raw_scores": {
            "class_probability": round(float(conditional[top_index]), 4),
            "signature_similarity": round(similarity, 4),
            "centroid_distance": round(distance, 4),
            "typical_distance": round(typical, 4),
            "probabilities": {classes[i]: round(float(conditional[i]), 4) for i in range(len(classes)) if allowed[i]},
        },
    }


def predict_image(image: Image.Image, category: str | None = None, threshold: float = 0.45) -> dict:
    return predict_array(preprocess(image), category=category, threshold=threshold)
