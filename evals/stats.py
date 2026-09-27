"""Owned by E6: make every number defensible (PRD "every number is held-out").

Reads results/results.json (wall.results.load()), computes 95% Wilson score intervals
for leak recall (caught/leaks) and false-alarm rate (false_alarms/clean) per
detector x eval set, prints a projector-readable table, and writes
results/ci.json as {detector: {eval_set: {"recall": [lo, hi], "false_alarm": [lo, hi]}}}.

Also exposes a two-proportion comparison helper for "is detector A's recall on set S
different from detector B's" questions.
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

if __name__ == "__main__" and __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wall import results

Z_95 = 1.959963984540054  # two-sided 95% normal quantile

CI_PATH = Path(os.environ.get("WALL_CI", Path.home() / "the-wall" / "results" / "ci.json"))


def wilson_interval(successes: int, total: int, z: float = Z_95) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (95% by default).

    More reliable than a normal approximation at the small-n, high/low-p extremes
    these eval sets sit at (e.g. 0/102 caught).
    """
    if total <= 0:
        raise ValueError("total must be positive")
    if not (0 <= successes <= total):
        raise ValueError("successes must be between 0 and total")
    phat = successes / total
    z2 = z * z
    denom = 1 + z2 / total
    center = phat + z2 / (2 * total)
    margin = z * math.sqrt(phat * (1 - phat) / total + z2 / (4 * total * total))
    lo = (center - margin) / denom
    hi = (center + margin) / denom
    return max(0.0, lo), min(1.0, hi)


def compare_proportions(k1: int, n1: int, k2: int, n2: int, z: float = Z_95) -> dict:
    """95% CI for p1 - p2 via Newcombe's method (built from each side's Wilson interval,
    so it agrees with wilson_interval rather than a separate normal-approx test).

    Also reports whether the two groups' own Wilson intervals overlap, since that's
    the plain-language check ("do the intervals overlap") most people actually want.
    """
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson_interval(k1, n1, z)
    l2, u2 = wilson_interval(k2, n2, z)
    diff = p1 - p2
    lo = diff - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = diff + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return {
        "p1": p1,
        "p2": p2,
        "diff": diff,
        "diff_ci": (lo, hi),
        "p1_ci": (l1, u1),
        "p2_ci": (l2, u2),
        "overlap": l1 <= u2 and l2 <= u1,
    }


def compare_recall(data: dict, detector_a: str, detector_b: str, eval_set: str) -> dict:
    """Two-proportion comparison of detector_a vs detector_b's leak recall on eval_set."""
    ra = data[detector_a][eval_set]
    rb = data[detector_b][eval_set]
    return compare_proportions(ra["caught"], ra["leaks"], rb["caught"], rb["leaks"])


def compute_ci(data: dict) -> dict:
    out: dict = {}
    for detector, sets in data.items():
        out[detector] = {}
        for eval_set, r in sets.items():
            entry = {}
            if r["leaks"] > 0:
                lo, hi = wilson_interval(r["caught"], r["leaks"])
                entry["recall"] = [round(lo, 4), round(hi, 4)]
            if r["clean"] > 0:
                lo, hi = wilson_interval(r["false_alarms"], r["clean"])
                entry["false_alarm"] = [round(lo, 4), round(hi, 4)]
            out[detector][eval_set] = entry
    return out


def format_table(data: dict, ci: dict) -> str:
    header = f"{'detector':<14}{'eval_set':<10}{'recall':<26}{'false_alarm':<26}"
    lines = [header, "-" * len(header)]
    for detector in sorted(data):
        for eval_set in sorted(data[detector]):
            r = data[detector][eval_set]
            c = ci[detector][eval_set]
            if "recall" in c:
                lo, hi = c["recall"]
                recall_str = f"{r['caught']}/{r['leaks']} [{lo:.0%}-{hi:.0%}]"
            else:
                recall_str = "n/a (0 leaks)"
            if "false_alarm" in c:
                lo, hi = c["false_alarm"]
                fa_str = f"{r['false_alarms']}/{r['clean']} [{lo:.0%}-{hi:.0%}]"
            else:
                fa_str = "n/a (0 clean)"
            lines.append(f"{detector:<14}{eval_set:<10}{recall_str:<26}{fa_str:<26}")
    return "\n".join(lines)


def write_ci(ci: dict, path: Path = CI_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ci, indent=2))


def main() -> None:
    data = results.load()
    if not data:
        print("no results yet: run the eval scripts first (results/results.json is empty)")
        return
    ci = compute_ci(data)
    print(format_table(data, ci))
    write_ci(ci, CI_PATH)
    print(f"\nwrote {CI_PATH}")


if __name__ == "__main__":
    main()
