"""River as the de-identifier: a LoRA-tuned Qwen that reads a firm's practice
policy and returns the exact spans to remove from a passage.

    spans(text, practice="immigration", model="tuned") -> [{text, kind, replacement}]

model="tuned" samples the checkpoint in .runtime/river-deid/state.json;
model="base" samples the untuned base model (for comparison). Every live success
is cached under .runtime/demo_cache/river_deid.json and replayed (with
"replayed": True on each span) when the live call fails. Spans whose text is not
an exact substring of the passage are dropped.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

RUNTIME = Path("/Users/dqi26/the-wall/.runtime")
STATE_PATH = RUNTIME / "river-deid" / "state.json"
CACHE_PATH = RUNTIME / "demo_cache" / "river_deid.json"
POLICY_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "policy.json"
BASE_MODEL = "Qwen/Qwen3.6-35B-A3B-FP8"

KINDS = {
    "name": "[PERSON]",
    "org": "[ORG]",
    "amount": "[AMOUNT]",
    "award": "[AWARD]",
    "year": "[YEAR]",
    "publication": "[PUBLICATION]",
    "id_number": "[ID_NUMBER]",
    "location": "[LOCATION]",
    "quasi_identifier": "[QUASI_IDENTIFIER]",
}


def system_prompt(practice: str = "immigration") -> str:
    policy = json.loads(POLICY_PATH.read_text())[practice]
    never = "\n".join(f"- {item}" for item in policy["never_compounds"])
    may = ", ".join(policy["may_compound"])
    kinds = "\n".join(f"- {k} -> {v}" for k, v in KINDS.items())
    return (
        f"You de-identify passages from a law firm's {practice} matters.\n"
        f"Firm policy: these never leave the matter:\n{never}\n"
        f"These may be reused across matters: {may}.\n\n"
        "List every span that must be removed, including paraphrased "
        "quasi-identifiers: descriptions specific enough to single out a person "
        "(a unique title, a 'youngest/first/only' claim, a named list or ranking). "
        "Do not remove generic legal argument, criteria language or exhibit "
        "structure.\n\n"
        f"Kinds and replacements:\n{kinds}\n\n"
        'Reply with JSON only: {"spans":[{"text":"<exact substring>","kind":"<kind>",'
        '"replacement":"<replacement>"}]}. Each text must be copied exactly from '
        'the passage. If nothing must be removed reply {"spans":[]}.'
    )


def valid_spans(text: str, raw: list) -> list[dict]:
    """Keep only well-formed spans whose text occurs exactly in the passage."""
    out, seen = [], set()
    for s in raw or []:
        if not isinstance(s, dict):
            continue
        t, kind = s.get("text"), s.get("kind")
        if not isinstance(t, str) or not t.strip() or t not in text or t in seen:
            continue
        if kind not in KINDS:
            kind = "quasi_identifier"
        seen.add(t)
        out.append({"text": t, "kind": kind, "replacement": KINDS[kind]})
    return out


def parse(text: str, completion: str) -> list[dict]:
    completion = re.sub(r"<think>.*?</think>", "", completion, flags=re.S)
    match = re.search(r"\{.*\}", completion, flags=re.S)
    if not match:
        return []
    try:
        return valid_spans(text, json.loads(match.group(0)).get("spans"))
    except (json.JSONDecodeError, AttributeError):
        return []


def checkpoint_path() -> str | None:
    if not STATE_PATH.exists():
        return None
    state = json.loads(STATE_PATH.read_text())
    return state.get("checkpoint_path") if state.get("status") == "done" else None


def sample_many(texts: list[str], practice: str, model: str) -> list[str]:
    """Raw completions for many passages in one River session (tuned or base)."""
    import river_client as river
    from river_client.renderers import get_renderer

    from river.env import load_dotenv

    load_dotenv()
    checkpoint = None
    if model == "tuned":
        checkpoint = checkpoint_path()
        if not checkpoint:
            raise RuntimeError("no finished river-deid checkpoint")
    renderer = get_renderer(BASE_MODEL)
    prompts = [
        renderer.build_sample_prompt(
            [{"role": "system", "content": system_prompt(practice)}, {"role": "user", "content": t}]
        ).prompt
        + "\n</think>\n\n"  # non-thinking mode, same tokens the SFT targets start with
        for t in texts
    ]
    client = river.Client(api_key=os.environ["RIVER_API_KEY"])
    try:
        with client.session(job="k3-river-deid-sample") as session:
            groups = session.sample(
                prompts=prompts,
                base_model=BASE_MODEL,
                checkpoint=checkpoint,
                max_tokens=1024,
                temperature=0.0,
                stop=renderer.get_stop_strings(),
            )
        return [g[0].text for g in groups]
    finally:
        client.close()


def _key(text: str, practice: str, model: str) -> str:
    return hashlib.sha256(f"{model}|{practice}|{text}".encode()).hexdigest()[:24]


def _cache() -> dict:
    try:
        return json.loads(CACHE_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def spans(text: str, practice: str = "immigration", model: str = "tuned") -> list[dict]:
    key = _key(text, practice, model)
    try:
        result = parse(text, sample_many([text], practice, model)[0])
    except Exception:
        cached = _cache().get(key)
        if cached is None:
            raise
        return [{**s, "replayed": True} for s in cached]
    cache = _cache()
    cache[key] = result
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache))
    return result
