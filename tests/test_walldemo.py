import json

import wall.walldemo as walldemo


def test_attack_chen_vs_delmarva_wall_holds():
    result = walldemo.attack("chen", "delmarva")
    assert result["total"] == 5
    assert result["passed"] == 5
    assert result["replayed"] is False
    assert all(c["passed"] for c in result["checks"])
    names = [c["name"] for c in result["checks"]]
    assert any("recalls its own facts" in n for n in names)
    assert any("control" in n for n in names)


def test_attack_caches_last_success(tmp_path, monkeypatch):
    cache = tmp_path / "wall.json"
    monkeypatch.setattr(walldemo, "CACHE", cache)

    walldemo.attack("chen", "delmarva")
    assert cache.exists()
    cached = json.loads(cache.read_text())
    assert cached["replayed"] is False


def test_attack_replays_cache_on_live_failure(tmp_path, monkeypatch):
    cache = tmp_path / "wall.json"
    cache.write_text(json.dumps({
        "checks": [{"name": "x", "call": "y", "result": "z", "passed": True}],
        "passed": 1, "total": 1, "replayed": False,
    }))
    monkeypatch.setattr(walldemo, "CACHE", cache)

    def boom(*_a, **_k):
        raise RuntimeError("gbrain unreachable")

    monkeypatch.setattr(walldemo, "_run_live", boom)
    result = walldemo.attack("chen", "delmarva")
    assert result["replayed"] is True
    assert result["passed"] == 1
