"""Interface contract shared by every delegation (PRD: "Interface contract").

Frozen after base layer. No agent adds or changes an endpoint here; request a
change from the coordinator instead.
"""

from typing import Literal

from pydantic import BaseModel

Verdict = Literal["clean", "leak"]
Detector = Literal["regex", "carryover", "prompt_judge", "river_judge", "base_judge"]


# POST /check  (B1 guard; A2 agent calls it on every draft)
class CheckRequest(BaseModel):
    matter_id: str
    draft: str


class Hit(BaseModel):
    detector: Detector
    matter: str  # the OTHER matter whose fact leaked
    evidence: str  # the matched span or judge rationale


class CheckResponse(BaseModel):
    verdict: Verdict
    hits: list[Hit] = []


# POST /scrub  (B3 scrub)
class ScrubRequest(BaseModel):
    matter_id: str
    practice: str
    text: str


class ScrubResponse(BaseModel):
    text: str
    removed: int


# POST /judge  (B2 river; same JSON as the training labels)
class JudgeRequest(BaseModel):
    current: str
    protected: list[str]
    draft: str


class JudgeResponse(BaseModel):
    verdict: Verdict
    matter: str | None = None
    evidence: str | None = None


# POST /deidentify  (C2 pipeline; O-1 demo)
class DeidSpan(BaseModel):
    start: int  # offsets into the ORIGINAL text
    end: int
    kind: str  # e.g. name, org, amount, a_number, receipt, email, date, quasi_identifier
    replacement: str


class DeidentifyRequest(BaseModel):
    text: str
    practice: str = "immigration"
    matter_id: str | None = None  # known matter facts improve recall when given


class DeidentifyResponse(BaseModel):
    text: str  # de-identified text
    spans: list[DeidSpan] = []
    removed: int
    residual: JudgeResponse | None = None  # judge verdict on the de-identified text
    judge: str | None = None  # which judge produced `residual` (river_judge, prompt_judge)


# results/results.json, written by eval runners via wall.results.record():
# {detector: {eval_set: {"caught", "leaks", "false_alarms", "clean", "n"}}}
class EvalResult(BaseModel):
    caught: int  # leaks flagged
    leaks: int  # leak cases in the set
    false_alarms: int  # clean cases flagged
    clean: int  # clean cases in the set
    n: int  # total cases
