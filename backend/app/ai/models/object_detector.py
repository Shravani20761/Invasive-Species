"""Object detection.

OpenCV contours provide a clearly labelled demo locator. If YOLO_WEIGHTS points
at a local YOLOv8 (or compatible Ultralytics) weights file, those weights are
used instead. COCO labels from a general detector are not treated as species names.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from app.core.config import get_settings


def _opencv_boxes(rgb: np.ndarray) -> dict:
    try:
        import cv2
    except ImportError:
        height, width = rgb.shape[:2]
        return {
            "detector": "unavailable",
            "note": "OpenCV is not installed, so no detection boxes were produced.",
            "boxes": [
                {
                    "label": "full_frame",
                    "score": None,
                    "x": 0,
                    "y": 0,
                    "width": int(width),
                    "height": int(height),
                }
            ],
        }
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 40, 120)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    height, width = gray.shape
    minimum = 0.02 * width * height
    boxes = []
    for contour in contours:
        x, y, box_w, box_h = cv2.boundingRect(contour)
        area = int(box_w * box_h)
        if area < minimum:
            continue
        boxes.append(
            {
                "label": "salient_region",
                "score": None,
                "x": int(x),
                "y": int(y),
                "width": int(box_w),
                "height": int(box_h),
                "area": area,
            }
        )
    boxes.sort(key=lambda item: item["area"], reverse=True)
    boxes = boxes[:5]
    if not boxes:
        boxes = [
            {
                "label": "full_frame",
                "score": None,
                "x": 0,
                "y": 0,
                "width": int(width),
                "height": int(height),
                "area": int(width * height),
            }
        ]
    return {
        "detector": "opencv_contour_demo",
        "note": "Boxes are OpenCV edge contours. They do not name a species. Configure YOLO_WEIGHTS for a general object detector.",
        "boxes": boxes,
    }


def _yolo_boxes(rgb: np.ndarray, weights: Path) -> dict | None:
    try:
        from ultralytics import YOLO
    except ImportError:
        return None
    model = YOLO(str(weights))
    results = model.predict(rgb, verbose=False)
    boxes = []
    for result in results:
        names = result.names
        if result.boxes is None:
            continue
        for box in result.boxes:
            xyxy = box.xyxy[0].tolist()
            class_id = int(box.cls[0])
            boxes.append(
                {
                    "label": str(names.get(class_id, class_id)),
                    "score": round(float(box.conf[0]), 4),
                    "x": int(xyxy[0]),
                    "y": int(xyxy[1]),
                    "width": int(xyxy[2] - xyxy[0]),
                    "height": int(xyxy[3] - xyxy[1]),
                }
            )
    return {
        "detector": "ultralytics_yolo",
        "weights": str(weights),
        "note": "Labels come from the configured detector weights, usually generic COCO classes. They are not invasive-species identifications.",
        "boxes": boxes,
    }


class ObjectDetector:
    def detect(self, image: Image.Image) -> dict:
        rgb = np.asarray(image.convert("RGB"))
        weights = get_settings().yolo_weights.strip()
        if weights:
            path = Path(weights)
            if not path.exists():
                opencv = _opencv_boxes(rgb)
                opencv["note"] = f"YOLO weights were configured but not found at {path}. {opencv['note']}"
                return opencv
            yolo = _yolo_boxes(rgb, path)
            if yolo is not None:
                return yolo
            opencv = _opencv_boxes(rgb)
            opencv["note"] = "Ultralytics is not installed, so detection fell back to OpenCV contours. " + opencv["note"]
            return opencv
        return _opencv_boxes(rgb)
