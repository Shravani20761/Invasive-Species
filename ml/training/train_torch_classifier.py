"""Train a small PyTorch classifier when torch is installed and a labelled folder exists.

Expected layout:
  ml/datasets/field/<scientific_name>/*.jpg

Labels are the folder names. This script does not download weights and does not invent labels.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    try:
        import torch
        import torch.nn as nn
        from PIL import Image
        from torch.utils.data import DataLoader, Dataset
    except ImportError:
        print("PyTorch is not installed. Use ml/training/train_demo_classifier.py, or install backend/requirements-ml.txt.")
        return 1
    data_dir = ROOT / "ml" / "datasets" / "field"
    if not data_dir.exists():
        print(f"No labelled image folder at {data_dir}.")
        print("Create one class folder per scientific name, add photographs, then rerun this script.")
        return 1
    classes = sorted(path.name for path in data_dir.iterdir() if path.is_dir())
    if len(classes) < 2:
        print("Need at least two class folders to train a transfer-learning head.")
        return 1

    class FolderImages(Dataset):
        def __init__(self):
            self.items = []
            for index, label in enumerate(classes):
                for image_path in (data_dir / label).glob("*"):
                    if image_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                        self.items.append((image_path, index))

        def __len__(self):
            return len(self.items)

        def __getitem__(self, index):
            path, label = self.items[index]
            image = Image.open(path).convert("RGB").resize((160, 160))
            tensor = torch.tensor(list(image.getdata()), dtype=torch.float32).reshape(160, 160, 3) / 255.0
            return tensor.permute(2, 0, 1), label

    dataset = FolderImages()
    if len(dataset) < len(classes):
        print("Each class folder needs at least one image.")
        return 1
    loader = DataLoader(dataset, batch_size=8, shuffle=True)
    model = nn.Sequential(
        nn.Conv2d(3, 16, 3, stride=2, padding=1),
        nn.ReLU(),
        nn.Conv2d(16, 32, 3, stride=2, padding=1),
        nn.ReLU(),
        nn.AdaptiveAvgPool2d((1, 1)),
        nn.Flatten(),
        nn.Linear(32, len(classes)),
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.CrossEntropyLoss()
    model.train()
    for _epoch in range(5):
        for inputs, labels in loader:
            optimizer.zero_grad()
            loss = loss_fn(model(inputs), labels)
            loss.backward()
            optimizer.step()
    destination = ROOT / "ml" / "models" / "torch_species.pt"
    destination.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "labels": classes,
            "backbone": "tiny",
            "categories": {},
            "metadata": {
                "name": "torch-folder-classifier",
                "version": "1.0.0",
                "limitation": "Trained only on the local folder you provided. Verify before operational use.",
            },
        },
        destination,
    )
    print(f"Saved checkpoint to {destination}. Set INFERENCE_MODE=weights to use it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
