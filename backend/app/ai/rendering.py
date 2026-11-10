"""Render synthetic colour signatures. These are training patterns, not species photographs."""

from __future__ import annotations

import numpy as np

from app.ai.features import IMAGE_SIZE


def render_signature(entry: dict, rng: np.random.Generator, size: int = IMAGE_SIZE) -> np.ndarray:
    base = np.array(entry["base"], dtype=np.int16)
    noise = rng.integers(-16, 17, size=(size, size, 3), dtype=np.int16)
    canvas = np.clip(base + noise, 0, 255).astype(np.uint8)
    yy, xx = np.mgrid[0:size, 0:size]
    pattern = entry.get("pattern", "blobs")

    if pattern == "bands":
        band = np.array(entry["blobs"][0][0] if entry["blobs"] else entry["base"], dtype=np.int16)
        for y in range(0, size, 16):
            jitter = rng.integers(-10, 11, size=3)
            canvas[y : y + 5] = np.clip(band + jitter, 0, 255)
    elif pattern == "veins":
        vein = np.array(entry["blobs"][0][0] if entry["blobs"] else (180, 200, 120), dtype=np.int16)
        for offset in range(-size, size, 18):
            mask = np.abs(xx - yy - offset) <= 1
            canvas[mask] = np.clip(vein + rng.integers(-8, 9, size=3), 0, 255)
    elif pattern == "spots":
        color = np.array(entry["blobs"][0][0] if entry["blobs"] else (240, 240, 240), dtype=np.int16)
        for _ in range(16):
            cy = int(rng.integers(8, size - 8))
            cx = int(rng.integers(8, size - 8))
            radius = int(rng.integers(3, 8))
            mask = (yy - cy) ** 2 + (xx - cx) ** 2 <= radius**2
            canvas[mask] = np.clip(color + rng.integers(-8, 9, size=3), 0, 255)
    else:
        for color, fraction in entry.get("blobs", []):
            cy = int(rng.integers(size // 6, size - size // 6))
            cx = int(rng.integers(size // 6, size - size // 6))
            ry = max(6, int(size * (0.10 + fraction)))
            rx = max(6, int(size * (0.12 + fraction)))
            mask = ((yy - cy) / ry) ** 2 + ((xx - cx) / rx) ** 2 <= 1.0
            canvas[mask] = np.clip(np.array(color, dtype=np.int16) + rng.integers(-12, 13, size=3), 0, 255)
    return canvas
