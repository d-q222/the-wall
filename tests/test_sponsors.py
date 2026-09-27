from fastapi import FastAPI
from fastapi.testclient import TestClient

from wall import sponsors
from wall.contract import JudgeResponse


def _client(tmp_path, monkeypatch):
    monkeypatch.setattr(sponsors, "CACHE", tmp_path / "sponsors.json")
    app = FastAPI()
    app.include_router(sponsors.router)
    return TestClient(app)


def test_facts_shape(tmp_path, monkeypatch):
    body = _client(tmp_path, monkeypatch).get("/demo/api/stack").json()
    assert set(body) == {"gbrain", "river", "qm"}
    assert set(body["river"]["scores"]) == {"regex", "base_judge", "prompt_judge", "river_judge"}


def test_judge_live_then_replay(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(sponsors.judge_mod, "judge", lambda req: JudgeResponse(verdict="leak", evidence="$42,000"))
    live = c.post("/demo/api/stack/judge").json()
    assert live["verdict"] == "leak" and live["replayed"] is False and "Claude" in live["answered_by"]

    def boom(req):
        raise RuntimeError("down")

    monkeypatch.setattr(sponsors.judge_mod, "judge", boom)
    replay = c.post("/demo/api/stack/judge").json()
    assert replay["verdict"] == "leak" and replay["replayed"] is True and replay["at"] == live["at"]


def test_memorable_reports_mode(tmp_path, monkeypatch):
    class P:
        returncode = 0
        stdout = "memorable/ingest.sh: MODE=stub (x)\nmemorable/ingest.sh: recall check\nstep one\n"

    monkeypatch.setattr(sponsors.subprocess, "run", lambda *a, **k: P())
    body = _client(tmp_path, monkeypatch).post("/demo/api/stack/memorable").json()
    assert body["mode"] == "stub" and body["recall"] == "step one"
