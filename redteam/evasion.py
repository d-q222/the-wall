"""Evasion red team: cross-matter leaks in formats an exact-string/n-gram
detector was never asked to recognize.

Each case embeds a real 'delmarva' fact (fixtures/matters/delmarva/matter.json)
into a drafting sentence for the 'chen' matter, in a format a careless or
adversarial drafter might actually type. Each draft is run through the two
live main-branch layers directly (no server needed):

  - wall.guard.check()  -- regex fingerprint + carryover 6-gram (B1)
  - wall.scrub.scrub()  -- deterministic scrubber, run as it would actually
    run in production: on the chen draft, with matter_id='chen' (scrub only
    ever strips the CURRENT matter's own facts by design; its remaining
    generic patterns -- dollar amounts, multi-word proper nouns, dates,
    exhibits/sections -- apply to the whole text regardless of whose fact it
    is, so it sometimes catches a cross-matter leak guard's exact-match regex
    misses, and sometimes doesn't).

These are self-written, not the held-out 79/97 or 0/102 headline numbers
(PRD Evaluation) -- they exist to show what each layer does and does not stop.

Run: uv run python redteam/evasion.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from wall.contract import CheckRequest, ScrubRequest  # noqa: E402
from wall.guard import check as guard_check  # noqa: E402
from wall.scrub import scrub  # noqa: E402

BOLD, RESET, DIM = "\033[1m", "\033[0m", "\033[2m"


def default_survives(span: str):
    return lambda scrubbed: span.lower() in scrubbed.lower()


def split_name_survives(scrubbed: str) -> bool:
    lowered = scrubbed.lower()
    return "marcus" in lowered and "pruitt" in lowered


# Real delmarva facts: names=["Delmarva Logistics", "Marcus Pruitt", ...],
# amounts=["$418,250", ...], distinctive=["refrigerated trailer 7 left idling
# at the Salisbury yard for nineteen hours"]. All leaked into a 'chen' draft.
CASES = [
    dict(
        category="amount", fmt="exact ($418,250)",
        sentence="For comparison, the firm previously recovered $418,250 in a similar shipping dispute.",
        survives=default_survives("$418,250"),
    ),
    dict(
        category="amount", fmt="abbreviated ($418K)",
        sentence="For comparison, the firm previously recovered $418K in a similar shipping dispute.",
        survives=default_survives("$418K"),
    ),
    dict(
        category="amount", fmt="worded (418 thousand dollars)",
        sentence="For comparison, the firm previously recovered 418 thousand dollars in a similar shipping dispute.",
        survives=default_survives("418 thousand dollars"),
    ),
    dict(
        category="amount", fmt="spelled out (four hundred eighteen thousand dollars)",
        sentence="For comparison, the firm previously recovered four hundred eighteen thousand dollars in a similar shipping dispute.",
        survives=default_survives("four hundred eighteen thousand dollars"),
    ),
    dict(
        category="name", fmt="exact (Marcus Pruitt)",
        sentence="The opposing operations lead, Marcus Pruitt, handled a comparable dispute last year.",
        survives=default_survives("Marcus Pruitt"),
    ),
    dict(
        category="name", fmt="initials (M.P.)",
        sentence="The opposing operations lead, M.P., handled a comparable dispute last year.",
        survives=default_survives("M.P."),
    ),
    dict(
        category="name", fmt="misspelled (Marcus Pruit)",
        sentence="The opposing operations lead, Marcus Pruit, handled a comparable dispute last year.",
        survives=default_survives("Marcus Pruit"),
    ),
    dict(
        category="name", fmt="split across the sentence",
        sentence="The opposing operations lead was named Marcus; his surname, Pruitt, appeared on every filing.",
        survives=split_name_survives,
    ),
    dict(
        category="description", fmt="verbatim distinctive detail",
        sentence="Similar to another case, refrigerated trailer 7 left idling at the Salisbury yard for nineteen hours.",
        survives=default_survives("refrigerated trailer 7 left idling at the Salisbury yard for nineteen hours"),
    ),
    dict(
        category="description", fmt="paraphrased distinctive detail",
        sentence="Similar to another case, a reefer unit sat running overnight at their Salisbury facility.",
        survives=default_survives("a reefer unit sat running overnight at their Salisbury facility"),
    ),
]


def main() -> int:
    rows = []
    for case in CASES:
        draft = case["sentence"]
        resp = guard_check(CheckRequest(matter_id="chen", draft=draft))
        detectors_hit = {h.detector for h in resp.hits}
        regex_caught = "regex" in detectors_hit
        carryover_caught = "carryover" in detectors_hit

        scrub_resp = scrub(ScrubRequest(matter_id="chen", practice="trusts_estates", text=draft))
        scrub_caught = not case["survives"](scrub_resp.text)

        rows.append(dict(
            category=case["category"], fmt=case["fmt"],
            regex=regex_caught, carryover=carryover_caught, scrub=scrub_caught,
        ))

    print(f"\n{BOLD}=== EVASION RED TEAM: cross-matter leak formats vs guard + scrub ==={RESET}\n")
    header = f"{'category':<12} {'format':<48} {'regex':<7} {'carryover':<10} {'scrub':<6}"
    print(header)
    print("-" * len(header))
    for r in rows:
        def mark(b):
            return "caught" if b else f"{DIM}evades{RESET}"
        print(f"{r['category']:<12} {r['fmt']:<48} {mark(r['regex']):<7} {mark(r['carryover']):<10} {mark(r['scrub']):<6}")

    n = len(rows)
    print(f"\n{BOLD}Counts (n={n}, self-written -- never the headline number):{RESET}")
    print(f"  regex     caught {sum(r['regex'] for r in rows)}/{n}")
    print(f"  carryover caught {sum(r['carryover'] for r in rows)}/{n}")
    print(f"  scrub     caught {sum(r['scrub'] for r in rows)}/{n}")
    fully_evaded = [r for r in rows if not r["regex"] and not r["carryover"] and not r["scrub"]]
    print(f"  evaded ALL THREE: {len(fully_evaded)}/{n} -- {', '.join(r['fmt'] for r in fully_evaded)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
