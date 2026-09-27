"""Unit tests for wall.judge. The LLM is always mocked here; no network calls."""

from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from wall.contract import JudgeRequest
from wall.judge import JudgeError, judge

REQ = JudgeRequest(
    current="reyes: Client Luisa Reyes v. Parkside Terrace Apartments.",
    protected=["chen: Client Wen Chen, breach of contract, settlement $50,000."],
    draft="Please find our position below.",
)


@dataclass
class _TextBlock:
    text: str
    type: str = "text"


def _fake_client(*texts: str) -> MagicMock:
    client = MagicMock()
    client.messages.create.side_effect = [
        MagicMock(content=[_TextBlock(text=t)]) for t in texts
    ]
    return client


def test_judge_leak_verdict():
    client = _fake_client('{"verdict": "leak", "matter": "chen", "evidence": "settlement $50,000"}')
    resp = judge(REQ, client=client)
    assert resp.verdict == "leak"
    assert resp.matter == "chen"
    assert resp.evidence == "settlement $50,000"
    assert client.messages.create.call_count == 1


def test_judge_clean_verdict():
    client = _fake_client('{"verdict": "clean", "matter": null, "evidence": null}')
    resp = judge(REQ, client=client)
    assert resp.verdict == "clean"
    assert resp.matter is None
    assert resp.evidence is None


def test_judge_uppercase_verdict_is_normalized():
    client = _fake_client('{"verdict": "LEAK", "matter": "chen", "evidence": "x"}')
    resp = judge(REQ, client=client)
    assert resp.verdict == "leak"


def test_judge_retries_once_on_malformed_json():
    client = _fake_client("not json", '{"verdict": "clean", "matter": null, "evidence": null}')
    resp = judge(REQ, client=client)
    assert resp.verdict == "clean"
    assert client.messages.create.call_count == 2


def test_judge_raises_after_second_malformed():
    client = _fake_client("not json", "still not json")
    with pytest.raises(JudgeError):
        judge(REQ, client=client)
    assert client.messages.create.call_count == 2


def test_judge_raises_on_bad_verdict_value():
    client = _fake_client(
        '{"verdict": "maybe", "matter": null, "evidence": null}',
        '{"verdict": "clean", "matter": null, "evidence": null}',
    )
    resp = judge(REQ, client=client)
    assert resp.verdict == "clean"
    assert client.messages.create.call_count == 2
