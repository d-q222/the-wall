"""Owned by C5: score regex, carryover, and the prompt judge on the synthetic O-1
leak set (evals/o1/o1_cases.jsonl) as eval set "o1_demo" (CONTRACT.md C5 O-1 eval).

o1_demo is self-written, so it is never the headline; the headline stays the
held-out hard set scored by evals/run_guard.py.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
EVALS_DIR = ROOT / "evals"
for p in (ROOT, EVALS_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from run_guard import EvalRow, evaluate, load_rows  # noqa: E402 (main-owned parser/scorer)

from wall import results  # noqa: E402
from wall.contract import EvalResult, JudgeRequest  # noqa: E402
from wall.judge import judge as prompt_judge  # noqa: E402

CASES = Path(__file__).resolve().parent / "o1_cases.jsonl"
EVAL_SET = "o1_demo"


def evaluate_prompt_judge(rows: list[EvalRow]) -> EvalResult | None:
    """Score wall.judge.judge() on every row. Returns None if it is still the B2 stub."""
    caught = leaks = false_alarms = clean = 0
    for row in rows:
        if row.label == "LEAK":
            leaks += 1
        else:
            clean += 1
        try:
            resp = prompt_judge(
                JudgeRequest(
                    current=row.current.text,
                    protected=[b.text for b in row.protected.values()],
                    draft=row.draft,
                )
            )
        except NotImplementedError:
            return None
        if resp.verdict == "leak":
            if row.label == "LEAK":
                caught += 1
            else:
                false_alarms += 1
    return EvalResult(caught=caught, leaks=leaks, false_alarms=false_alarms, clean=clean, n=leaks + clean)


def run_river() -> None:
    """Best-effort passthrough to evals/run_judges.py (B2, lands with b2-river).

    Its CLI is not yet defined on this branch; the coordinator re-runs this once
    b2-river merges and adjusts the call below if the signature differs.
    """
    script = EVALS_DIR / "run_judges.py"
    if not script.exists():
        print(f"[{EVAL_SET}] --judge river: {script} not found (b2-river not merged yet); skipped")
        return
    proc = subprocess.run(
        [sys.executable, str(script), str(CASES), "--eval-set", EVAL_SET],
        capture_output=True,
        text=True,
    )
    print(proc.stdout, end="")
    if proc.returncode != 0:
        print(f"[{EVAL_SET}] --judge river: run_judges.py exited {proc.returncode}: {proc.stderr.strip()}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--judge",
        choices=["river"],
        help="also shell out to evals/run_judges.py for the river-tuned judge, if present",
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

    judge_result = evaluate_prompt_judge(rows)
    if judge_result is None:
        print(f"[{EVAL_SET}] prompt_judge: skipped (wall.judge raised NotImplementedError; b2-river not merged yet)")
    else:
        results.record("prompt_judge", EVAL_SET, judge_result)
        print(
            f"[{EVAL_SET}] prompt_judge: caught {judge_result.caught}/{judge_result.leaks} leaks, "
            f"{judge_result.false_alarms}/{judge_result.clean} false alarms (n={judge_result.n})"
        )

    if args.judge == "river":
        run_river()


if __name__ == "__main__":
    main()
