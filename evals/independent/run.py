"""Score every detector on the independent test sets (lanes i1-i5).

    uv run python -m evals.independent.run                 # all detectors, all sets found
    uv run python -m evals.independent.run --detectors regex,carryover,prompt

Each lane writes evals/independent/<name>.jsonl on its own branch (flat rows:
{current, protected[], draft, label, ...}). This reads them from origin/<branch>
(falling back to the lane's worktree), scores regex + carryover (wall.guard via
evals/run_guard.py) and the prompt / base / River judges (evals/run_judges.py),
and records each as indep_<name> plus a pooled "independent" set.

Model verdicts are cached under .runtime/eval_cache/indep_<judge>_<name>_<sha>.jsonl
(keyed by file content), so reruns only sample new rows. Per-row verdicts are
written to .runtime/indep/verdicts.json for the README's per-trick miss counts.
"""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import river_client as river

from evals import run_guard, run_judges
from wall.contract import EvalResult
from wall.results import record

LANES = ["i1-mixups", "i2-formats", "i3-paraphrase", "i4-adversarial", "i5-immigration"]
WORKTREES = Path("/Users/dqi26/the-wall-wt")
RIVER_STATES = [WORKTREES / "h2-river-live/.runtime/river/state.json", WORKTREES / "b2-river/.runtime/river/state.json"]
OUT = Path(".runtime/indep/verdicts.json")
DETECTORS = ["regex", "carryover", "prompt", "base", "river"]
TRICK_KEYS = ("id", "trick", "category")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout


def find_sets() -> dict[str, tuple[str, str]]:
    """name -> (source label, jsonl text) for every independent set that has landed."""
    found: dict[str, tuple[str, str]] = {}
    for lane in LANES:
        names = [p for p in _git("ls-tree", "--name-only", f"origin/{lane}", "evals/independent/").split() if p.endswith(".jsonl")]
        for p in names:
            found[Path(p).stem] = (f"origin/{lane}", _git("show", f"origin/{lane}:{p}"))
        if not names:
            for p in sorted((WORKTREES / lane / "evals/independent").glob("*.jsonl")):
                found[p.stem] = (f"worktree {lane}", p.read_text())
    return found


def trick_of(raw: dict) -> str:
    for k in TRICK_KEYS:
        if raw.get(k):
            return str(raw[k])
    return "?"


def river_checkpoint() -> river.Checkpoint:
    for path in RIVER_STATES:
        if path.exists():
            state = json.loads(path.read_text())
            if "checkpoint_path" in state:
                print(f"River checkpoint from {path}: {state['checkpoint_path']} step {state['checkpoint_step']}")
                return river.Checkpoint(
                    path=state["checkpoint_path"], step=state["checkpoint_step"], checkpoint_type=state["checkpoint_type"]
                )
    raise SystemExit("no River checkpoint found in " + ", ".join(map(str, RIVER_STATES)))


def score(labels: list[str], flags: list[bool | None]) -> tuple[EvalResult, int]:
    leaks = sum(lab == "leak" for lab in labels)
    caught = sum(lab == "leak" and f is True for lab, f in zip(labels, flags))
    fa = sum(lab == "clean" and f is True for lab, f in zip(labels, flags))
    errors = sum(f is None for f in flags)
    return EvalResult(caught=caught, leaks=leaks, false_alarms=fa, clean=len(labels) - leaks, n=len(labels)), errors


def run_detector(det: str, raws: list[dict], cache_stem: str) -> list[bool | None]:
    """True = flagged as leak, False = passed as clean, None = unparseable/error."""
    if det in ("regex", "carryover"):
        out = []
        for raw in raws:
            row = run_guard.parse_flat_row(raw)
            if row is None:  # block text doesn't match the generator's one-line matter format
                out.append(None)
                continue
            r = run_guard.evaluate([row], det)
            out.append(bool(r.caught or r.false_alarms))
        return out
    cases = [run_judges._flat_row_to_case(raw) for raw in raws]
    cache = run_judges.CACHE_DIR / f"indep_{det}_{cache_stem}.jsonl"
    run_judges.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if cache.exists():  # drop cached errors so they're retried
        kept = [line for line in cache.read_text().splitlines() if json.loads(line)["verdict"] is not None]
        cache.write_text("".join(line + "\n" for line in kept))
    if det == "prompt":
        verdicts = run_judges.run_prompt(cases, cache)
    else:
        ckpt = river_checkpoint() if det == "river" else None
        verdicts = run_judges.run_sampled(cases, cache, checkpoint=ckpt, max_tokens=400)
    return [None if v is None else v == "leak" for v in verdicts]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--detectors", default=",".join(DETECTORS))
    args = parser.parse_args()
    detectors = args.detectors.split(",")

    subprocess.run(["git", "fetch", "-q", "origin"], check=False)
    sets = find_sets()
    if not sets:
        raise SystemExit("no independent sets have landed yet")

    report = json.loads(OUT.read_text()) if OUT.exists() else {}
    pooled: dict[str, tuple[list[str], list]] = {d: ([], []) for d in detectors}
    for name, (source, text) in sorted(sets.items()):
        raws = [json.loads(line) for line in text.splitlines() if line.strip()]
        raws = [r for r in raws if str(r.get("label", "")).lower() in ("leak", "clean")]
        labels = [str(r["label"]).lower() for r in raws]
        stem = f"{name}_{hashlib.sha256(text.encode()).hexdigest()[:10]}"
        print(f"[{name}] {len(raws)} rows from {source} ({labels.count('leak')} leak / {labels.count('clean')} clean)")
        entry = report.setdefault(name, {})
        entry.update(source=source, n=len(raws), rows=[{"label": lab, "trick": trick_of(r)} for lab, r in zip(labels, raws)])
        for det in detectors:
            flags = run_detector(det, raws, stem)
            result, errors = score(labels, flags)
            detector = run_judges.DETECTOR_NAME.get(det, det)
            record(detector, f"indep_{name}", result)
            entry.setdefault("flags", {})[detector] = flags
            pooled[det][0].extend(labels)
            pooled[det][1].extend(flags)
            missed = [trick_of(r) for r, lab, f in zip(raws, labels, flags) if lab == "leak" and f is not True]
            alarms = [trick_of(r) for r, lab, f in zip(raws, labels, flags) if lab == "clean" and f is True]
            print(
                f"  {detector:14s} caught {result.caught}/{result.leaks}  false alarms {result.false_alarms}/{result.clean}"
                f"  errors {errors}  missed {missed}  false-alarmed {alarms}"
            )

    for det in detectors:
        labels, flags = pooled[det]
        result, errors = score(labels, flags)
        detector = run_judges.DETECTOR_NAME.get(det, det)
        record(detector, "independent", result)
        print(f"[pooled] {detector:14s} caught {result.caught}/{result.leaks}  false alarms {result.false_alarms}/{result.clean}  errors {errors}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
