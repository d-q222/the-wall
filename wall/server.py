"""HTTP surface for the contract. Routes delegate to modules owned by one branch each."""

from fastapi import FastAPI

from wall import guard, judge, scrub
from wall.contract import (
    CheckRequest,
    CheckResponse,
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
