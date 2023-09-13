import io

import pytest
from PIL import Image

import imaging
from imaging import ImageTooLarge, InvalidImage, decode_image
from tests.conftest import make_image_bytes


@pytest.mark.parametrize("fmt", ["PNG", "JPEG", "GIF", "WEBP", "BMP"])
def test_common_formats_decode(fmt):
    image = decode_image(make_image_bytes(fmt=fmt))
    assert image.size == (64, 48)


def test_pillow_global_limit_is_set():
    assert Image.MAX_IMAGE_PIXELS == imaging.MAX_IMAGE_PIXELS


@pytest.mark.parametrize("data", [b"", b"not an image at all", make_image_bytes()[:40]])
def test_garbage_and_truncated_files_are_rejected(data):
    with pytest.raises(InvalidImage):
        decode_image(data)


def test_unsupported_format_is_rejected():
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8)).save(buffer, format="TIFF")
    with pytest.raises(InvalidImage, match="Unsupported"):
        decode_image(buffer.getvalue())


def test_pixel_bomb_is_rejected_before_decoding(monkeypatch):
    monkeypatch.setattr(imaging, "MAX_IMAGE_PIXELS", 1000)
    with pytest.raises(ImageTooLarge):
        decode_image(make_image_bytes(size=(50, 50)))


def test_real_limit_rejects_huge_dimensions():
    buffer = io.BytesIO()
    Image.new("1", (8000, 6000)).save(buffer, format="PNG")
    with pytest.raises(ImageTooLarge):
        decode_image(buffer.getvalue())
