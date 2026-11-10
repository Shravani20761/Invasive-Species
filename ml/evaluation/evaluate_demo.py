"""Score held-out synthetic signatures. This is not a field-photo evaluation."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.ai.demo_model import evaluate_bundle, load_bundle  # noqa: E402


def main() -> int:
    report = evaluate_bundle(load_bundle())
    print(report["note"])
    print(f"Hold-out accuracy on synthetic signatures: {report['accuracy']:.3f} ({report['samples']} images)")
    if report["accuracy"] < 0.9:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
