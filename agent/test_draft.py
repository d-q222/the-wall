"""Offline draft tests — the LLM is mocked.

Acceptance (PRD FR-3): a draft for chen cites only chen facts. This asserts no
delmarva/reyes fact string from wall.matters leaks into an offline chen
draft's assembled context or (mocked) output.
"""

from agent import draft
from wall.matters import matters


def other_matter_facts(current: str) -> list[str]:
    facts = []
    for matter_id, m in matters().items():
        if matter_id == current:
            continue
        for values in m["facts"].values():
            facts.extend(values)
    return facts


def test_offline_chen_draft_has_no_other_matter_facts(monkeypatch):
    monkeypatch.setattr(draft, "draft_letter", lambda prompt, model=None: prompt)
    monkeypatch.setattr(draft, "check_draft", lambda matter_id, d: None)

    result, verdict = draft.run("chen", "Write a status letter to the client.", offline=True)

    assert verdict is None
    leaked = [f for f in other_matter_facts("chen") if f in result]
    assert leaked == []


def test_offline_recall_only_reads_own_matter_documents():
    context = draft.recall_offline("chen")
    leaked = [f for f in other_matter_facts("chen") if f in context]
    assert leaked == []
