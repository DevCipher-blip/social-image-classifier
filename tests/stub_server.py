"""Run the real API with a STUB model and canned Twitter data, fully offline.

For demos and the README examples only: the "model" always answers sports_car and
/keyword reads a fixed fake profile page whose media links are served as synthetic
images. Start it with:

    gunicorn --bind 127.0.0.1:8000 "tests.stub_server:create_stub_app()"
"""

import io

import torch
from PIL import Image

from app import create_app
from classifier import Classifier
from crawler import Crawler

STUB_LABEL_INDEX = 817  # "sports_car, sport_car" in labels.txt

FAKE_PROFILE = """
<img src="https://pbs.twimg.com/profile_images/1/avatar.jpg">
<img src="https://pbs.twimg.com/media/StubPhotoA?format=jpg&name=small">
<img src="https://pbs.twimg.com/media/StubPhotoB?format=png&name=small">
<img src="https://pbs.twimg.com/media/StubMissing?format=jpg&name=small">
"""


class StubModel(torch.nn.Module):
    def forward(self, batch):
        logits = torch.zeros(batch.shape[0], 1000)
        logits[:, STUB_LABEL_INDEX] = 8.0
        return logits


class _CannedResponse:
    def __init__(self, status_code, content=b""):
        self.status_code = status_code
        self.headers = {"Content-Length": str(len(content))}
        self._content = content

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def iter_content(self, chunk_size):
        yield self._content


class CannedMediaHost:
    """Plays pbs.twimg.com: synthetic images for StubPhoto*, 404 for anything else."""

    def get(self, url, **kwargs):
        if "/media/StubPhoto" not in url:
            return _CannedResponse(404)
        buffer = io.BytesIO()
        Image.new("RGB", (320, 240), (180, 40, 40)).save(buffer, format="JPEG")
        return _CannedResponse(200, buffer.getvalue())


def create_stub_app():
    return create_app(
        classifier=Classifier(model_factory=StubModel),
        crawler_factory=lambda: Crawler(page_source=lambda url: FAKE_PROFILE),
        http=CannedMediaHost(),
    )
