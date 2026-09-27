"""Owned by C5: score regex, carryover, and the prompt judge on the synthetic O-1
leak set (evals/o1/o1_cases.jsonl) as eval set "o1_demo" (CONTRACT.md C5 O-1 eval).

o1_demo is self-written, so it is never the headline; the headline stays the
held-out hard set scored by evals/run_guard.py.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
EVALS_DIR = ROOT / "evals"
for p in (ROOT, EVALS_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from run_guard import evaluate, load_rows  # noqa: E402 (main-owned parser/scorer)

from wall import results  # noqa: E402
from wall.contract import EvalResult  # noqa: E402

CASES = Path(__file__).resolve().parent / "o1_cases.jsonl"
EVAL_SET = "o1_demo"


def evaluate_judge(judge: str) -> tuple[EvalResult, int] | None:
    """Score a B2 judge ("prompt" or "river") on o1_cases.jsonl via evals/run_judges.py's
    own loaders, cache and scorer. Returns (result, errors), or None if it can't run."""
    import run_judges as rj  # imported lazily: pulls in river_client

    cases = [rj._flat_row_to_case(json.loads(line)) for line in CASES.read_text().splitlines() if line.strip()]
    cache_path = rj._cache_path(judge, EVAL_SET)
    if judge == "prompt":
        verdicts = rj.run_prompt(cases, cache_path)
    else:
        if not rj.STATE_PATH.exists():
            print(f"[{EVAL_SET}] river_judge: skipped ({rj.STATE_PATH} not found; no River checkpoint here)")
            return None
        verdicts = rj.run_sampled(cases, cache_path, checkpoint=rj._load_river_checkpoint(), max_tokens=400)
    return rj._score(cases, verdicts)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--judge",
        choices=["river"],
        help="also score the River-tuned judge (needs .runtime/river/state.json from river/train.py)",
    )
    args = parser.parse_args()

    raw_lines = [line for line in CASES.read_text().splitlines() if line.strip()]
    rows = load_rows(CASES)
    if len(rows) != len(raw_lines):
        raise SystemExit(
            f"[{EVAL_SET}] {len(raw_lines) - len(rows)} row(s) failed to parse with parse_flat_row; fix o1_cases.jsonl"
        )
    print(
        f"[{EVAL_SET}] loaded {len(rows)} rows "
        f"({sum(r.label == 'LEAK' for r in rows)} LEAK / {sum(r.label == 'CLEAN' for r in rows)} CLEAN)"
    )

    for detector in ("regex", "carryover"):
        result = evaluate(rows, detector)
        results.record(detector, EVAL_SET, result)
        print(
            f"[{EVAL_SET}] {detector}: caught {result.caught}/{result.leaks} leaks, "
            f"{result.false_alarms}/{result.clean} false alarms (n={result.n})"
        )

    for judge in ["prompt"] + (["river"] if args.judge == "river" else []):
        scored = evaluate_judge(judge)
        if scored is None:
            continue
        result, errors = scored
        detector = f"{judge}_judge"
        results.record(detector, EVAL_SET, result)
        print(
            f"[{EVAL_SET}] {detector}: caught {result.caught}/{result.leaks} leaks, "
            f"{result.false_alarms}/{result.clean} false alarms (n={result.n}, errors={errors})"
        )


if __name__ == "__main__":
    main()
