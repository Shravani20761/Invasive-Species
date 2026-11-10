"""Train the synthetic-signature demo classifier."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.ai.demo_model import train_and_save  # noqa: E402


def main() -> None:
    path = train_and_save()
    print(f"Saved demo classifier to {path}")
    print("This model is trained on synthetic colour signatures, not field photographs.")


if __name__ == "__main__":
    main()
