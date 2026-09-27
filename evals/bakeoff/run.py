"""De-identification bakeoff: measure every detector (and unions) on k3's held-out
O-1 paragraphs, then pick the strategy by rule and write .runtime/deid_strategy.json.

    uv run python -m evals.bakeoff.run [--skip claude,river_base,river_tuned]

Scorer, split and fixtures are k3's (evals/deid/run.py); nothing is re-invented here.
Every model call is cached under .runtime/bakeoff/ so reruns are free.
"""

import argparse
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from evals.cost.measure import PRICE_PER_MTOK
from evals.deid.run import FIXTURES, HELD_OUT, paragraphs, score, text_spans
from wall import deid_strategy, matters, river_deid

CACHE = river_deid.RUNTIME / "bakeoff"
UNIONS = {
    "rules+facts": ["rules", "facts"],
    "rules+facts+claude": ["rules", "facts", "claude"],
    "rules+facts+river_base": ["rules", "facts", "river_base"],
    "rules+facts+river": ["rules", "facts", "river_tuned"],
    "rules+facts+river+claude": ["rules", "facts", "river_tuned", "claude"],
}


def _cached(name: str, texts: list[str], run) -> tuple[list[list[dict]], dict]:
    """Spans per text for a model detector, from cache or `run(missing_texts)`."""
    path = CACHE / f"{name}.json"
    cache = json.loads(path.read_text()) if path.exists() else {}
    key = lambda t: hashlib.sha256(t.encode()).hexdigest()[:24]  # noqa: E731
    missing = [t for t in dict.fromkeys(texts) if key(t) not in cache]
    if missing:
        for t, entry in zip(missing, run(missing)):
            cache[key(t)] = entry
        CACHE.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cache))
    entries = [cache[key(t)] for t in texts]
    return [e["spans"] for e in entries], {
        "latency_s": sum(e["latency_s"] for e in entries) / len(entries),
        "cost_usd": sum(e.get("cost_usd") or 0 for e in entries) if all(e.get("cost_usd") is not None for e in entries) else None,
    }


def claude_run(texts: list[str]) -> list[dict]:
    model = os.environ.get("WALL_LLM_MODEL", "claude-sonnet-5")
    price = PRICE_PER_MTOK[model]

    def one(t: str) -> dict:
        t0 = time.monotonic()
        msg = deid_strategy.claude_message(t, "immigration", model)
        u = msg.usage
        return {
            "spans": river_deid.parse(t, deid_strategy.reply_text(msg)),
            "latency_s": time.monotonic() - t0,
            "cost_usd": (u.input_tokens * price["input"] + u.output_tokens * price["output"]) / 1e6,
        }

    with ThreadPoolExecutor(8) as pool:
        return list(pool.map(one, texts))


def river_run(model: str):
    def run(texts: list[str]) -> list[dict]:
        if model == "tuned" and not river_deid.checkpoint_path():
            # Final checkpoint not ready: use the latest saved one (step-20+), as briefed.
            state = json.loads(river_deid.STATE_PATH.read_text())
            river_deid.checkpoint_path = lambda: state["checkpoint_path"]
            print(f"river_tuned: using in-progress checkpoint step {state.get('checkpoint_step')}")
        t0 = time.monotonic()
        completions = river_deid.sample_many(texts, "immigration", model)
        per = (time.monotonic() - t0) / len(texts)  # one batched session; amortised per paragraph
        return [{"spans": river_deid.parse(t, c), "latency_s": per, "cost_usd": None}
                for t, c in zip(texts, completions)]
    return run


def local(texts: list[str], name: str) -> tuple[list[list[dict]], dict]:
    t0 = time.monotonic()
    spans = [deid_strategy.DETECTORS[name](t, "immigration", None) for t in texts]
    return spans, {"latency_s": (time.monotonic() - t0) / len(texts), "cost_usd": 0.0}


def metrics(rows, preds: list[list[tuple[int, int]]], stats: dict) -> dict:
    total = {"caught": 0, "leaks": 0, "false_alarms": 0, "clean": 0, "q_caught": 0, "q_leaks": 0}
    for (p, idents), pred in zip(rows, preds):
        for k, v in score(p, idents, pred).items():
            total[k] += v
    return {
        "identifier_recall": total["caught"] / total["leaks"],
        "quasi_recall": total["q_caught"] / total["q_leaks"] if total["q_leaks"] else None,
        "over_redaction": total["false_alarms"] / total["clean"],
        "latency_ms_per_paragraph": round(stats["latency_s"] * 1000, 2),
        "cost_usd_per_1k_paragraphs": None if stats["cost_usd"] is None else round(stats["cost_usd"] / len(rows) * 1000, 4),
        **{k: total[k] for k in ("caught", "leaks", "q_caught", "q_leaks", "false_alarms", "clean")},
        "n_paragraphs": len(rows),
    }


def choose(results: dict, max_over: float) -> str:
    """Max identifier recall s.t. over-redaction <= max_over; tie-break quasi recall, then latency."""
    ok = {k: m for k, m in results.items() if m["over_redaction"] <= max_over}
    return max(ok, key=lambda k: (ok[k]["identifier_recall"], ok[k]["quasi_recall"] or 0,
                                  -ok[k]["latency_ms_per_paragraph"]))


def facts_other_matters(text: str, own: str) -> list[dict]:
    """The facts detector as it behaves on a document its own fact sheet does not cover."""
    return [{"text": v, "kind": k} for mid, m in matters.matters().items() if mid != own
            for k, vals in m["facts"].items() for v in vals if v and v in text]


def tuned_cache_name() -> str:
    state = json.loads(river_deid.STATE_PATH.read_text())
    return f"river_tuned_step{state.get('checkpoint_step')}" + ("_final" if state.get("status") == "done" else "")


def main(skip: set[str]) -> None:
    rows, owners = [], []
    for m in HELD_OUT:
        ps, idents = paragraphs(FIXTURES, m)
        rows += [(p, idents) for p in ps]
        owners += [m] * len(ps)
    texts = [p for p, _ in rows]
    spans, stats = {}, {}
    for name in ("facts", "rules"):
        spans[name], stats[name] = local(texts, name)
    runners = {"claude": ("claude", claude_run), "river_base": ("river_base", river_run("base")),
               "river_tuned": (tuned_cache_name(), river_run("tuned"))}
    for name, (cache_name, run) in runners.items():
        if name in skip:
            continue
        try:
            spans[name], stats[name] = _cached(cache_name, texts, run)
        except Exception as exc:  # a detector that cannot run is reported, not fatal
            print(f"{name}: skipped ({type(exc).__name__}: {exc})")
    # Two conditions. "known": the facts detector sees the paragraph's own fact sheet, which IS
    # the answer key (circular). "unseen": facts of other matters only -- a document whose
    # identifiers are not on any fact sheet yet. Selection uses "unseen".
    conditions = {}
    for cond in ("unseen", "known"):
        sp = dict(spans)
        if cond == "unseen":
            sp["facts"] = [facts_other_matters(t, o) for t, o in zip(texts, owners)]
        for union, parts in UNIONS.items():
            if all(p in sp for p in parts):
                sp[union] = [[s for p in parts for s in sp[p][i]] for i in range(len(texts))]
                stats[union] = {"latency_s": sum(stats[p]["latency_s"] for p in parts),
                                "cost_usd": None if any(stats[p]["cost_usd"] is None for p in parts)
                                else sum(stats[p]["cost_usd"] for p in parts)}
        conditions[cond] = {name: metrics(rows, [text_spans(t, s) for t, s in zip(texts, sp[name])], stats[name])
                            for name in sp}
    results = conditions["unseen"]
    max_over = float(os.environ.get("WALL_DEID_MAX_OVERREDACT", "0.10"))
    chosen = choose(results, max_over)
    out = {
        # facts stays on as a floor: free, and 0 over-redacted tokens in every condition.
        "detectors": list(dict.fromkeys(["facts", *UNIONS.get(chosen, [chosen])])),
        "chosen": chosen,
        "chosen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rule": f"max identifier recall s.t. over-redaction <= {max_over}; tie-break quasi recall, then latency; "
                "scored with the facts detector blind to the paragraph's own fact sheet; "
                "facts is always kept as a zero-cost, zero-over-redaction floor",
        "eval": f"k3 held-out {','.join(HELD_OUT)} ({len(rows)} paragraphs)",
        "river_tuned_checkpoint": tuned_cache_name() if "river_tuned" in spans else None,
        "metrics": results,
        "metrics_own_fact_sheet_known": conditions["known"],
    }
    deid_strategy.STRATEGY_PATH.parent.mkdir(parents=True, exist_ok=True)
    deid_strategy.STRATEGY_PATH.write_text(json.dumps(out, indent=2))
    for cond, res in conditions.items():
        print(f"-- {cond}")
        for name, m in res.items():
            print(f"{name:26s} ids {m['caught']}/{m['leaks']}  quasi {m['q_caught']}/{m['q_leaks']}  "
                  f"over {m['false_alarms']}/{m['clean']} ({m['over_redaction']:.3f})  "
                  f"{m['latency_ms_per_paragraph']} ms  ${m['cost_usd_per_1k_paragraphs']}/1k")
    print(f"chosen: {chosen} -> {out['detectors']}  ({deid_strategy.STRATEGY_PATH})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip", default="")
    main(set(filter(None, parser.parse_args().skip.split(","))))
