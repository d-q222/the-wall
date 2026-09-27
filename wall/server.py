"""HTTP surface for the contract. Routes delegate to modules owned by one branch each."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from wall import compound, deid, guard, judge, results, scrub, walldemo
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


# Web demo (C4 shell + F-lane pages), same origin as the API.
_demo = Path(__file__).resolve().parent.parent / "demo"
_demo.mkdir(exist_ok=True)
app.mount("/demo", StaticFiles(directory=_demo, html=True), name="demo")
app.mount("/scoreboard", StaticFiles(directory=_demo.parent / "scoreboard", html=True), name="scoreboard")
results.RESULTS.parent.mkdir(parents=True, exist_ok=True)
app.mount("/results", StaticFiles(directory=results.RESULTS.parent), name="results")
