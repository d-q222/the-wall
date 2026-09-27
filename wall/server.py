"""HTTP surface for the contract. Routes delegate to modules owned by one branch each."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from wall import deid, guard, judge, scrub
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


# O-1 demo UI (C4), same origin as the API.
_demo = Path(__file__).resolve().parent.parent / "demo"
_demo.mkdir(exist_ok=True)
app.mount("/demo", StaticFiles(directory=_demo, html=True), name="demo")
