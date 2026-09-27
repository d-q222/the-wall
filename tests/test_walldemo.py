import json

import wall.walldemo as walldemo


class FakeClient:
    """Mimics walls.client.Client: a matter agent that only ever sees itself.

    Unit tests use this instead of the live GBrain server (walls.client.Client)
    so they stay deterministic and don't compete with other lanes for GBrain's
    rate-limited OAuth token endpoint. The live path is verified manually
    (uv run python walls/attack.py; POST /demo/api/wall).
    """

    def __init__(self, matter):
        self.matter = matter

    def search(self, query, source_id=None):
        if source_id == "__all__":
            raise PermissionError("refused: __all__ clamped to grant")
        if query == self.matter:
            return [{"source_id": self.matter, "slug": "intake"}]
        return []

    def get_page(self, slug, source_id=None):
        if source_id and source_id != self.matter:
            return {"error": "permission_denied"}
        return {"text": "own file"}


class BreachedClient(FakeClient):
    def get_page(self, slug, source_id=None):
        return {"text": "leaked content"}  # wall breached: no denial


def test_run_live_wall_holds(monkeypatch):
    monkeypatch.setattr(walldemo, "Client", FakeClient)
    result = walldemo._run_live("chen", "delmarva")

    assert result["total"] == 5
    assert result["passed"] == 5
    assert result["replayed"] is False
    assert all(c["passed"] for c in result["checks"])
    # the frontend matches on these substrings to animate/label each check
    names = [c["name"] for c in result["checks"]]
    assert any("recalls its own facts" in n for n in names)
    assert any("control" in n for n in names)
    assert any("searches for" in n for n in names)
    assert any("ALL sources" in n for n in names)
    assert any("opens" in n for n in names)


def test_run_live_reports_a_breach(monkeypatch):
    monkeypatch.setattr(walldemo, "Client", BreachedClient)
    result = walldemo._run_live("chen", "delmarva")

    assert result["passed"] < result["total"]
    failed = [c for c in result["checks"] if not c["passed"]]
    assert any("opens" in c["name"] for c in failed)


def test_attack_caches_last_success(tmp_path, monkeypatch):
    cache = tmp_path / "wall.json"
    monkeypatch.setattr(walldemo, "CACHE", cache)
    monkeypatch.setattr(walldemo, "Client", FakeClient)

    result = walldemo.attack("chen", "delmarva")
    assert result["replayed"] is False
    assert cache.exists()
    cached = json.loads(cache.read_text())["chen|delmarva"]
    assert cached["passed"] == 5
    assert cached["replayed"] is False


def test_attack_replays_legacy_single_result_cache(tmp_path, monkeypatch):
    # caches written before per-pair keys held one bare chen|delmarva result
    cache = tmp_path / "wall.json"
    cache.write_text(json.dumps({
        "checks": [
            {"name": "chen recalls its own facts", "call": "y", "result": "z", "passed": True},
            {"name": "delmarva reads its own file (control)", "call": "y", "result": "z", "passed": False},
        ],
        "passed": 1, "total": 2, "replayed": False,
    }))
    monkeypatch.setattr(walldemo, "CACHE", cache)

    def boom(*_a, **_k):
        raise RuntimeError("gbrain unreachable")

    monkeypatch.setattr(walldemo, "_run_live", boom)
    result = walldemo.attack("chen", "delmarva")
    assert result["replayed"] is True
    assert result["passed"] == 1


def test_attack_never_replays_another_pairs_result(tmp_path, monkeypatch):
    cache = tmp_path / "wall.json"
    monkeypatch.setattr(walldemo, "CACHE", cache)
    monkeypatch.setattr(walldemo, "Client", FakeClient)
    walldemo.attack("chen", "delmarva")

    def boom(*_a, **_k):
        raise RuntimeError("gbrain unreachable")

    monkeypatch.setattr(walldemo, "_run_live", boom)
    assert walldemo.attack("chen", "delmarva")["replayed"] is True
    try:
        walldemo.attack("chen", "reyes")
    except RuntimeError:
        pass
    else:
        raise AssertionError("replayed chen|delmarva for chen|reyes")
