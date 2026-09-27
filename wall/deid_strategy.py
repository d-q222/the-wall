"""The measured de-identification strategy (lane m1).

evals/bakeoff/run.py scores every detector and union on k3's held-out paragraphs
and writes .runtime/deid_strategy.json. load() returns the chosen detector list
(["facts", "rules"] if the file is missing); detect() runs those detectors and
returns merged, non-overlapping spans [{start, end, text, kind}].
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from wall import matters, pii

STRATEGY_PATH = Path("/Users/dqi26/the-wall/.runtime/deid_strategy.json")
DEFAULT = ["facts", "rules"]


def load() -> list[str]:
    try:
        return json.loads(STRATEGY_PATH.read_text())["detectors"]
    except (OSError, json.JSONDecodeError, KeyError):
        return list(DEFAULT)


def _facts(text: str, practice: str, matter_id: str | None) -> list[dict]:
    """Known fact-sheet values of every matter found verbatim in the text."""
    found = {}
    for m in matters.matters().values():
        for kind, values in m.get("facts", {}).items():
            for v in values:
                if v and v in text:
                    found.setdefault(v, kind)
    return [{"text": v, "kind": k} for v, k in found.items()]


def _rules(text: str, practice: str, matter_id: str | None) -> list[dict]:
    return [{"text": text[s.start:s.end], "kind": s.kind} for s in pii.find(text)]


def claude_message(text: str, practice: str, model: str | None = None):
    """One Claude span-extraction call with k3's policy prompt and JSON schema."""
    import anthropic

    from river.env import load_dotenv
    from wall import river_deid

    load_dotenv()
    workspace_id = os.environ.get("ANTHROPIC_WORKSPACE_ID")
    client = anthropic.Anthropic(
        api_key=os.environ["ANTHROPIC_API_KEY"],
        default_headers={"anthropic-workspace-id": workspace_id} if workspace_id else None,
    )
    return client.messages.create(
        model=model or os.environ.get("WALL_LLM_MODEL", "claude-sonnet-5"),
        max_tokens=4096,
        system=river_deid.system_prompt(practice),
        messages=[{"role": "user", "content": text}],
    )


def reply_text(msg) -> str:
    """The text block of a Claude reply (skips any thinking blocks)."""
    return "".join(b.text for b in msg.content if b.type == "text")


def _claude(text: str, practice: str, matter_id: str | None) -> list[dict]:
    from wall import river_deid

    return river_deid.parse(text, reply_text(claude_message(text, practice)))


def _river(model: str):
    def run(text: str, practice: str, matter_id: str | None) -> list[dict]:
        from wall import river_deid

        return river_deid.spans(text, practice, model)
    return run


DETECTORS = {
    "facts": _facts,
    "rules": _rules,
    "claude": _claude,
    "river_tuned": _river("tuned"),
    "river_base": _river("base"),
}


def detect(text: str, practice: str = "immigration", matter_id: str | None = None,
           detectors: list[str] | None = None) -> list[dict]:
    """Run the chosen detectors; merge overlapping hits into one span (first kind wins).

    A detector that fails (no key, River down) is skipped so rules+facts always run.
    """
    hits = []
    for order, name in enumerate(detectors or load()):
        try:
            found = DETECTORS[name](text, practice, matter_id)
        except Exception:
            continue
        for s in found:
            start = text.find(s["text"])
            while start != -1:
                hits.append((start, start + len(s["text"]), order, s["kind"]))
                start = text.find(s["text"], start + 1)
    merged: list[dict] = []
    for start, end, _, kind in sorted(hits):
        if merged and start < merged[-1]["end"]:
            merged[-1]["end"] = max(merged[-1]["end"], end)
            continue
        merged.append({"start": start, "end": end, "kind": kind})
    return [{**m, "text": text[m["start"]:m["end"]]} for m in merged]
