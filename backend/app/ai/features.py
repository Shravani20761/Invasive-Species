"""Image preprocessing and feature extraction shared by training and inference."""

from __future__ import annotations

import numpy as np
from PIL import Image

FEATURE_VERSION = "colour-signature-v1"
IMAGE_SIZE = 160


def preprocess(image: Image.Image) -> np.ndarray:
    """Resize with Pillow and denoise with OpenCV when it is installed."""
    resized = image.convert("RGB").resize((IMAGE_SIZE, IMAGE_SIZE), Image.Resampling.BILINEAR)
    array = np.asarray(resized)
    try:
        import cv2

        bgr = cv2.cvtColor(array, cv2.COLOR_RGB2BGR)
        bgr = cv2.GaussianBlur(bgr, (3, 3), 0)
        array = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    except ImportError:
        pass
    return np.ascontiguousarray(array)


def extract_features(rgb: np.ndarray) -> np.ndarray:
    """Fixed-length colour and texture features. No randomness."""
    image = rgb.astype(np.float32) / 255.0
    mean = image.mean(axis=(0, 1))
    std = image.std(axis=(0, 1))
    red, green, blue = image[:, :, 0], image[:, :, 1], image[:, :, 2]
    maximum = image.max(axis=2)
    minimum = image.min(axis=2)
    delta = maximum - minimum
    saturation = np.where(maximum <= 1e-6, 0.0, delta / np.maximum(maximum, 1e-6))
    value = maximum
    hue = np.zeros_like(maximum)
    active = delta > 1e-6
    hue = np.where((maximum == red) & active, ((green - blue) / np.maximum(delta, 1e-6)) % 6, hue)
    hue = np.where((maximum == green) & active, ((blue - red) / np.maximum(delta, 1e-6)) + 2, hue)
    hue = np.where((maximum == blue) & active, ((red - green) / np.maximum(delta, 1e-6)) + 4, hue)
    hue = (hue / 6.0) % 1.0

    def fraction(mask: np.ndarray) -> float:
        return float(mask.mean())

    green_frac = fraction((hue > 0.20) & (hue < 0.46) & (saturation > 0.22) & (value > 0.15))
    blue_frac = fraction((hue > 0.50) & (hue < 0.72) & (saturation > 0.22))
    yellow_frac = fraction((hue > 0.10) & (hue < 0.18) & (saturation > 0.35) & (value > 0.45))
    orange_frac = fraction((hue > 0.02) & (hue <= 0.10) & (saturation > 0.40) & (value > 0.35))
    white_frac = fraction((value > 0.82) & (saturation < 0.20))
    brown_frac = fraction((hue > 0.04) & (hue < 0.14) & (value > 0.20) & (value < 0.72) & (saturation > 0.28))
    purple_frac = fraction((hue > 0.72) & (hue < 0.92) & (saturation > 0.22))
    dark_frac = fraction(value < 0.22)
    gray = image.mean(axis=2)
    gy, gx = np.gradient(gray)
    edge = float((np.hypot(gx, gy) > 0.08).mean())
    return np.array(
        [
            mean[0],
            mean[1],
            mean[2],
            std[0],
            std[1],
            std[2],
            float(hue.mean()),
            float(saturation.mean()),
            float(value.mean()),
            green_frac,
            blue_frac,
            yellow_frac,
            orange_frac,
            white_frac,
            brown_frac,
            purple_frac,
            dark_frac,
            edge,
        ],
        dtype=np.float64,
    )


def features_from_image(image: Image.Image) -> np.ndarray:
    return extract_features(preprocess(image))
