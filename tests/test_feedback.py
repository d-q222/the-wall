import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from river import retrain
from wall import feedback

PASSAGE = "Dr. Adaeze Umeh led the Terraform Labs team in Lagos."


@pytest.fixture(autouse=True)
def tmp_runtime(tmp_path, monkeypatch):
    monkeypatch.setattr(feedback, "FEEDBACK", tmp_path / "feedback.jsonl")
    monkeypatch.setattr(retrain, "OUT", tmp_path / "river-retrain")
    monkeypatch.setattr(retrain, "STATE", tmp_path / "river-retrain" / "state.json")
    monkeypatch.setattr(retrain, "TRAIN", tmp_path / "river-retrain" / "train.jsonl")
    monkeypatch.setattr(retrain, "LOG", tmp_path / "river-retrain" / "train.log")
    monkeypatch.setattr(retrain, "K3_DATA", tmp_path / "k3" / "train.jsonl")
    monkeypatch.setattr(retrain, "K3_STATE", tmp_path / "k3" / "state.json")
    monkeypatch.setattr(retrain, "BLIND", tmp_path / "blind.jsonl")
    return tmp_path


def _missed(**kw):
    return {"matter_id": "o1-umeh", "practice": "immigration", "passage": PASSAGE,
            "kind": "missed", "span_text": "Adaeze", "replacement": "[PERSON]", **kw}


def test_record_appends_and_summary_counts():
    feedback.record(_missed())
    feedback.record(_missed(kind="wrong", span_text="Lagos", replacement=None))
    rows = feedback.load()
    assert len(rows) == 2 and rows[0]["span_text"] == "Adaeze"
    assert feedback.summary() == {"n": 2, "by_kind": {"missed": 1, "wrong": 1}}


def test_record_rejects_span_not_in_passage():
    with pytest.raises(ValueError):
        feedback.record(_missed(span_text="Nobody"))
    assert feedback.load() == []


def test_missed_becomes_chat_row_with_span_added():
    row = feedback.to_training_example(_missed(spans=[{"text": "Umeh", "replacement": "[PERSON]"}]))
    roles = [m["role"] for m in row["messages"]]
    assert roles == ["system", "user", "assistant"]
    assert row["messages"][1]["content"] == PASSAGE and "immigration" in row["messages"][0]["content"]
    spans = json.loads(row["messages"][2]["content"])["spans"]
    assert {"text": "Adaeze", "kind": "name", "replacement": "[PERSON]"} in spans
    assert {"text": "Umeh", "kind": "name", "replacement": "[PERSON]"} in spans


def test_numbered_placeholder_and_unknown_map_to_k3_kinds():
    spans = json.loads(feedback.to_training_example(_missed(replacement="[ORG_2]", span_text="Terraform Labs"))["messages"][2]["content"])["spans"]
    assert spans == [{"text": "Terraform Labs", "kind": "org", "replacement": "[ORG]"}]
    spans = json.loads(feedback.to_training_example(_missed(replacement=None, span_text="Lagos"))["messages"][2]["content"])["spans"]
    assert spans[0]["kind"] == "quasi_identifier"


def test_wrong_removes_span_from_target():
    c = _missed(kind="wrong", span_text="Lagos",
                spans=[{"text": "Lagos", "replacement": "[CITY]"}, {"text": "Umeh", "replacement": "[PERSON]"}])
    spans = json.loads(feedback.to_training_example(c)["messages"][2]["content"])["spans"]
    assert [s["text"] for s in spans] == ["Umeh"]


def test_build_set_merges_k3_rows_and_upsampled_feedback(tmp_runtime):
    k3 = tmp_runtime / "k3"
    k3.mkdir()
    base = {"messages": [{"role": "user", "content": "x"}, {"role": "assistant", "content": "{}"}]}
    (k3 / "train.jsonl").write_text("\n".join(json.dumps(base) for _ in range(5)) + "\n")
    (k3 / "state.json").write_text(json.dumps({"checkpoint_path": "river://k3/final"}))
    feedback.record(_missed())
    assert retrain.plan()["from_checkpoint"] == "river://k3/final"
    n, n_fb = retrain.build_set()
    assert (n, n_fb) == (5 + retrain.FEEDBACK_UPSAMPLE, 1)
    assert len(retrain.TRAIN.read_text().splitlines()) == n


def test_routes_record_list_and_guard_retrain(monkeypatch):
    app = FastAPI()
    app.include_router(feedback.router)
    client = TestClient(app)
    launched = []
    monkeypatch.setattr(retrain, "launch", lambda: launched.append(1) or {"job": "j"})

    assert client.post("/demo/api/feedback", json=_missed()).status_code == 200
    body = client.get("/demo/api/feedback").json()
    assert body["summary"]["n"] == 1 and body["retrain"]["plan"]["n_feedback"] == 1

    assert client.post("/demo/api/retrain", json={}).json()["launched"] is False
    assert launched == []
    assert client.post("/demo/api/retrain", json={"confirm": True}).json()["launched"] is True
    assert launched == [1]


def test_failed_retrain_keeps_last_good_checkpoint(monkeypatch):
    retrain.OUT.mkdir(parents=True)
    retrain.STATE.write_text(json.dumps({"status": "done", "checkpoint": "river://ours/final", "n_feedback": 1}))
    feedback.record(_missed())

    class P:
        pid = 999999999
    monkeypatch.setattr(retrain.subprocess, "Popen", lambda *a, **k: P())
    assert retrain.launch()["checkpoint"] == "river://ours/final"
    retrain._write_state(status="failed")
    assert retrain.start_checkpoint() == "river://ours/final"


def test_build_set_refuses_blind_set_overlap(tmp_runtime):
    draft = "A passage from the blind set that nobody may ever train on, long enough to match."
    (tmp_runtime / "blind.jsonl").write_text(json.dumps({"current": "x", "protected": [], "draft": draft, "label": "leak"}) + "\n")
    feedback.record(_missed(passage=draft + " Adaeze", span_text="Adaeze"))
    with pytest.raises(ValueError, match="blind"):
        retrain.build_set()
    assert not retrain.TRAIN.exists()
