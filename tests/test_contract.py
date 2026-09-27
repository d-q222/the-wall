from fastapi.testclient import TestClient

from wall.contract import EvalResult
from wall.matters import matters, policy
from wall.server import app


def test_routes_exist():
    paths = {getattr(r, "path", None) for r in app.routes}
    assert {"/check", "/scrub", "/judge", "/deidentify"} <= paths


def test_fixtures_load():
    assert {"delmarva", "chen", "reyes"} <= set(matters())
    assert all(m["practice"] in policy() for m in matters().values())


def test_results_roundtrip(tmp_path, monkeypatch):
    from wall import results

    monkeypatch.setattr(results, "RESULTS", tmp_path / "results.json")
    results.record("regex", "hard", EvalResult(caught=0, leaks=102, false_alarms=0, clean=98, n=200))
    results.record("carryover", "hard", EvalResult(caught=1, leaks=102, false_alarms=0, clean=98, n=200))
    assert set(results.load()) == {"regex", "carryover"}
