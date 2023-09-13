import pytest
import requests

from fetcher import (
    MAX_DOWNLOAD_BYTES,
    FetchError,
    UnsafeImageURL,
    fetch_image_bytes,
    media_filename,
    validate_media_url,
)


@pytest.mark.parametrize(
    "url",
    [
        "https://pbs.twimg.com/media/FzQ1abc_DEF-9",
        "https://pbs.twimg.com/media/FzQ1abc.jpg",
        "https://pbs.twimg.com/media/FzQ1abc?format=jpg&name=small",
    ],
)
def test_genuine_media_links_are_accepted(url):
    assert validate_media_url(url) == url


def test_fragment_is_dropped():
    assert validate_media_url("https://pbs.twimg.com/media/A#x") == "https://pbs.twimg.com/media/A"


@pytest.mark.parametrize(
    "url",
    [
        "http://pbs.twimg.com/media/A",
        "file:///etc/passwd",
        "//pbs.twimg.com/media/A",
        "https://evil.example/media/A",
        "https://pbs.twimg.com.evil.example/media/A",
        "https://pbs.twimg.com./media/A",
        "https://PBS.TWIMG.COM/media/A",
        "https://user:pw@pbs.twimg.com/media/A",
        "https://pbs.twimg.com@169.254.169.254/media/A",
        "https://pbs.twimg.com:8080/media/A",
        "https://pbs.twimg.com:443/media/A",
        "https://127.0.0.1/media/A",
        "https://pbs.twimg.com/profile_images/1/a.jpg",
        "https://pbs.twimg.com/media/../../admin",
        "https://pbs.twimg.com/media/%2e%2e/admin",
        "https://pbs.twimg.com/media/a%2Fb",
        "https://pbs.twimg.com/media\\..\\admin",
        "https://pbs.twimg.com/media/A/B",
        "https://pbs.twimg.com/media/",
        "https://pbs.twimg.com/media/A?next=http://evil.example/",
    ],
)
def test_unsafe_links_are_refused(url):
    with pytest.raises(UnsafeImageURL):
        validate_media_url(url)


def test_media_filename_is_last_segment():
    assert media_filename("https://pbs.twimg.com/media/Abc.jpg?name=small") == "Abc.jpg"


class StreamResponse:
    def __init__(self, chunks, status_code=200, headers=None):
        self.chunks = chunks
        self.status_code = status_code
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def iter_content(self, chunk_size):
        yield from self.chunks


class OneResponseSession:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


URL = "https://pbs.twimg.com/media/Abc"


def test_fetch_streams_with_timeout_and_without_redirects():
    session = OneResponseSession(StreamResponse([b"ab", b"cd"]))
    assert fetch_image_bytes(session, URL) == b"abcd"
    _, kwargs = session.calls[0]
    assert kwargs == {"timeout": (5, 15), "stream": True, "allow_redirects": False}


def test_redirect_response_is_not_followed():
    session = OneResponseSession(StreamResponse([], status_code=302))
    with pytest.raises(FetchError, match="302"):
        fetch_image_bytes(session, URL)


def test_declared_oversize_is_refused():
    headers = {"Content-Length": str(MAX_DOWNLOAD_BYTES + 1)}
    session = OneResponseSession(StreamResponse([b"x"], headers=headers))
    with pytest.raises(FetchError, match="limit"):
        fetch_image_bytes(session, URL)


def test_streamed_oversize_is_refused_without_content_length():
    chunk = b"x" * (1024 * 1024)
    session = OneResponseSession(StreamResponse([chunk] * 11))
    with pytest.raises(FetchError, match="limit"):
        fetch_image_bytes(session, URL)


@pytest.mark.parametrize("error", [requests.Timeout(), requests.ConnectionError()])
def test_network_errors_become_fetch_errors(error):
    with pytest.raises(FetchError):
        fetch_image_bytes(OneResponseSession(error), URL)


def test_unsafe_url_is_never_requested():
    session = OneResponseSession(StreamResponse([b"x"]))
    with pytest.raises(UnsafeImageURL):
        fetch_image_bytes(session, "https://evil.example/media/Abc")
    assert session.calls == []
