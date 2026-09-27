"""Single writer helper for results/results.json so parallel eval runners don't clobber each other."""

import fcntl
import json
from pathlib import Path

from wall.contract import EvalResult

RESULTS = Path(__file__).resolve().parent.parent / "results" / "results.json"


def record(detector: str, eval_set: str, result: EvalResult) -> None:
    RESULTS.parent.mkdir(exist_ok=True)
    RESULTS.touch()
    with RESULTS.open("r+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        text = f.read()
        data = json.loads(text) if text.strip() else {}
        data.setdefault(detector, {})[eval_set] = result.model_dump()
        f.seek(0)
        f.truncate()
        json.dump(data, f, indent=2)


def load() -> dict:
    return json.loads(RESULTS.read_text()) if RESULTS.exists() and RESULTS.read_text().strip() else {}
