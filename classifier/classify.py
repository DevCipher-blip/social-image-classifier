"""Label images with a pretrained torchvision VGG19 (ImageNet-1k classes)."""

import threading
from collections.abc import Callable
from pathlib import Path

import torch
from PIL import Image
from torchvision import models, transforms

from .model_config import DEVICE, IMAGE_SIZE, LABELS_PATH, MEAN, RESIZE_SIZE, STD

PREPROCESS = transforms.Compose(
    [
        transforms.Resize(RESIZE_SIZE),
        transforms.CenterCrop(IMAGE_SIZE),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ]
)


def load_labels(path: Path = LABELS_PATH) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_vgg19() -> torch.nn.Module:
    # Downloads ~550 MB of weights into the torch hub cache on first use.
    return models.vgg19(weights=models.VGG19_Weights.IMAGENET1K_V1)


class Classifier:
    """Holds one model per process; it is built lazily on the first prediction.

    Building VGG19 takes seconds and over half a gigabyte, so concurrent first
    requests must not each build their own copy: the lock makes the load happen once.
    """

    def __init__(
        self,
        model_factory: Callable[[], torch.nn.Module] = build_vgg19,
        labels: list[str] | None = None,
        device: str = DEVICE,
    ):
        self._model_factory = model_factory
        self._labels = labels if labels is not None else load_labels()
        self._device = device
        self._model: torch.nn.Module | None = None
        self._lock = threading.Lock()

    def _loaded_model(self) -> torch.nn.Module:
        if self._model is None:
            with self._lock:
                if self._model is None:
                    model = self._model_factory().to(self._device)
                    model.eval()
                    self._model = model
        return self._model

    def predict(self, image: Image.Image, filename: str) -> dict:
        model = self._loaded_model()
        batch = PREPROCESS(image.convert("RGB")).unsqueeze(0).to(self._device)
        with torch.no_grad():
            probabilities = torch.softmax(model(batch), dim=-1)[0]
        probability, index = probabilities.max(dim=0)
        return {
            "filename": filename,
            "label": self._labels[index.item()],
            "probability": round(probability.item() * 100, 2),
        }
