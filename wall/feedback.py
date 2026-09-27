"""Attorney corrections -> River training examples (the self-improving loop).

An attorney reviewing a de-identified passage records a correction: an identifier
the model MISSED (should have been replaced) or one it got WRONG (replaced but
should have stayed). Each correction becomes one chat-format training row in the
same lane k3-river-deid trains on, so the next River retrain learns from it.

Routes (mounted by the coordinator): POST/GET /demo/api/feedback, POST /demo/api/retrain.
"""

import json
import os
import time
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

RUNTIME = Path(os.environ.get("WALL_RUNTIME", "/Users/dqi26/the-wall/.runtime"))
FEEDBACK = RUNTIME / "feedback.jsonl"

SYSTEM = (
    "You de-identify legal documents for a small law firm. Given the practice area and a "
    "passage, return JSON {\"spans\": [{\"text\": <exact identifier text>, \"replacement\": "
    "<typed placeholder like [PERSON]>}]} listing every identifier that must be replaced "
    "under that practice's policy, and nothing that may stay."
)


class Correction(BaseModel):
    matter_id: str
    practice: str
    passage: str
    kind: Literal["missed", "wrong"]
    span_text: str
    replacement: str | None = None  # placeholder the missed span should get, e.g. "[PERSON]"
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


def _target_spans(c: dict) -> list[dict]:
    spans = [
        {"text": s["text"], "replacement": s.get("replacement") or "[REDACTED]"}
        for s in (c.get("spans") or [])
        if s.get("text") and s["text"] != c["span_text"]
    ]
    if c["kind"] == "missed":
        spans.append({"text": c["span_text"], "replacement": c.get("replacement") or "[REDACTED]"})
    return spans


def to_training_example(c: dict) -> dict:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Practice: {c['practice']}\n\nPassage:\n{c['passage']}"},
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

