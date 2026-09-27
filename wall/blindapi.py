"""Blind-set entry API (owned by h1-blind).

Daniel hand-writes 30 blind cases via demo/blind.html. append() validates the
row with evals/run_guard.py parse_flat_row and appends it to the shared data
pack; summary() returns running {leak, clean, n} counts. NEVER read or display
any other file in the data dir.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evals.run_guard import parse_flat_row  # noqa: E402

BLIND_PATH = Path("/Users/dqi26/the-wall/data/blind.jsonl")


def append(row: dict) -> dict:
    """Validate a flat blind row and append it to blind.jsonl."""
    if not isinstance(row, dict):
        return {"ok": False, "error": "row must be a JSON object"}
    parsed = parse_flat_row(row)
    if parsed is None:
        return {
            "ok": False,
            "error": (
                "row does not parse: need current/protected blocks shaped like "
                "'M<n>: Client <name> (<org>) v. <other party>, <role>. "
                "Matter type: <type>. Confidential: <text with $amount>.' "
                "plus draft and label LEAK/CLEAN"
            ),
        }
    if not parsed.protected:
        return {"ok": False, "error": "at least one protected matter block is required"}
    BLIND_PATH.parent.mkdir(parents=True, exist_ok=True)
    with BLIND_PATH.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    counts = summary()
    return {"ok": True, **counts}


def summary() -> dict:
    """Return {leak, clean, n} over parseable rows in blind.jsonl."""
    leak = clean = 0
    if BLIND_PATH.exists():
        for line in BLIND_PATH.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                parsed = parse_flat_row(json.loads(line))
            except (json.JSONDecodeError, TypeError, AttributeError):
                continue
            if parsed is None:
                continue
            if parsed.label == "LEAK":
                leak += 1
            else:
                clean += 1
    return {"leak": leak, "clean": clean, "n": leak + clean}
