from fastapi.testclient import TestClient

from wall.server import app


def test_root_redirects_to_welcome():
    r = TestClient(app).get("/", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert r.headers["location"] == "/demo/welcome.html"
