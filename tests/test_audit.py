"""Owned by G5. Tests for wall.audit.record / recent / backfill."""

import json

import wall.audit as audit


def _isolate(monkeypatch, tmp_path):
    monkeypatch.setattr(audit, "AUDIT_FILE", tmp_path / "audit.jsonl")
    monkeypatch.setattr(audit, "RUNTIME_DIR", tmp_path / "runtime")
    monkeypatch.setattr(audit, "RESULTS_FILE", tmp_path / "results.json")


def test_record_appends_json_line(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    audit.record({"kind": "wall", "matter": "chen", "summary": "held", "counts": {"passed": 5}})
    lines = (tmp_path / "audit.jsonl").read_text().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["kind"] == "wall"
    assert entry["matter"] == "chen"
    assert entry["summary"] == "held"
    assert entry["counts"] == {"passed": 5}
    assert entry["timestamp"]


def test_recent_returns_newest_first_and_respects_limit(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    for i in range(5):
        audit.record({"kind": "eval", "summary": f"event {i}"})
    assert [e["summary"] for e in audit.recent(3)] == ["event 4", "event 3", "event 2"]
    assert len(audit.recent()) == 5


def test_record_never_raises(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    audit.record(None)
    audit.record({"counts": {"weird": object()}})
    audit.record("not a dict")
    # Uncreatable target must still not raise.
    blocker = tmp_path / "blocker"
    blocker.write_text("a file, not a directory")
    monkeypatch.setattr(audit, "AUDIT_FILE", blocker / "audit.jsonl")
    audit.record({"kind": "wall"})


def test_recent_missing_or_corrupt_file_returns_something_sane(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    assert audit.recent() == []
    (tmp_path / "audit.jsonl").write_text('{"kind": "wall"}\nnot json\n')
    assert audit.recent() == [{"kind": "wall"}]


def test_backfill_seeds_from_cache_and_results(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    cache = tmp_path / "runtime" / "demo_cache"
    cache.mkdir(parents=True)
    (cache / "wall.json").write_text(json.dumps({"passed": 5, "total": 5, "replayed": False}))
    (cache / "garbage.json").write_text("{oops")
    (tmp_path / "results.json").write_text(
        json.dumps({"regex": {"hard": {"caught": 0, "leaks": 102, "false_alarms": 0, "n": 200}}})
    )
    assert audit.backfill() == 2
    events = audit.recent()
    assert len(events) == 2
    kinds = {e["kind"] for e in events}
    assert kinds == {"wall", "eval"}
    wall = next(e for e in events if e["kind"] == "wall")
    assert wall["counts"] == {"passed": 5, "total": 5}
    assert "5/5" in wall["summary"]
    # Idempotent: second call is a no-op.
    assert audit.backfill() == 0
    assert len(audit.recent()) == 2
