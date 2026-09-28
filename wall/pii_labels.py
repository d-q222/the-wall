"""Name what kind of detail a hidden clue is ("accomplishment", "job title", ...) so a
placeholder says more than [QUASI_IDENTIFIER]. River's base model answers in one short
phrase from a fixed list; answers are cached, and a keyword fallback covers River being
slow or unavailable.

    labels(clues: list[str], practice="immigration") -> {clue: "accomplishment", ...}
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from wall import river_deid

CACHE_PATH = river_deid.RUNTIME / "demo_cache" / "pii_labels.json"
TIMEOUT_S = float(os.environ.get("WALL_PII_LABEL_TIMEOUT", "20"))
CHOICES = ["accomplishment", "job title", "publication", "press coverage",
           "place", "date", "relationship", "project", "detail"]

_FALLBACK = [
    (r"\b(prize|award|medal|honou?r|fellowship|won|wins|winning)\b", "accomplishment"),
    (r"\b(chair|founder|founded|ceo|director|head|lead|led|principal|professor|chief)\b", "job title"),
    (r"\b(published|paper|journal|book|article|patent)\b", "publication"),
    (r"\b(featured|profiled|interview|press|magazine|coverage)\b", "press coverage"),
    (r"\b(youngest|first|only|oldest|record)\b", "accomplishment"),
]


def _fallback(clue: str) -> str:
    low = clue.lower()
    return next((label for pattern, label in _FALLBACK if re.search(pattern, low)), "detail")


def _cache() -> dict:
    try:
        return json.loads(CACHE_PATH.read_text())
    except (OSError, ValueError):
        return {}


def _ask_river(clues: list[str]) -> list[str]:
    import river_client as river
    from river_client.renderers import get_renderer

    from river.env import load_dotenv

    load_dotenv()
    renderer = get_renderer(river_deid.BASE_MODEL)
    system = ("You name what kind of personal detail a phrase is, for a de-identified legal "
              f"document. Answer with exactly one of: {', '.join(CHOICES)}. Reply with only those words.")
    prompts = [renderer.build_sample_prompt([{"role": "system", "content": system},
                                             {"role": "user", "content": c}]).prompt + "\n</think>\n\n"
               for c in clues]
    client = river.Client(api_key=os.environ["RIVER_API_KEY"])
    try:
        with client.session(timeout=TIMEOUT_S, job="pii-labels") as session:
            groups = session.sample(prompts=prompts, base_model=river_deid.BASE_MODEL, max_tokens=8,
                                    temperature=0.0, stop=renderer.get_stop_strings(), timeout=TIMEOUT_S)
        return [g[0].text for g in groups]
    finally:
        client.close()


def labels(clues: list[str], practice: str = "immigration") -> dict[str, str]:
    cache, todo = _cache(), [c for c in dict.fromkeys(clues) if c not in _cache()]
    if todo:
        try:
            for clue, answer in zip(todo, _ask_river(todo)):
                word = answer.strip().lower().strip(".\"' ")
                cache[clue] = word if word in CHOICES else _fallback(clue)
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            CACHE_PATH.write_text(json.dumps(cache, indent=2))
        except Exception:
            for clue in todo:
                cache[clue] = _fallback(clue)
    return {c: cache.get(c) or _fallback(c) for c in clues}
