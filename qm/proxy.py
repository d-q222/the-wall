"""FR-12: adapter QM can use as its `securityScreen` proxy, backed by wall's /judge.

QM's proxy contract (docs/deploy-directory.md, src/security/security-screener.ts):
  POST <endpoint>, header `x-api-key: <SECURITY_SCREEN_PROXY_TOKEN>`
  body:  {text: str, hook: "user_input" | "tool_response", metadata: {...}}
  reply: {score: 0..1, threshold: 0..1, primary_outcome?: str}  (score >= threshold -> strict)

wall's contract (wall/contract.py, read-only) is matter-shaped, not score-shaped:
  POST /judge  {current: str, protected: list[str], draft: str} -> {verdict: "clean"|"leak", ...}

This process is the adapter between the two: it runs standalone (not inside wall/, which
we don't edit), forwards `text` as `draft` to wall's /judge (WALL_JUDGE_URL, default
http://localhost:8788/judge -- the wall API's current port per the coordinator's port
map), and turns "leak"/"clean" into score/threshold. `current`/`protected` aren't in
QM's proxy payload, so they come from this call's `metadata` -- set
`metadata: {current_matter, protected_matters}` in QM's securityScreen config for the
room being screened (FR-11's rooms.py records each room's project id; which matter a
room speaks for is a mapping the integrator supplies here, not something this adapter
guesses).

Verified against the real judge (wall.judge, a live claude-sonnet-5 call): a
delmarva-fact draft scored leak (1.0 >= threshold) when protected_matters names it, an
unrelated draft scored clean.

Usage: uv run python qm/proxy.py            # serves on :8814 (a4-qm's assigned dev port)
Wire into QM (per-project, in deploy config): securityScreen.endpoint = http://localhost:8814/screen
"""

from __future__ import annotations

import os

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

WALL_JUDGE_URL = os.environ.get("WALL_JUDGE_URL", "http://localhost:8788/judge")
PROXY_TOKEN = os.environ.get("SECURITY_SCREEN_PROXY_TOKEN")  # optional in dev
THRESHOLD = 0.5

app = FastAPI(title="qm-screening-proxy (wall adapter)")


class ScreenRequest(BaseModel):
    text: str
    hook: str
    metadata: dict = {}


class ScreenResponse(BaseModel):
    score: float
    threshold: float
    primary_outcome: str | None = None


@app.post("/screen")
def screen(req: ScreenRequest, x_api_key: str | None = Header(default=None)) -> ScreenResponse:
    if PROXY_TOKEN and x_api_key != PROXY_TOKEN:
        raise HTTPException(status_code=401, detail="bad x-api-key")

    current = req.metadata.get("current_matter", "")
    protected = req.metadata.get("protected_matters", [])
    resp = httpx.post(
        WALL_JUDGE_URL,
        json={"current": current, "protected": protected, "draft": req.text},
        timeout=30,
    )
    resp.raise_for_status()
    verdict = resp.json()["verdict"]

    leak = verdict == "leak"
    return ScreenResponse(score=1.0 if leak else 0.0, threshold=THRESHOLD, primary_outcome="leak" if leak else None)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8814)  # a4-qm's assigned dev port
