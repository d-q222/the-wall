"""Attorney corrections -> River training examples (the self-improving loop).

An attorney reviewing a de-identified passage records a correction: an identifier
the model MISSED (should have been replaced) or one it got WRONG (replaced but
should have stayed). Each correction becomes one chat-format training row in the
same lane k3-river-deid trains on, so the next River retrain learns from it.

Routes (mounted by the coordinator): POST/GET /demo/api/feedback, POST /demo/api/retrain.
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

RUNTIME = Path(os.environ.get("WALL_RUNTIME", "/Users/dqi26/the-wall/.runtime"))
FEEDBACK = RUNTIME / "feedback.jsonl"

# Same row schema as k3-river-deid (wall/river_deid.py): system prompt from the practice
# policy, user = the passage, assistant = {"spans": [{text, kind, replacement}]}.
try:
    from wall.river_deid import KINDS, system_prompt
except ImportError:  # k3 not merged yet; mirror its kinds and a minimal prompt
    KINDS = {"name": "[PERSON]", "org": "[ORG]", "amount": "[AMOUNT]", "award": "[AWARD]",
             "year": "[YEAR]", "publication": "[PUBLICATION]", "id_number": "[ID_NUMBER]",
             "location": "[LOCATION]", "quasi_identifier": "[QUASI_IDENTIFIER]"}

    def system_prompt(practice: str = "immigration") -> str:
        kinds = "\n".join(f"- {k} -> {v}" for k, v in KINDS.items())
        return (
            f"You de-identify passages from a law firm's {practice} matters.\n"
            f"Kinds and replacements:\n{kinds}\n\n"
            'Reply with JSON only: {"spans":[{"text":"<exact substring>","kind":"<kind>",'
            '"replacement":"<replacement>"}]}. If nothing must be removed reply {"spans":[]}.'
        )

KIND_OF = {v: k for k, v in KINDS.items()}


class Correction(BaseModel):
    matter_id: str
    practice: str
    passage: str
    kind: Literal["missed", "wrong"]
    span_text: str
    span_kind: str | None = None  # k3 kind for a missed span, e.g. "name"
    replacement: str | None = None  # or its placeholder, e.g. "[PERSON]"
    note: str | None = None
    # The model's spans on this passage when the attorney reviewed it, if the UI has them;
    # lets the training target be the full corrected span list rather than one span.
    spans: list[dict] | None = None


def record(correction: Correction | dict) -> dict:
    c = correction if isinstance(correction, Correction) else Correction(**correction)
    if c.span_text not in c.passage:
        raise ValueError("span_text must appear in passage")
    row = {"ts": time.time(), **c.model_dump()}
    FEEDBACK.parent.mkdir(parents=True, exist_ok=True)
    with FEEDBACK.open("a") as f:
        f.write(json.dumps(row) + "\n")
    return row


def load() -> list[dict]:
    if not FEEDBACK.exists():
        return []
    return [json.loads(line) for line in FEEDBACK.read_text().splitlines() if line.strip()]


def _span(text: str, kind: str | None, replacement: str | None) -> dict:
    # Placeholders may be numbered ("[PERSON_2]"); map back to the base kind.
    base = re.sub(r"_\d+\]$", "]", replacement or "")
    kind = kind if kind in KINDS else KIND_OF.get(replacement or "", KIND_OF.get(base, "quasi_identifier"))
    return {"text": text, "kind": kind, "replacement": KINDS[kind]}


def _target_spans(c: dict) -> list[dict]:
    spans = [
        _span(s["text"], s.get("kind"), s.get("replacement"))
        for s in (c.get("spans") or [])
        if s.get("text") and s["text"] != c["span_text"]
    ]
    if c["kind"] == "missed":
        spans.append(_span(c["span_text"], c.get("span_kind"), c.get("replacement")))
    return spans


def to_training_example(c: dict) -> dict:
    return {
        "messages": [
            {"role": "system", "content": system_prompt(c["practice"])},
            {"role": "user", "content": c["passage"]},
            {"role": "assistant", "content": json.dumps({"spans": _target_spans(c)})},
        ],
        "source": "attorney_feedback",
        "kind": c["kind"],
        "matter_id": c["matter_id"],
    }


def to_training_examples(corrections: list[dict] | None = None) -> list[dict]:
    return [to_training_example(c) for c in (load() if corrections is None else corrections)]


def summary(corrections: list[dict] | None = None) -> dict:
    rows = load() if corrections is None else corrections
    by_kind = {"missed": 0, "wrong": 0}
    for r in rows:
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1
    return {"n": len(rows), "by_kind": by_kind}


router = APIRouter()


@router.post("/demo/api/feedback")
def post_feedback(correction: Correction) -> dict:
    try:
        row = record(correction)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"recorded": row, "summary": summary()}


@router.get("/demo/api/feedback")
def get_feedback() -> dict:
    from river import retrain  # imported lazily: pulls in river_client

    rows = load()
    return {
        "corrections": rows,
        "summary": summary(rows),
        "retrain": {"plan": retrain.plan(), "state": retrain.state()},
    }


class RetrainRequest(BaseModel):
    confirm: bool = False


@router.post("/demo/api/retrain")
def post_retrain(req: RetrainRequest) -> dict:
    from river import retrain  # imported lazily: pulls in river_client

    if not req.confirm:
        return {"launched": False, "plan": retrain.plan(), "state": retrain.state()}
    try:
        return {"launched": True, **retrain.launch()}
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc

