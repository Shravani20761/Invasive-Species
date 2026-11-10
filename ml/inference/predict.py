"""Run demo inference on one image file."""

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.ai.demo_model import predict_image  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python ml/inference/predict.py path/to/image.jpg [plant|animal]")
        return 1
    image = Image.open(sys.argv[1])
    category = sys.argv[2] if len(sys.argv) > 2 else None
    result = predict_image(image, category=category)
    print(result["demo_notice"])
    print(f"{result['predicted_common_name']} ({result['scientific_name']})")
    print(f"Confidence {result['confidence_percent']}% | insufficient={result['insufficient_confidence']}")
    print(result["message"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
