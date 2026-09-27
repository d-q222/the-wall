"""Matter agent: recall through the matter's own scoped GBrain client, draft a
letter with the in-product LLM, then check the draft against the output guard.

Usage:
    uv run python -m agent.draft --matter chen --task "<instruction>"
    uv run python -m agent.draft --matter chen --task "<instruction>" --offline
    uv run python -m agent.draft --matter chen --task "<instruction>" --procedure <scrubbed.md>
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request

from agent.env import load_env
from agent.gbrain_client import GBrainClient, content_text

API_URL = os.environ.get("WALL_API_URL", "http://localhost:8788")
CHECK_URL = f"{API_URL}/check"
SCRUB_URL = f"{API_URL}/scrub"
DEFAULT_MODEL = "claude-sonnet-5"


def recall_online(matter_id: str, task: str) -> str:
    """Recall the matter's own facts through its scoped GBrain client. Never a
    local trusted caller or __all__ — those would see every matter."""
    client = GBrainClient(matter_id)
    keywords = " ".join(w for w in task.split() if len(w) > 2) or task
    search_hits = content_text(client.call("search", {"query": keywords}))
    intake = content_text(client.call("get_page", {"slug": "intake"}))
    return f"# Search results for '{keywords}'\n{search_hits}\n\n# Intake\n{intake}"


def recall_offline(matter_id: str) -> str:
    """Read the matter's own fixture documents directly. Tests only — never
    used for a live draft."""
    from wall.matters import documents

    docs = documents(matter_id)
    return "\n\n".join(f"# {name}\n{text}" for name, text in docs.items())


def build_prompt(matter_id: str, task: str, context: str, procedure: str | None) -> str:
    parts = [
        f"You are a lawyer's drafting assistant for matter '{matter_id}'.",
        f"Task: {task}",
        "Use ONLY the facts below. Never mention any client, name, org, or "
        "amount from any other matter.",
        f"## Matter facts\n{context}",
    ]
    if procedure:
        parts.append(f"## Firm know-how (scrubbed procedure, no client facts)\n{procedure}")
    return "\n\n".join(parts)


def draft_letter(prompt: str, model: str | None = None) -> str:
    import anthropic

    load_env()
    headers = None
    if os.environ.get("ANTHROPIC_WORKSPACE_ID"):
        headers = {"anthropic-workspace-id": os.environ["ANTHROPIC_WORKSPACE_ID"]}
    client = anthropic.Anthropic(default_headers=headers)
    resp = client.messages.create(
        model=model or os.environ.get("WALL_LLM_MODEL", DEFAULT_MODEL),
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    text_blocks = [block.text for block in resp.content if block.type == "text"]
    if not text_blocks:
        raise RuntimeError(f"no text in response (stop_reason={resp.stop_reason})")
    return "".join(text_blocks)


def check_draft(matter_id: str, draft: str) -> dict | None:
    """POST the draft to the output guard. Returns None ("guard unavailable")
    on connection refused, HTTP 500, or any other failure — never rewrites the
    draft to try to pass."""
    body = json.dumps({"matter_id": matter_id, "draft": draft}).encode()
    req = urllib.request.Request(
        CHECK_URL, body, {"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError):
        return None


def run(
    matter_id: str, task: str, offline: bool = False, procedure_path: str | None = None
) -> tuple[str, dict | None]:
    context = recall_offline(matter_id) if offline else recall_online(matter_id, task)
    procedure = open(procedure_path).read() if procedure_path else None
    prompt = build_prompt(matter_id, task, context, procedure)
    draft = draft_letter(prompt)
    verdict = check_draft(matter_id, draft)
    return draft, verdict


def main() -> None:
    parser = argparse.ArgumentParser(description="Matter agent: scoped recall, draft, guard check")
    parser.add_argument("--matter", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument(
        "--offline", action="store_true", help="Read fixtures directly — tests only, no live recall"
    )
    parser.add_argument("--procedure", help="Path to a scrubbed firm procedure to include as know-how")
    args = parser.parse_args()

    if args.offline:
        print("[OFFLINE MODE — reading wall.matters fixtures directly, not live GBrain recall]")

    draft, verdict = run(args.matter, args.task, args.offline, args.procedure)

    print("\n=== DRAFT ===\n")
    print(draft)
    print("\n=== GUARD ===")
    if verdict is None:
        print("guard unavailable")
    else:
        print(json.dumps(verdict, indent=2))


if __name__ == "__main__":
    main()
