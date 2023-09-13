import io

from tests.conftest import make_image_bytes
from tests.stub_server import create_stub_app


def test_stub_app_runs_the_whole_keyword_flow_offline():
    body = create_stub_app().test_client().get("/keyword?keyword=stub_demo").get_json()
    assert [p["filename"] for p in body["predictions"]] == ["StubPhotoA", "StubPhotoB"]
    assert {p["label"] for p in body["predictions"]} == {"sports_car, sport_car"}
    assert [s["reason"] for s in body["skipped"]] == ["Media host answered 404"]


def test_stub_app_classifies_uploads():
    client = create_stub_app().test_client()
    response = client.post("/file", data={"image": (io.BytesIO(make_image_bytes()), "a.png")})
    assert response.status_code == 200
