"""Owned by B1: run regex + carryover detectors over every eval file present (PRD FR-4, FR-5).

Eval files live at /Users/dqi26/the-wall/data/ (gitignored, never copied into git).
Missing files are skipped. Results are written via wall.results.record() so the
scoreboard can read them from results/results.json.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import NamedTuple

if __name__ == "__main__" and __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wall import results
from wall.contract import EvalResult
from wall.guard import carryover_hits, regex_fingerprint_hits

DATA_DIR = Path("/Users/dqi26/the-wall/data")

EVAL_FILES = {
    "judge_eval.jsonl": "standard",
    "judge_eval_hard.jsonl": "hard",
    "demo_leak_cases.jsonl": "demo",
    "blind.jsonl": "blind",
}

# "M213: Client Diego Ibarra (Willow Dental) v. Diego Ibarra, board treasurer.
#  Matter type: breach of contract. Confidential: client authorized settlement up to $610,000."
BLOCK_RE = re.compile(
    r"(?:(?P<mid>M\d+):\s*)?Client\s+(?P<name1>.+?)\s*\((?P<org>.+?)\)\s*v\.\s*"
    r"(?P<name2>.+?),\s*(?P<role>.+?)\.\s*Matter type:\s*(?P<mtype>.+?)\.\s*"
    r"Confidential:\s*(?P<conf>.+?\$[\d,]+(?:\.\d+)?)\.",
    re.DOTALL,
)
AMOUNT_RE = re.compile(r"\$[\d,]+(?:\.\d+)?")


class Block(NamedTuple):
    matter_id: str
    facts: dict
    text: str


class EvalRow(NamedTuple):
    current: Block
    protected: dict[str, Block]
    draft: str
    label: str  # "LEAK" | "CLEAN"


def parse_block(text: str, fallback_id: str) -> Block | None:
    text = text.strip()
    m = BLOCK_RE.search(text)
    if not m:
        return None
    amt = AMOUNT_RE.search(m.group("conf"))
    names = [m.group("name1").strip(), m.group("name2").strip()]
    facts = {
        "names": list(dict.fromkeys(n for n in names if n)),
        "orgs": [m.group("org").strip()],
        "amounts": [amt.group()] if amt else [],
    }
    matter_id = (m.group("mid") or fallback_id).strip()
    return Block(matter_id=matter_id, facts=facts, text=text)


def _protected_blocks(lines: list[str]) -> dict[str, Block]:
    protected: dict[str, Block] = {}
    for i, line in enumerate(lines):
        line = line.strip().lstrip("-").strip()
        if not line:
            continue
        block = parse_block(line, f"protected_{i}")
        if block:
            protected[block.matter_id] = block
    return protected


def parse_messages_row(row: dict) -> EvalRow | None:
    """Rows shaped like judge_train_v2.jsonl / judge_eval*.jsonl (a chat transcript + meta.label)."""
    try:
        user = row["messages"][1]["content"]
    except (KeyError, IndexError, TypeError):
        return None
    if "DRAFT:" not in user:
        return None
    head, _, draft = user.partition("DRAFT:")
    cur_part, _, prot_part = head.partition("PROTECTED (other matters):")
    current = parse_block(cur_part.replace("CURRENT MATTER", ""), "current")
    if current is None:
        return None
    protected = _protected_blocks(prot_part.strip().splitlines())
    label = str(row.get("meta", {}).get("label", "")).upper()
    if label not in ("LEAK", "CLEAN"):
        return None
    return EvalRow(current=current, protected=protected, draft=draft.strip(), label=label)


def parse_flat_row(row: dict) -> EvalRow | None:
    """Rows shaped like JudgeRequest + label: {current, protected: [...], draft, label}."""
    if not {"current", "protected", "draft"} <= row.keys():
        return None
    current = parse_block(row["current"], "current")
    if current is None:
        return None
    protected = _protected_blocks(list(row["protected"]))
    label = str(row.get("label", "")).upper()
    if label not in ("LEAK", "CLEAN"):
        return None
    return EvalRow(current=current, protected=protected, draft=str(row["draft"]).strip(), label=label)


def load_rows(path: Path) -> list[EvalRow]:
    rows = []
    skipped = 0
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            parsed = parse_messages_row(raw) or parse_flat_row(raw)
            if parsed:
                rows.append(parsed)
            else:
                skipped += 1
    if skipped:
        print(f"  ({skipped} row(s) in {path.name} did not match a known schema; skipped)")
    return rows


def evaluate(rows: list[EvalRow], detector: str) -> EvalResult:
    caught = leaks = false_alarms = clean = 0
    for row in rows:
        if row.label == "LEAK":
            leaks += 1
        else:
            clean += 1

        if detector == "regex":
            hits = regex_fingerprint_hits(row.draft, row.current.facts, {mid: b.facts for mid, b in row.protected.items()})
        elif detector == "carryover":
            hits = carryover_hits(
                row.draft,
                [row.current.text],
                {mid: [b.text] for mid, b in row.protected.items()},
            )
        else:
            raise ValueError(detector)

        if hits:
            if row.label == "LEAK":
                caught += 1
            else:
                false_alarms += 1

    return EvalResult(caught=caught, leaks=leaks, false_alarms=false_alarms, clean=clean, n=leaks + clean)


def main() -> None:
    for filename, eval_set in EVAL_FILES.items():
        path = DATA_DIR / filename
        if not path.exists():
            print(f"[{eval_set}] skipped: {filename} not found in {DATA_DIR}")
            continue

        rows = load_rows(path)
        if not rows:
            print(f"[{eval_set}] skipped: no parseable rows in {filename}")
            continue

        for detector in ("regex", "carryover"):
            result = evaluate(rows, detector)
            results.record(detector, eval_set, result)
            print(
                f"[{eval_set}] {detector}: caught {result.caught}/{result.leaks} leaks, "
                f"{result.false_alarms}/{result.clean} false alarms (n={result.n})"
            )


if __name__ == "__main__":
    main()
