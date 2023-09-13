import io

import pytest

import app as app_module
from tests.conftest import LABELS, make_image_bytes


class FakeCrawler:
    links = []

    def get_image_links(self, keyword):
        return list(self.links)


class FakeResponse:
    def __init__(self, content=b"", status_code=200, headers=None):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def iter_content(self, chunk_size):
        for start in range(0, len(self.content), chunk_size):
            yield self.content[start : start + chunk_size]


class FakeHttp:
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.requested = []

    def get(self, url, **kwargs):
        self.requested.append((url, kwargs))
        response = self.responses[url]
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture
def http():
    return FakeHttp()


@pytest.fixture
def client(classifier, http):
    FakeCrawler.links = []
    return app_module.create_app(
        classifier=classifier, crawler_factory=FakeCrawler, http=http
    ).test_client()


def upload(client, data, filename="photo.png"):
    return client.post(
        "/file",
        data={"image": (io.BytesIO(data), filename)},
        content_type="multipart/form-data",
    )


def test_status_reports_running(client):
    response = client.get("/status")
    assert response.status_code == 200
    assert response.get_json() == {"status": "API is up and running"}


def test_keyword_is_required(client):
    response = client.get("/keyword")
    assert response.status_code == 400
    assert "keyword" in response.get_json()["message"]


def test_file_upload_requires_image_field(client):
    response = client.post("/file", data={})
    assert response.status_code == 400
    assert "image" in response.get_json()["message"]


def test_file_upload_is_classified(client):
    response = upload(client, make_image_bytes())
    assert response.status_code == 200
    [prediction] = response.get_json()["predictions"]
    assert prediction["filename"] == "photo.png"
    assert prediction["label"] == LABELS[2]


def test_upload_filename_cannot_escape_and_is_not_written(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    response = upload(client, make_image_bytes(), filename="../../etc/evil.png")
    assert response.status_code == 200
    assert response.get_json()["predictions"][0]["filename"] == "etc_evil.png"
    assert list(tmp_path.iterdir()) == []


def test_each_request_only_reports_its_own_image(client):
    upload(client, make_image_bytes(), filename="first.png")
    response = upload(client, make_image_bytes(), filename="second.png")
    filenames = [p["filename"] for p in response.get_json()["predictions"]]
    assert filenames == ["second.png"]


def test_garbage_upload_is_a_json_400(client):
    response = upload(client, b"<?php echo 1; ?>", filename="shell.png")
    assert response.status_code == 400
    assert response.get_json() == {"message": "The file is not a readable image"}


def test_oversized_body_is_a_json_413(classifier):
    flask_app = app_module.create_app(classifier=classifier)
    flask_app.config["MAX_CONTENT_LENGTH"] = 1024
    response = upload(flask_app.test_client(), b"x" * 4096)
    assert response.status_code == 413
    assert response.is_json


def test_pixel_bomb_upload_is_a_json_413(client, monkeypatch):
    import imaging

    monkeypatch.setattr(imaging, "MAX_IMAGE_PIXELS", 100)
    response = upload(client, make_image_bytes())
    assert response.status_code == 413
    assert "pixels" in response.get_json()["message"]


def test_keyword_classifies_crawled_media(client, http):
    link = "https://pbs.twimg.com/media/AbC123?format=jpg&name=small"
    FakeCrawler.links = [link]
    http.responses[link] = FakeResponse(make_image_bytes(fmt="JPEG"))
    response = client.get("/keyword?keyword=nasa")
    assert response.status_code == 200
    [prediction] = response.get_json()["predictions"]
    assert prediction["label"] == LABELS[2]


def test_unknown_route_returns_json_404(client):
    response = client.get("/nope")
    assert response.status_code == 404
    assert response.is_json
    assert "message" in response.get_json()


def test_wrong_method_returns_json_405(client):
    response = client.post("/status")
    assert response.status_code == 405
    assert response.is_json


def test_unexpected_error_returns_generic_json_500(classifier):
    class BrokenCrawler:
        def get_image_links(self, keyword):
            raise RuntimeError("internal detail that must not leak")

    client = app_module.create_app(
        classifier=classifier, crawler_factory=BrokenCrawler
    ).test_client()
    response = client.get("/keyword?keyword=nasa")
    assert response.status_code == 500
    assert response.get_json() == {"message": "Something went wrong"}


def test_keyword_skips_unsafe_links_without_fetching_them(client, http):
    good = "https://pbs.twimg.com/media/Good1?format=png"
    FakeCrawler.links = [
        "http://pbs.twimg.com/media/Plain",
        "https://169.254.169.254/media/Meta",
        "https://pbs.twimg.com@evil.example/media/X",
        good,
    ]
    http.responses[good] = FakeResponse(make_image_bytes())
    body = client.get("/keyword?keyword=nasa").get_json()
    assert [p["filename"] for p in body["predictions"]] == ["Good1"]
    assert len(body["skipped"]) == 3
    assert [url for url, _ in http.requested] == [good]


def test_keyword_fetches_use_timeout_and_no_redirects(client, http):
    link = "https://pbs.twimg.com/media/Abc"
    FakeCrawler.links = [link]
    http.responses[link] = FakeResponse(make_image_bytes())
    client.get("/keyword?keyword=nasa")
    _, kwargs = http.requested[0]
    assert kwargs["timeout"] == (5, 15)
    assert kwargs["allow_redirects"] is False


def test_keyword_reports_failed_downloads_and_keeps_going(client, http):
    import requests

    slow, broken, good = (f"https://pbs.twimg.com/media/{name}" for name in ("Slow", "Gone", "Ok"))
    FakeCrawler.links = [slow, broken, good]
    http.responses[slow] = requests.Timeout("read timed out")
    http.responses[broken] = FakeResponse(status_code=404)
    http.responses[good] = FakeResponse(make_image_bytes())
    body = client.get("/keyword?keyword=nasa").get_json()
    assert [p["filename"] for p in body["predictions"]] == ["Ok"]
    assert [s["url"] for s in body["skipped"]] == [slow, broken]


def test_keyword_caps_number_of_images(client, http):
    links = [f"https://pbs.twimg.com/media/Img{i}" for i in range(15)]
    FakeCrawler.links = links
    for link in links:
        http.responses[link] = FakeResponse(make_image_bytes())
    body = client.get("/keyword?keyword=nasa").get_json()
    assert len(body["predictions"]) == 10
