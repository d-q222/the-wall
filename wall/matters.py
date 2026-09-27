"""Synthetic matter fixtures. No real client data anywhere."""

import json
from functools import cache
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
MATTERS_DIR = FIXTURES / "matters"


@cache
def matters() -> dict[str, dict]:
    """matter_id -> matter.json contents (id, client, practice, facts)."""
    return {
        p.name: json.loads((p / "matter.json").read_text())
        for p in sorted(MATTERS_DIR.iterdir())
        if (p / "matter.json").exists()
    }


def documents(matter_id: str) -> dict[str, str]:
    """filename -> text for every note in a matter folder (the matter's corpus)."""
    return {p.name: p.read_text() for p in sorted((MATTERS_DIR / matter_id).glob("*.md"))}


@cache
def policy() -> dict:
    return json.loads((FIXTURES / "policy.json").read_text())
