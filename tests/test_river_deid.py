import json

import pytest

from wall import river_deid

TEXT = "Dr. Ada Vell, the only person to chair the Kest Review twice, earns $200,000."


def test_system_prompt_carries_the_practice_policy():
    prompt = river_deid.system_prompt("immigration")
    assert "salary" in prompt and "recommender identities" in prompt
    assert "quasi_identifier" in prompt


def test_parse_keeps_exact_substrings_and_normalises_kinds():
    completion = json.dumps({"spans": [
        {"text": "Dr. Ada Vell", "kind": "name"},
        {"text": "the only person to chair the Kest Review twice", "kind": "weird"},
        {"text": "$999", "kind": "amount"},
        {"text": "Dr. Ada Vell", "kind": "name"},
    ]})
    spans = river_deid.parse(TEXT, "<think>x</think>" + completion)
    assert [s["text"] for s in spans] == ["Dr. Ada Vell", "the only person to chair the Kest Review twice"]
    assert spans[1] == {"text": spans[1]["text"], "kind": "quasi_identifier", "replacement": "[QUASI_IDENTIFIER]"}


def test_parse_tolerates_garbage():
    assert river_deid.parse(TEXT, "no json here") == []
    assert river_deid.parse(TEXT, "{not json}") == []


def test_spans_caches_live_success_and_replays_on_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(river_deid, "CACHE_PATH", tmp_path / "cache.json")
    monkeypatch.setattr(river_deid, "sample_many",
                        lambda texts, p, m: ['{"spans":[{"text":"$200,000","kind":"amount"}]}'])
    live = river_deid.spans(TEXT)
    assert live == [{"text": "$200,000", "kind": "amount", "replacement": "[AMOUNT]"}]

    def boom(*a):
        raise RuntimeError("river down")

    monkeypatch.setattr(river_deid, "sample_many", boom)
    assert river_deid.spans(TEXT) == [{**live[0], "replayed": True}]
    with pytest.raises(RuntimeError):
        river_deid.spans("never seen before")


def test_training_data_never_reads_the_blind_set_or_held_out_matters():
    from pathlib import Path

    from river.deid import make_data

    source = Path(make_data.__file__).read_text()
    assert "blind" not in source and "the-wall/data" not in source
    assert make_data.TRAIN_MATTERS == ["o1-achterberg", "o1-umeh"]
