import pytest

import app as app_module


@pytest.fixture
def client():
    return app_module.create_app().test_client()


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


def test_unknown_route_returns_json_404(client):
    response = client.get("/nope")
    assert response.status_code == 404
    assert response.is_json
    assert "message" in response.get_json()


def test_wrong_method_returns_json_405(client):
    response = client.post("/status")
    assert response.status_code == 405
    assert response.is_json


def test_unexpected_error_returns_generic_json_500(client, monkeypatch):
    def explode(*_args, **_kwargs):
        raise RuntimeError("internal detail that must not leak")

    monkeypatch.setattr(app_module, "Crawler", explode)
    response = client.get("/keyword?keyword=nasa")
    assert response.status_code == 500
    assert response.get_json() == {"message": "Something went wrong"}
