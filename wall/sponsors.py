"""Owned by S2. "Built on" screen API: one live proof per hackathon host.

Demo-safe rule (same as walldemo): each proof caches its last live success
under .runtime/demo_cache/sponsors.json and replays it, flagged
"replayed": true with its original timestamp, if the live call fails.
GBrain's proof is the existing POST /demo/api/wall; this router adds the rest.
"""
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter

from wall import judge as judge_mod
from wall.contract import JudgeRequest

router = APIRouter(prefix="/demo/api/stack")

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".runtime" / "demo_cache" / "sponsors.json"
RESULTS = Path("/Users/dqi26/the-wall/results/results.json")
RIVER_JUDGE_STATE = Path("/Users/dqi26/the-wall-wt/b2-river/.runtime/river/state.json")
RIVER_DEID_STATE = Path("/Users/dqi26/the-wall/.runtime/river-deid/state.json")
CLIENTS = Path("/Users/dqi26/.superset/projects/The-Wall/.runtime/clients")
QM_STATUS = Path("/Users/dqi26/the-wall-wt/_status/a4-qm.md")

# Synthetic sample: the draft for one matter repeats another matter's figure.
SAMPLE = JudgeRequest(
    current="Matter CHEN: H-1B petition for a software engineer, Wei Chen.",
    protected=["Matter DELMARVA: Delmarva Farms LLC wage dispute; confidential settlement floor is $42,000."],
    draft=(
        "Dear Officer, we write in support of Mr. Chen's H-1B petition. "
        "As with the poultry employer we represent, where the floor was $42,000, "
        "the offered wage exceeds the prevailing level."
    ),
)


def _read(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _cached(name: str, live) -> dict:
    """Run live(); on success cache it, on failure replay the cached copy."""
    cache = _read(CACHE)
    try:
        result = {**live(), "at": _now(), "replayed": False}
    except Exception as exc:  # noqa: BLE001 - any live failure falls back to replay
        if name in cache:
            return {**cache[name], "replayed": True, "error": type(exc).__name__}
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "replayed": False, "at": _now()}
    cache[name] = result
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache))
    return result


def _state(path: Path) -> dict:
    s = _read(path)
    keys = ("base_model", "status", "n_examples", "checkpoint_step", "n_steps_planned", "checkpoint_path")
    return {k: s.get(k) for k in keys} if s else {}


def _score(results: dict, detector: str, eval_set: str) -> dict | None:
    row = results.get(detector, {}).get(eval_set)
    if not isinstance(row, dict):
        return None
    return {k: row.get(k) for k in ("caught", "leaks", "false_alarms", "clean", "n")}


@router.get("")
def facts() -> dict:
    """Static facts per host, read at request time so numbers never go stale."""
    results = _read(RESULTS)
    scores = {
        det: {s: _score(results, det, s) for s in ("hard", "independent", "blind")}
        for det in ("regex", "base_judge", "prompt_judge", "river_judge")
    }
    o1 = sorted(p.stem for p in CLIENTS.glob("o1-*.json")) if CLIENTS.exists() else []
    matters = sorted(p.stem for p in CLIENTS.glob("*.json")) if CLIENTS.exists() else []
    return {
        "gbrain": {"matters": matters, "o1": o1},
        "river": {"judge": _state(RIVER_JUDGE_STATE), "deid": _state(RIVER_DEID_STATE), "scores": scores},
        "qm": _qm_record(),
    }


@router.post("/judge")
def judge() -> dict:
    """Run the app's live /judge on a synthetic sample draft and say which judge answered."""
    import os

    def live() -> dict:
        res = judge_mod.judge(SAMPLE)
        model = os.environ.get("WALL_LLM_MODEL", judge_mod.DEFAULT_MODEL)
        return {"ok": True, "verdict": res.verdict, "evidence": res.evidence, "answered_by": f"Claude prompt judge ({model})"}

    return {**_cached("judge", live), "draft": SAMPLE.draft}


@router.post("/memorable")
def memorable() -> dict:
    """Run memorable/ingest.sh (scrubbed procedure in, recall out) and report the mode it used."""

    def live() -> dict:
        proc = subprocess.run(
            ["bash", "memorable/ingest.sh"], cwd=ROOT, capture_output=True, text=True, timeout=60
        )
        out = proc.stdout
        if proc.returncode != 0:
            raise RuntimeError(f"ingest.sh exit {proc.returncode}")
        mode = re.search(r"MODE=(\w+)", out)
        recall = out.split("recall check", 1)[-1].strip() if "recall check" in out else ""
        return {"ok": True, "mode": mode.group(1) if mode else "unknown", "recall": recall[:1200]}

    return _cached("memorable", live)


def _qm_record() -> dict:
    """QM's recorded live run (A4): last timestamped PASS line from its status file."""
    try:
        lines = QM_STATUS.read_text().splitlines()
    except OSError:
        return {}
    stamped = [ln for ln in lines if re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", ln)]
    proof = next((ln for ln in reversed(stamped) if "FR-11" in ln and ("verified" in ln or "done" in ln)), None)
    if not proof:
        return {}
    return {"at": proof[:19], "line": proof[20:].split(": ", 1)[-1][:400], "pass": "acceptance: PASS" in QM_STATUS.read_text()}
