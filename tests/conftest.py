import io
import threading

import pytest
import torch
from PIL import Image

from classifier import Classifier

LABELS = ["tabby cat", "golden retriever", "sports car"]


class StubModel(torch.nn.Module):
    """Stands in for VGG19: always favours one class and records how it was called."""

    def __init__(self, winning_index=2):
        super().__init__()
        self.winning_index = winning_index
        self.calls = []

    def forward(self, batch):
        self.calls.append(
            {
                "shape": tuple(batch.shape),
                "training": self.training,
                "grad": torch.is_grad_enabled(),
            }
        )
        logits = torch.zeros(batch.shape[0], len(LABELS))
        logits[:, self.winning_index] = 4.0
        return logits


class CountingFactory:
    def __init__(self):
        self.builds = 0
        self.model = StubModel()
        self._lock = threading.Lock()

    def __call__(self):
        with self._lock:
            self.builds += 1
        return self.model


@pytest.fixture
def model_factory():
    return CountingFactory()


@pytest.fixture
def classifier(model_factory):
    return Classifier(model_factory=model_factory, labels=LABELS, device="cpu")


def make_image_bytes(size=(64, 48), color=(200, 30, 30), fmt="PNG"):
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format=fmt)
    return buffer.getvalue()
