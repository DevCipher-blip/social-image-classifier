"""Decode untrusted image bytes with explicit format and pixel limits."""

import io
import warnings

from PIL import Image, UnidentifiedImageError

MAX_IMAGE_PIXELS = 40_000_000
ALLOWED_FORMATS = frozenset({"JPEG", "PNG", "GIF", "WEBP", "BMP"})

# Pillow only warns between 1x and 2x of this limit; decode_image turns that into a rejection.
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


class InvalidImage(ValueError):
    status_code = 400


class ImageTooLarge(InvalidImage):
    status_code = 413


def decode_image(data: bytes) -> Image.Image:
    if not data:
        raise InvalidImage("The uploaded file is empty")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            header = Image.open(io.BytesIO(data))
            if header.format not in ALLOWED_FORMATS:
                raise InvalidImage(f"Unsupported image format: {header.format}")
            if header.width * header.height > MAX_IMAGE_PIXELS:
                raise ImageTooLarge(f"Image exceeds {MAX_IMAGE_PIXELS} pixels")
            header.verify()

            image = Image.open(io.BytesIO(data))
            image.load()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise ImageTooLarge(f"Image exceeds {MAX_IMAGE_PIXELS} pixels") from error
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as error:
        if isinstance(error, InvalidImage):
            raise
        raise InvalidImage("The file is not a readable image") from error
    return image
