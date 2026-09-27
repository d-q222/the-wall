"""HTTP surface for the contract. Routes delegate to modules owned by one branch each."""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from wall import audit, blindapi, compound, deid, guard, judge, policyapi, results, scrub, walldemo
from wall.matters import documents, matters
from wall.contract import (
    CheckRequest,
    CheckResponse,
    DeidentifyRequest,
    DeidentifyResponse,
    JudgeRequest,
    JudgeResponse,
    ScrubRequest,
    ScrubResponse,
)

app = FastAPI(title="Ethical Wall Brain")


@app.post("/check")
def check(req: CheckRequest) -> CheckResponse:
    return guard.check(req)


@app.post("/scrub")
def scrub_(req: ScrubRequest) -> ScrubResponse:
    return scrub.scrub(req)


@app.post("/judge")
def judge_(req: JudgeRequest) -> JudgeResponse:
    return judge.judge(req)


@app.post("/deidentify")
def deidentify(req: DeidentifyRequest) -> DeidentifyResponse:
    return deid.deidentify(req)


@app.post("/demo/api/wall")
def wall_attack(matter: str = "chen", target: str = "delmarva") -> dict:
    return walldemo.attack(matter, target)


@app.post("/demo/api/compound")
def compound_(source: str = "delmarva", target: str = "chen") -> dict:
    return compound.run(source, target)


@app.get("/demo/api/matters")
def matters_() -> list[dict]:
    """Every fixture matter with its documents, for the matters and datasets pages."""
    return [{**m, "documents": documents(mid)} for mid, m in matters().items()]


@app.get("/demo/api/policy")
def policy_get() -> dict:
    return policyapi.get()


@app.post("/demo/api/policy")
def policy_save(policy: dict) -> dict:
    return policyapi.save(policy)


@app.get("/demo/api/audit")
def audit_recent(limit: int = 100) -> list[dict]:
    return audit.recent(limit)


@app.post("/demo/api/blind")
def blind_append(row: dict) -> dict:
    return blindapi.append(row)


@app.get("/demo/api/blind")
def blind_summary() -> dict:
    return blindapi.summary()


# Web demo (C4 shell + F-lane pages), same origin as the API.
# WALL_DEMO_DIR lets a live preview serve in-progress pages without touching the repo.
_demo = Path(os.environ.get("WALL_DEMO_DIR", Path(__file__).resolve().parent.parent / "demo"))
_demo.mkdir(exist_ok=True)
app.mount("/demo", StaticFiles(directory=_demo, html=True), name="demo")
app.mount("/scoreboard", StaticFiles(directory=Path(__file__).resolve().parent.parent / "scoreboard", html=True), name="scoreboard")
results.RESULTS.parent.mkdir(parents=True, exist_ok=True)
app.mount("/results", StaticFiles(directory=results.RESULTS.parent), name="results")
