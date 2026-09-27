"""Owned by F2. The compounding beat for the web demo.

run(source, target):
  1. read the source matter's session log (its procedure, in its own words)
  2. scrub it with wall.scrub.scrub, using the source matter's own practice policy
  3. draft a letter for the target matter with the target's intake + the
     scrubbed procedure as know-how (Anthropic API)
  4. check the draft with wall.guard.check

Caches the last successful run so a live-API failure can replay it instead of
breaking the demo (docs/CONTRACT.md "Web demo" demo-safe replay rule).
"""

import json
import os
import re
from pathlib import Path

from wall.contract import CheckRequest, ScrubRequest
from wall.guard import check as guard_check
from wall.matters import MATTERS_DIR, matters
from wall.scrub import scrub as scrub_text

CACHE = Path(__file__).resolve().parent.parent / ".runtime" / "demo_cache" / "compound.json"
ENV_FILE = Path.home() / "the-wall" / ".env"

# Placeholders wall.scrub.scrub substitutes in place of a fact (see wall/scrub.py).
_PLACEHOLDER_RE = re.compile(
    r"the counterparty|Counterparty|\[amount\]|\[date\]|\[redacted detail\]|the exhibit|the relevant section"
)
_STEP_RE = re.compile(r"^(\d+)\.\s+(.+)$", re.MULTILINE)


def _load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def _mark_facts(text: str, facts: dict) -> str:
    """Wrap the source matter's own facts in <mark class="fact"> for the UI."""
    strings = sorted(
        {s for s in facts.get("names", []) + facts.get("orgs", []) + facts.get("amounts", []) + facts.get("distinctive", []) if s},
        key=len,
        reverse=True,
    )
    for s in strings:
        text = re.sub(re.escape(s), lambda m: f'<mark class="fact">{m.group()}</mark>', text)
    return text


def _mark_placeholders(text: str) -> str:
    """Wrap scrub's placeholder tokens in <mark class="replaced"> for the UI."""
    return _PLACEHOLDER_RE.sub(lambda m: f'<mark class="replaced">{m.group()}</mark>', text)


def _mark_structure(text: str) -> str:
    """Wrap leading numbered-step markers in <mark class="structure">: the shape
    carried over from the procedure, as opposed to the client facts filling it."""
    return _STEP_RE.sub(lambda m: f'<mark class="structure">{m.group(1)}.</mark> {m.group(2)}', text)


def _draft_letter(target: str, scrubbed_procedure: str) -> str:
    import anthropic

    env = _load_env()
    api_key = env.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not available")
    workspace_id = env.get("ANTHROPIC_WORKSPACE_ID") or os.environ.get("ANTHROPIC_WORKSPACE_ID")
    model = os.environ.get("WALL_LLM_MODEL", "claude-sonnet-5")

    client = anthropic.Anthropic(
        api_key=api_key,
        default_headers={"anthropic-workspace-id": workspace_id} if workspace_id else None,
    )

    intake = (MATTERS_DIR / target / "intake.md").read_text()

    prompt = (
        "You are a lawyer's drafting assistant. Below is a firm procedure note "
        "(scrubbed of any client's names, amounts and case-specific details) and "
        "the intake for the current client matter. The two matters are in "
        "different practice areas, so treat the procedure as a drafting PATTERN "
        "(the order of moves a good letter makes), not a legal theory: translate "
        "any litigation-specific vocabulary (breach, damages, forum) into terms "
        "that fit the current matter's own relationship and area of law. Never "
        "accuse anyone of wrongdoing the intake doesn't describe.\n\n"
        f"--- Firm procedure (scrubbed) ---\n{scrubbed_procedure}\n\n"
        f"--- Client intake ---\n{intake}\n\n"
        "Draft the letter this intake calls for, as a numbered list of steps "
        "that follows the procedure's underlying pattern: (1) open with the "
        "relevant basis and date, (2) present the key items in two buckets, "
        "settled/documented facts first, then anything disputed or projected, "
        "(3) reference the primary supporting document before making any ask, "
        "(4) close with a clear deadline and where the recipient should direct "
        "next steps. Use ONLY facts from the client intake above; never mention "
        "any name, amount or detail from the procedure note itself. Output only "
        "the letter text, formatted as a numbered list of exactly 4 steps."
    )

    resp = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in resp.content if block.type == "text").strip()


def run(source: str = "delmarva", target: str = "chen") -> dict:
    try:
        raw_procedure = (MATTERS_DIR / source / "session-demand-letter.md").read_text()

        source_matter = matters()[source]
        scrub_resp = scrub_text(ScrubRequest(matter_id=source, practice=source_matter["practice"], text=raw_procedure))

        draft = _draft_letter(target, scrub_resp.text)
        check_resp = guard_check(CheckRequest(matter_id=target, draft=draft))

        result = {
            "source": source,
            "target": target,
            "raw_procedure": raw_procedure,
            "raw_procedure_html": _mark_facts(raw_procedure, source_matter.get("facts", {})),
            "scrubbed_procedure": scrub_resp.text,
            "scrubbed_procedure_html": _mark_placeholders(scrub_resp.text),
            "removed": scrub_resp.removed,
            "draft": draft,
            "draft_html": _mark_structure(draft),
            "check": check_resp.model_dump(),
            "replayed": False,
        }
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(result, indent=2))
        return result
    except Exception:
        if CACHE.exists():
            cached = json.loads(CACHE.read_text())
            cached["replayed"] = True
            return cached
        raise
