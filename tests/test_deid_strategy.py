import json

from evals.bakeoff.run import choose
from wall import deid_strategy


def test_load_defaults_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(deid_strategy, "STRATEGY_PATH", tmp_path / "missing.json")
    assert deid_strategy.load() == ["facts", "rules"]


def test_load_reads_chosen_detectors(tmp_path, monkeypatch):
    path = tmp_path / "deid_strategy.json"
    path.write_text(json.dumps({"detectors": ["rules", "river_tuned"]}))
    monkeypatch.setattr(deid_strategy, "STRATEGY_PATH", path)
    assert deid_strategy.load() == ["rules", "river_tuned"]


def test_detect_merges_overlaps_and_skips_failing_detector(monkeypatch):
    text = "Dr. Ana Duarte won the Kessler Prize in Lisbon."

    def boom(*_):
        raise RuntimeError("no key")

    monkeypatch.setitem(deid_strategy.DETECTORS, "a", lambda *_: [{"text": "Ana Duarte", "kind": "name"}])
    monkeypatch.setitem(deid_strategy.DETECTORS, "b", lambda *_: [{"text": "Duarte won", "kind": "quasi_identifier"},
                                                                    {"text": "Lisbon", "kind": "location"}])
    monkeypatch.setitem(deid_strategy.DETECTORS, "c", boom)
    spans = deid_strategy.detect(text, detectors=["a", "b", "c"])
    assert [(s["text"], s["kind"]) for s in spans] == [("Ana Duarte won", "name"), ("Lisbon", "location")]
    assert all(text[s["start"]:s["end"]] == s["text"] for s in spans)


def test_choose_respects_overredaction_cap_then_tiebreaks():
    m = lambda r, q, o, ms: {"identifier_recall": r, "quasi_recall": q,  # noqa: E731
                             "over_redaction": o, "latency_ms_per_paragraph": ms}
    results = {
        "greedy": m(1.0, 1.0, 0.30, 1),
        "slow": m(0.9, 0.8, 0.05, 900),
        "fast": m(0.9, 0.8, 0.05, 1),
        "weak": m(0.7, 1.0, 0.00, 0),
    }
    assert choose(results, 0.10) == "fast"
    assert choose(results, 0.50) == "greedy"
