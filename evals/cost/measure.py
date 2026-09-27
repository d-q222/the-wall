"""E2 cost: measured cost and latency for the prompt judge.

Builds 20 synthetic JudgeRequest-shaped cases ({current, protected, draft})
from fixtures/matters/ (synthetic only; never opens the real data pack),
calls the prompt judge via the anthropic SDK, and reports cost per 1,000
judgments plus p50/p95 latency from measured token usage.

River judge: not measured. As of this run `b2-river` has landed neither a
deployment nor a sampling/inference path on main (`wall/judge.py` is still
the stub, `river/` holds only a .gitkeep) - there is nothing runnable to
time or price. River's own per-token or per-deployment price is likewise
unknown; ask River.

Run: uv run python evals/cost/measure.py
"""

from __future__ import annotations

import json
import os
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import anthropic

if __name__ == "__main__" and __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from wall.matters import matters

ENV_PATH = Path("/Users/dqi26/the-wall/.env")
OUT_PATH = Path(__file__).resolve().parent / "results.json"

# Anthropic first-party API rates, read via the claude-api skill on 2026-09-27.
PRICE_PER_MTOK = {"claude-sonnet-5": {"input": 2.00, "output": 10.00}}

JUDGE_SYSTEM = (
    "You are a cross-client confidentiality judge for a small law firm's AI "
    "assistant. You are given the current matter's own facts (always allowed "
    "to appear in its own draft), a list of protected fact summaries from "
    "OTHER matters (must never appear), and a draft. Decide clean or leak. "
    "If leak, name which protected matter's facts appeared and quote the "
    "evidence span. Respond with JSON only, no other text: "
    '{"verdict": "clean" or "leak", "matter": string or null, "evidence": string or null}.'
)


def load_env() -> None:
    """Load ANTHROPIC_API_KEY / ANTHROPIC_WORKSPACE_ID from the data pack's .env."""
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def _fact_summary(matter: dict) -> str:
    f = matter["facts"]
    return f"{matter['client']}: {', '.join(f['names'])}; {', '.join(f['amounts'])}; {f['distinctive'][0]}"


def build_cases() -> list[dict]:
    """20 synthetic JudgeRequest-shaped cases: clean and leak drafts per matter."""
    m = matters()
    ids = sorted(m)
    cases: list[dict] = []
    for current in ids:
        others = [o for o in ids if o != current]
        protected = [_fact_summary(m[o]) for o in others]
        own = m[current]["facts"]
        client_name = m[current]["client"]

        cases.append({
            "current": current,
            "protected": protected,
            "draft": f"Draft letter for {client_name} covering {own['names'][0]} and {own['amounts'][0]}.",
        })
        cases.append({
            "current": current,
            "protected": protected,
            "draft": f"Following up with {client_name} regarding {own['distinctive'][0]}; no other clients mentioned.",
        })
        for other in others:
            o = m[other]["facts"]
            cases.append({
                "current": current,
                "protected": protected,
                "draft": (
                    f"Draft for {client_name} mentions {o['names'][0]} and the amount "
                    f"{o['amounts'][0]} from an unrelated matter."
                ),
            })
            cases.append({
                "current": current,
                "protected": protected,
                "draft": f"Draft for {client_name} also describes: {o['distinctive'][0]}.",
            })
            cases.append({
                "current": current,
                "protected": protected,
                "draft": f"Note for {client_name}'s file references {o['orgs'][0]} in passing.",
            })
    return cases[:20]


def judge_prompt(case: dict) -> str:
    protected = "\n".join(f"- {p}" for p in case["protected"])
    return (
        f"Current matter: {case['current']}\n"
        f"Protected facts from other matters (never allowed in the draft):\n{protected}\n\n"
        f"Draft to check:\n{case['draft']}"
    )


@dataclass
class CallResult:
    input_tokens: int
    output_tokens: int
    latency_s: float


def call_judge(client: anthropic.Anthropic, model: str, case: dict) -> CallResult:
    start = time.monotonic()
    response = client.messages.create(
        model=model,
        max_tokens=300,
        system=JUDGE_SYSTEM,
        messages=[{"role": "user", "content": judge_prompt(case)}],
        extra_headers={"anthropic-workspace-id": os.environ["ANTHROPIC_WORKSPACE_ID"]},
    )
    latency = time.monotonic() - start
    return CallResult(response.usage.input_tokens, response.usage.output_tokens, latency)


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(ordered) - 1)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def main() -> None:
    load_env()
    model = os.environ.get("WALL_LLM_MODEL", "claude-sonnet-5")
    if model not in PRICE_PER_MTOK:
        raise SystemExit(f"no measured pricing for model {model!r}; add it to PRICE_PER_MTOK first")
    price = PRICE_PER_MTOK[model]

    if "ANTHROPIC_API_KEY" not in os.environ:
        raise SystemExit("ANTHROPIC_API_KEY not set; cannot run a live measurement")

    cases = build_cases()
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    calls = [call_judge(client, model, case) for case in cases]

    input_toks = [c.input_tokens for c in calls]
    output_toks = [c.output_tokens for c in calls]
    latencies = [c.latency_s for c in calls]
    costs_usd = [
        c.input_tokens / 1_000_000 * price["input"] + c.output_tokens / 1_000_000 * price["output"]
        for c in calls
    ]

    summary = {
        "detector": "prompt_judge",
        "model": model,
        "n": len(calls),
        "input_tokens": {
            "mean": round(statistics.mean(input_toks), 1),
            "p50": percentile(input_toks, 0.5),
            "p95": percentile(input_toks, 0.95),
        },
        "output_tokens": {
            "mean": round(statistics.mean(output_toks), 1),
            "p50": percentile(output_toks, 0.5),
            "p95": percentile(output_toks, 0.95),
        },
        "latency_s": {
            "mean": round(statistics.mean(latencies), 3),
            "p50": round(percentile(latencies, 0.5), 3),
            "p95": round(percentile(latencies, 0.95), 3),
        },
        "cost_per_1000_judgments_usd": round(statistics.mean(costs_usd) * 1000, 4),
        "price_per_mtok_usd": price,
        "river_judge": "not measured: no deployment or sampling path on main as of this run",
    }
    OUT_PATH.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
