"""B2: prompt-based LLM judge (PRD FR-7), the fallback third detector.

Calls the anthropic SDK directly (no framework) and returns the same JSON
shape as wall.contract.JudgeResponse. Malformed output is retried once; a
second failure raises JudgeError so callers never mistake an error for a
"clean" verdict.
"""

import json
import os

import anthropic

from river.env import load_dotenv
from wall.contract import JudgeRequest, JudgeResponse

load_dotenv()

DEFAULT_MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = (
    "You are a confidentiality wall for a law firm. You receive PROTECTED facts "
    "from other client matters and a DRAFT for the current matter. Each protected "
    "matter is given as `<matter_id>: <facts>`.\n\n"
    'Reply with JSON only, no other text: {"verdict": "leak" or "clean", '
    '"matter": the leaking matter\'s id or null, "evidence": the exact quoted '
    "leaking span from the draft, or null}.\n\n"
    "Facts about the CURRENT matter are never leaks. A draft that describes "
    "another matter's facts without naming that matter directly is still a leak."
)


class JudgeError(RuntimeError):
    """LLM output was not valid JSON matching the schema, twice in a row."""


def _client() -> anthropic.Anthropic:
    workspace_id = os.environ.get("ANTHROPIC_WORKSPACE_ID")
    return anthropic.Anthropic(
        api_key=os.environ["ANTHROPIC_API_KEY"],
        default_headers={"anthropic-workspace-id": workspace_id} if workspace_id else None,
    )


def _prompt(req: JudgeRequest) -> str:
    protected = "\n".join(f"- {p}" for p in req.protected)
    return (
        f"CURRENT MATTER: {req.current}\n\n"
        f"PROTECTED (other matters):\n{protected}\n\n"
        f"DRAFT:\n{req.draft}"
    )


def _parse(text: str) -> JudgeResponse:
    data = json.loads(text)
    verdict = str(data["verdict"]).strip().lower()
    if verdict not in ("clean", "leak"):
        raise ValueError(f"unexpected verdict {verdict!r}")
    return JudgeResponse(verdict=verdict, matter=data.get("matter"), evidence=data.get("evidence"))


def judge(req: JudgeRequest, *, client: anthropic.Anthropic | None = None) -> JudgeResponse:
    client = client or _client()
    model = os.environ.get("WALL_LLM_MODEL", DEFAULT_MODEL)
    messages: list[dict] = [{"role": "user", "content": _prompt(req)}]

    last_error: Exception | None = None
    for _attempt in range(2):
        response = client.messages.create(
            model=model,
            max_tokens=256,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        try:
            return _parse(text)
        except (json.JSONDecodeError, ValueError, KeyError) as exc:
            last_error = exc
            messages = messages + [
                {"role": "assistant", "content": text},
                {
                    "role": "user",
                    "content": "That was not valid JSON matching the schema. Reply with JSON only.",
                },
            ]
    raise JudgeError(f"malformed judge output after retry: {last_error}")
