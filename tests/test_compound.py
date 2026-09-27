import json

import pytest

from wall import compound


def _fake_chen_draft(target: str, scrubbed_procedure: str) -> str:
    return (
        "1. This letter concerns the Chen Family Trust accounting.\n"
        "2. Victor Chen and Mei-Lin Chen Barros are owed an accounting of the $2,340,000 corpus.\n"
        "3. Please review the enclosed exhibit.\n"
        "4. Objections are due within 14 days.\n"
    )


def _fake_leaky_draft(target: str, scrubbed_procedure: str) -> str:
    return "This letter references Marcus Pruitt and the Salisbury yard incident."


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(compound, "CACHE", tmp_path / "compound.json")


def test_run_scrubs_source_facts_and_checks_clean_target(monkeypatch):
    monkeypatch.setattr(compound, "_draft_letter", _fake_chen_draft)

    result = compound.run(source="delmarva", target="chen")

    assert result["removed"] > 0
    for leak in ("Marcus Pruitt", "Hollis Freight Brokers", "$418,250", "$37,900"):
        assert leak not in result["scrubbed_procedure"]

    assert result["draft"]
    assert result["check"]["verdict"] == "clean"
    assert result["replayed"] is False
    assert '<mark class="fact">' in result["raw_procedure_html"]
    assert '<mark class="structure">' in result["draft_html"]


def test_run_flags_a_leaky_draft_against_the_source_matter(monkeypatch):
    monkeypatch.setattr(compound, "_draft_letter", _fake_leaky_draft)

    result = compound.run(source="delmarva", target="chen")

    assert result["check"]["verdict"] == "leak"
    assert any(hit["matter"] == "delmarva" for hit in result["check"]["hits"])


def test_run_replays_cached_result_when_the_llm_call_fails(monkeypatch):
    monkeypatch.setattr(compound, "_draft_letter", _fake_chen_draft)
    first = compound.run(source="delmarva", target="chen")
    assert compound.CACHE.exists()

    def _boom(target: str, scrubbed_procedure: str) -> str:
        raise RuntimeError("LLM down")

    monkeypatch.setattr(compound, "_draft_letter", _boom)
    second = compound.run(source="delmarva", target="chen")

    assert second["replayed"] is True
    assert second["draft"] == first["draft"]


def test_run_raises_when_llm_fails_and_no_cache_exists(monkeypatch):
    def _boom(target: str, scrubbed_procedure: str) -> str:
        raise RuntimeError("LLM down")

    monkeypatch.setattr(compound, "_draft_letter", _boom)

    with pytest.raises(RuntimeError):
        compound.run(source="delmarva", target="chen")
