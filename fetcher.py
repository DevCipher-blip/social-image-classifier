"""Download Twitter media images, refusing anything that is not a plain pbs.twimg.com/media URL."""

import re
from urllib.parse import urlsplit, urlunsplit

import requests

ALLOWED_HOST = "pbs.twimg.com"
MEDIA_PATH = re.compile(r"/media/[A-Za-z0-9_-]{1,64}(\.(jpg|jpeg|png|webp|gif))?")
QUERY = re.compile(r"[A-Za-z0-9_=&.-]{0,200}")
TIMEOUT = (5, 15)
MAX_DOWNLOAD_BYTES = 10 * 1024 * 1024


class UnsafeImageURL(ValueError):
    pass


class FetchError(RuntimeError):
    pass


def validate_media_url(url: str) -> str:
    """Return a normalised media URL, or raise UnsafeImageURL.

    The crawler takes these links from scraped HTML, so they are untrusted: only https,
    the exact media host, no credentials or port, and a single /media/<id> path segment
    (which also rules out ../ and percent-encoded traversal).
    """
    parts = urlsplit(url)
    if parts.scheme != "https":
        raise UnsafeImageURL("Only https image links are fetched")
    if parts.netloc != ALLOWED_HOST:
        raise UnsafeImageURL(f"Only {ALLOWED_HOST} links are fetched, without credentials or port")
    if not MEDIA_PATH.fullmatch(parts.path):
        raise UnsafeImageURL("Only /media/<id> paths are fetched")
    if not QUERY.fullmatch(parts.query):
        raise UnsafeImageURL("Unexpected characters in the query string")
    return urlunsplit(("https", ALLOWED_HOST, parts.path, parts.query, ""))


def media_filename(url: str) -> str:
    return urlsplit(url).path.rsplit("/", 1)[-1]


def fetch_image_bytes(session: requests.Session, url: str) -> bytes:
    safe_url = validate_media_url(url)
    try:
        # Redirects stay off: a redirect would let the server send us to a host we never validated.
        with session.get(safe_url, timeout=TIMEOUT, stream=True, allow_redirects=False) as response:
            if response.status_code != 200:
                raise FetchError(f"Media host answered {response.status_code}")
            declared = response.headers.get("Content-Length")
            if declared and declared.isdigit() and int(declared) > MAX_DOWNLOAD_BYTES:
                raise FetchError("Image is larger than the download limit")
            body = bytearray()
            for chunk in response.iter_content(64 * 1024):
                body.extend(chunk)
                if len(body) > MAX_DOWNLOAD_BYTES:
                    raise FetchError("Image is larger than the download limit")
    except requests.RequestException as error:
        raise FetchError(f"Download failed: {type(error).__name__}") from error
    return bytes(body)
