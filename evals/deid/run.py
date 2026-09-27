"""Held-out O-1 de-identification eval: rules vs base Qwen vs River-tuned Qwen.

    uv run python -m evals.deid.run [--fixtures DIR] [--matters o1-a,o1-b] [--detectors ...]

See evals/deid/README.md for the metric mapping onto wall.results.record().
"""

import argparse
import json
import re
from pathlib import Path

from wall import river_deid
from wall.contract import EvalResult
from wall.deid import _find_all, _pii_candidates
from wall.results import record

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "matters"
HELD_OUT = ["o1-halliday", "o1-brandt", "o1-almeida", "o1-duarte"]
EVAL_SET = "o1_deid_heldout"
COVERED = 0.8  # an identifier counts as removed when >=80% of its characters are
WORD = re.compile(r"\w+")
DISTINCTIVE: set[str] = set()  # quasi-identifier fact strings, reported separately


def paragraphs(fixtures: Path, matter: str) -> tuple[list[str], list[str]]:
    facts = json.loads((fixtures / matter / "matter.json").read_text())["facts"]
    idents = sorted({v for vals in facts.values() for v in vals}, key=len, reverse=True)
    DISTINCTIVE.update(v for v in facts.get("distinctive", []) if " " in v)  # phrases, not ID numbers
    paras = [p.strip() for doc in sorted((fixtures / matter).glob("*.md"))
             for p in doc.read_text().split("\n\n") if p.strip()]
    return paras, idents


def rules_spans(text: str, idents: list[str], with_facts: bool) -> list[tuple[int, int]]:
    out = [(s, e) for s, e, _ in _pii_candidates(text)]
    if with_facts:
        out += [se for v in idents for se in _find_all(text, v)]
    return out


def text_spans(text: str, spans: list[dict]) -> list[tuple[int, int]]:
    return [se for s in spans for se in _find_all(text, s["text"])]


def score(text: str, idents: list[str], predicted: list[tuple[int, int]]) -> dict:
    removed = [False] * len(text)
    for s, e in predicted:
        removed[s:e] = [True] * (e - s)
    ident_chars = [False] * len(text)
    caught = leaks = q_caught = q_leaks = 0
    for v in idents:
        for s, e in _find_all(text, v):
            hit = sum(removed[s:e]) >= COVERED * (e - s)
            leaks += 1
            caught += hit
            if v in DISTINCTIVE:
                q_leaks += 1
                q_caught += hit
            ident_chars[s:e] = [True] * (e - s)
    clean = over = 0
    for m in WORD.finditer(text):
        if any(ident_chars[m.start():m.end()]):
            continue
        clean += 1
        over += any(removed[m.start():m.end()])
    return {"caught": caught, "leaks": leaks, "false_alarms": over, "clean": clean,
            "q_caught": q_caught, "q_leaks": q_leaks}


def main(fixtures: Path, matters: list[str], detectors: list[str]) -> None:
    rows = [(p, idents) for m in matters for p, idents in
            [(p, i) for ps, i in [paragraphs(fixtures, m)] for p in ps]]
    texts = [p for p, _ in rows]
    predictions = {}
    if "deid_rules" in detectors:
        predictions["deid_rules"] = [rules_spans(p, i, False) for p, i in rows]
    if "deid_rules_with_facts" in detectors:
        predictions["deid_rules_with_facts"] = [rules_spans(p, i, True) for p, i in rows]
    for name, model in [("river_deid_base", "base"), ("river_deid_tuned", "tuned")]:
        if name in detectors:
            completions = river_deid.sample_many(texts, "immigration", model)
            parsed = [river_deid.parse(p, c) for p, c in zip(texts, completions)]
            predictions[name] = [text_spans(p, sp) for p, sp in zip(texts, parsed)]
            dump = river_deid.RUNTIME / "river-deid" / f"eval_{name}.jsonl"  # gitignored runtime dir
            dump.write_text("".join(json.dumps({"paragraph": i, "spans": sp}) + "\n" for i, sp in enumerate(parsed)))
    for name, preds in predictions.items():
        total = {"caught": 0, "leaks": 0, "false_alarms": 0, "clean": 0, "q_caught": 0, "q_leaks": 0}
        for (p, idents), pred in zip(rows, preds):
            for k, v in score(p, idents, pred).items():
                total[k] += v
        q_caught, q_leaks = total.pop("q_caught"), total.pop("q_leaks")
        result = EvalResult(**total, n=total["leaks"] + total["clean"])
        record(name, EVAL_SET, result)
        print(f"{name}: identifiers removed {result.caught}/{result.leaks}, "
              f"(quasi-identifier phrases {q_caught}/{q_leaks}), "
              f"over-redacted tokens {result.false_alarms}/{result.clean} "
              f"({len(rows)} paragraphs, matters={','.join(matters)})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", type=Path, default=FIXTURES)
    parser.add_argument("--matters", default=",".join(HELD_OUT))
    parser.add_argument("--detectors", default="deid_rules,deid_rules_with_facts,river_deid_base,river_deid_tuned")
    args = parser.parse_args()
    main(args.fixtures, args.matters.split(","), args.detectors.split(","))
