"""End-to-end smoke tests over HTTP against a FastAPI TestClient (no real network).

/judge (B2) and /deidentify (C2) run for real with the anthropic SDK mocked --
no live LLM call, no cost, no network.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from wall.matters import matters
from wall.server import app

client = TestClient(app)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.fixture
def mock_anthropic(monkeypatch):
    """Stand in for the anthropic Python SDK (see CLAUDE.md: WALL_LLM_MODEL /
    'via the anthropic Python SDK'). Patches the class so any `anthropic.Anthropic(...)`
    construction returns a fake client whose `.messages.create(...)` answers with a
    minimal, valid JSON verdict -- no network call, no API key needed, no cost.
    """
    import anthropic

    fake_message = MagicMock()
    fake_message.content = [MagicMock(type="text", text=json.dumps({"verdict": "clean", "matter": None, "evidence": None}))]
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_message

    monkeypatch.setattr(anthropic, "Anthropic", MagicMock(return_value=fake_client))
    return fake_client


# ---------------------------------------------------------------------------
# /check (B1 guard -- implemented on main)
# ---------------------------------------------------------------------------


def test_check_flags_delmarva_detail_in_chen_draft():
    draft = (
        "Trustee Eleanor Chen notes that refrigerated trailer 7 left idling at the "
        "Salisbury yard for nineteen hours, similar to what we discussed."
    )
    resp = client.post("/check", json={"matter_id": "chen", "draft": draft})
    assert resp.status_code == 200
    body = resp.json()
    assert body["verdict"] == "leak"
    assert any(h["matter"] == "delmarva" for h in body["hits"])


def test_check_passes_chens_own_facts():
    draft = (
        "Trustee Eleanor Chen must account to Victor Chen and Mei-Lin Chen Barros for the "
        "$2,340,000 trust corpus held at Harborview Bank."
    )
    resp = client.post("/check", json={"matter_id": "chen", "draft": draft})
    assert resp.status_code == 200
    body = resp.json()
    assert body["verdict"] == "clean"
    assert body["hits"] == []


# ---------------------------------------------------------------------------
# /scrub (B3 scrub -- implemented on main)
# ---------------------------------------------------------------------------


def test_scrub_leaves_zero_fact_strings():
    text = (FIXTURES / "matters/delmarva/session-demand-letter.md").read_text()
    resp = client.post("/scrub", json={"matter_id": "delmarva", "practice": "litigation", "text": text})
    assert resp.status_code == 200
    body = resp.json()

    all_fact_strings = [s for m in matters().values() for values in m["facts"].values() for s in values if s]
    assert not any(s in body["text"] for s in all_fact_strings)
    assert body["removed"] > 0


# ---------------------------------------------------------------------------
# /judge (B2 river) and /deidentify (C2 pipeline) -- anthropic SDK mocked
# ---------------------------------------------------------------------------


def test_judge_runs_mocked(mock_anthropic):
    body = {"current": "chen", "protected": ["delmarva"], "draft": "Please remit payment within 14 days."}
    resp = client.post("/judge", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["verdict"] in ("clean", "leak")


def test_deidentify_runs_mocked(mock_anthropic):
    body = {"text": "Please remit payment within 14 days.", "practice": "immigration"}
    resp = client.post("/deidentify", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert "text" in data
    assert "removed" in data
