"""Run one judge detector over one eval set, write wall.results.record() (PRD FR-7/FR-9).

    uv run python -m evals.run_judges --judge prompt --set hard
    uv run python -m evals.run_judges --judge base   --set hard
    uv run python -m evals.run_judges --judge river  --set hard

`base` and `river` sample the Qwen judge model on River (untuned vs the LoRA
checkpoint from river/train.py); `prompt` calls wall.judge.judge() (anthropic).
Responses are cached under .runtime/eval_cache/ so a rerun over the same
judge+set only samples the rows that weren't cached yet.

Accepts both row shapes present in the data pack: the chat-transcript format
used by judge_train_v2.jsonl / judge_eval*.jsonl, and the flat
{current, protected[], draft, label} format docs/BLIND_SET.md defines for
blind.jsonl (mirrors evals/run_guard.py's parse_flat_row).

Run as `-m evals.run_judges`, not the file path directly, so the repo-root
packages (`wall`, `river`) resolve.
"""

import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import NamedTuple

import river_client as river
from river_client.renderers import get_renderer

from river.env import load_dotenv

load_dotenv()

from wall.contract import EvalResult, JudgeRequest
from wall.judge import JudgeError, judge as run_prompt_judge
from wall.results import record

DATA_DIR = Path("/Users/dqi26/the-wall/data")
SET_FILES = {
    "standard": "judge_eval.jsonl",
    "hard": "judge_eval_hard.jsonl",
    "demo": "demo_leak_cases.jsonl",
    "blind": "blind.jsonl",
}
BASE_MODEL = "Qwen/Qwen3.6-35B-A3B-FP8"
CACHE_DIR = Path(".runtime/eval_cache")
STATE_PATH = Path(".runtime/river/state.json")

DETECTOR_NAME = {"prompt": "prompt_judge", "base": "base_judge", "river": "river_judge"}

# Matches the wire format judge_train_v2.jsonl / judge_eval*.jsonl were rendered from.
JUDGE_SYSTEM_PROMPT = (
    "You are a confidentiality wall for a law firm. You receive PROTECTED facts from other "
    'client matters and a DRAFT for the current matter. Reply with JSON only: {"verdict":'
    '"LEAK"|"CLEAN","matter":id or null,"evidence":quote or null}. Facts about the current '
    "matter are never leaks. Descriptions that identify another matter without naming it ARE leaks."
)

_CURRENT_RE = re.compile(r"CURRENT MATTER (.+)")
_PROTECTED_RE = re.compile(r"^- (.+)$", re.MULTILINE)
_DRAFT_RE = re.compile(r"DRAFT:\n(.*)", re.DOTALL)


class EvalCase(NamedTuple):
    current: str
    protected: list[str]
    draft: str
    label: str  # "leak" | "clean"
    messages: list[dict]  # system + user, ready to sample a completion from


def _build_messages(current: str, protected: list[str], draft: str) -> list[dict]:
    protected_block = "\n".join(f"- {p}" for p in protected)
    user = f"CURRENT MATTER {current}\n\nPROTECTED (other matters):\n{protected_block}\n\nDRAFT:\n{draft}"
    return [{"role": "system", "content": JUDGE_SYSTEM_PROMPT}, {"role": "user", "content": user}]


def _messages_row_to_case(row: dict) -> EvalCase | None:
    """Rows shaped like judge_train_v2.jsonl / judge_eval*.jsonl (chat transcript + meta.label)."""
    try:
        user = row["messages"][1]["content"]
    except (KeyError, IndexError, TypeError):
        return None
    current_m, draft_m = _CURRENT_RE.search(user), _DRAFT_RE.search(user)
    if not current_m or not draft_m:
        return None
    label = str(row.get("meta", {}).get("label", "")).strip().lower()
    if label not in ("leak", "clean"):
        return None
    return EvalCase(
        current=current_m.group(1).strip(),
        protected=_PROTECTED_RE.findall(user),
        draft=draft_m.group(1).strip(),
        label=label,
        messages=row["messages"][:-1],
    )


def _flat_row_to_case(row: dict) -> EvalCase | None:
    """Rows shaped like JudgeRequest + label: {current, protected: [...], draft, label}."""
    if not {"current", "protected", "draft"} <= row.keys():
        return None
    label = str(row.get("label", "")).strip().lower()
    if label not in ("leak", "clean"):
        return None
    current = str(row["current"]).strip()
    protected = [str(p) for p in row["protected"]]
    draft = str(row["draft"]).strip()
    return EvalCase(
        current=current,
        protected=protected,
        draft=draft,
        label=label,
        messages=_build_messages(current, protected, draft),
    )


def _load_set(name: str) -> list[EvalCase]:
    path = DATA_DIR / SET_FILES[name]
    cases: list[EvalCase] = []
    skipped = 0
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            case = _messages_row_to_case(raw) or _flat_row_to_case(raw)
            if case is None:
                skipped += 1
                continue
            cases.append(case)
    if skipped:
        print(f"  ({skipped} row(s) in {path.name} did not match a known schema; skipped)")
    return cases


def _extract_json(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no JSON object in output")
    return json.loads(text[start : end + 1])


def _verdict_from_sample_text(text: str) -> str | None:
    body = text.split("</think>", 1)[-1] if "</think>" in text else text
    try:
        data = _extract_json(body)
        verdict = str(data["verdict"]).strip().lower()
        return verdict if verdict in ("clean", "leak") else None
    except (ValueError, KeyError, json.JSONDecodeError):
        return None


def _cache_path(judge: str, eval_set: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{judge}_{eval_set}.jsonl"


def _load_cache(path: Path) -> dict[int, str | None]:
    if not path.exists():
        return {}
    cache: dict[int, str | None] = {}
    with path.open() as f:
        for line in f:
            row = json.loads(line)
            cache[row["idx"]] = row["verdict"]
    return cache


def _append_cache(path: Path, idx: int, verdict: str | None) -> None:
    with path.open("a") as f:
        f.write(json.dumps({"idx": idx, "verdict": verdict}) + "\n")


def _score(cases: list[EvalCase], verdicts: list[str | None]) -> tuple[EvalResult, int]:
    n = len(cases)
    leaks = clean = caught = false_alarms = errors = 0
    for case, verdict in zip(cases, verdicts):
        if case.label == "leak":
            leaks += 1
        else:
            clean += 1
        if verdict is None:
            errors += 1
            continue
        if verdict == "leak":
            if case.label == "leak":
                caught += 1
            else:
                false_alarms += 1
    return EvalResult(caught=caught, leaks=leaks, false_alarms=false_alarms, clean=clean, n=n), errors


def _judge_one(case: EvalCase) -> str | None:
    req = JudgeRequest(current=case.current, protected=case.protected, draft=case.draft)
    try:
        return run_prompt_judge(req).verdict
    except JudgeError:
        return None


def run_prompt(cases: list[EvalCase], cache_path: Path, *, concurrency: int = 6) -> list[str | None]:
    cache = _load_cache(cache_path)
    verdicts: list[str | None] = [cache.get(idx) for idx in range(len(cases))]
    pending = [(idx, case) for idx, case in enumerate(cases) if idx not in cache]
    if not pending:
        return verdicts

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        for (idx, _case), verdict in zip(pending, pool.map(_judge_one, (case for _, case in pending))):
            verdicts[idx] = verdict
            _append_cache(cache_path, idx, verdict)
    return verdicts


def run_sampled(
    cases: list[EvalCase], cache_path: Path, *, checkpoint: "river.Checkpoint | None", max_tokens: int
) -> list[str | None]:
    cache = _load_cache(cache_path)
    pending = [(idx, case) for idx, case in enumerate(cases) if idx not in cache]
    verdicts: list[str | None] = [cache.get(idx) for idx in range(len(cases))]
    if not pending:
        return verdicts

    renderer = get_renderer(BASE_MODEL, thinking=False)
    stop = renderer.get_stop_strings()
    prompts = [renderer.build_sample_prompt(case.messages).prompt for _, case in pending]

    client = river.Client(api_key=os.environ["RIVER_API_KEY"])
    try:
        if checkpoint is None:
            samples = client.sample(prompts=prompts, base_model=BASE_MODEL, stop=stop, max_tokens=max_tokens)
            sampled_texts = [s.text for s in samples]
        else:
            with client.session(job="b2-judge-eval") as session:
                groups = session.sample(
                    prompts=prompts, base_model=BASE_MODEL, checkpoint=checkpoint, stop=stop, max_tokens=max_tokens
                )
                sampled_texts = [g[0].text for g in groups]
    finally:
        client.close()

    for (idx, _case), text in zip(pending, sampled_texts):
        verdict = _verdict_from_sample_text(text)
        verdicts[idx] = verdict
        _append_cache(cache_path, idx, verdict)
    return verdicts


def _load_river_checkpoint() -> "river.Checkpoint":
    if not STATE_PATH.exists():
        print(f"no {STATE_PATH}: river training hasn't produced a checkpoint yet", file=sys.stderr)
        sys.exit(1)
    state = json.loads(STATE_PATH.read_text())
    if "checkpoint_path" not in state:
        print(f"{STATE_PATH} has no checkpoint yet (status={state.get('status')})", file=sys.stderr)
        sys.exit(1)
    return river.Checkpoint(
        path=state["checkpoint_path"],
        step=state["checkpoint_step"],
        checkpoint_type=state["checkpoint_type"],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--judge", choices=["prompt", "base", "river"], required=True)
    parser.add_argument("--set", dest="eval_set", choices=list(SET_FILES), required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-tokens", type=int, default=400)
    args = parser.parse_args()

    path = DATA_DIR / SET_FILES[args.eval_set]
    if not path.exists():
        print(f"skipped: {path.name} not found in {DATA_DIR}", file=sys.stderr)
        sys.exit(0)

    cases = _load_set(args.eval_set)
    if args.limit:
        cases = cases[: args.limit]
    cache_path = _cache_path(args.judge, args.eval_set)

    if args.judge == "prompt":
        verdicts = run_prompt(cases, cache_path)
    elif args.judge == "base":
        verdicts = run_sampled(cases, cache_path, checkpoint=None, max_tokens=args.max_tokens)
    else:
        ckpt = _load_river_checkpoint()
        verdicts = run_sampled(cases, cache_path, checkpoint=ckpt, max_tokens=args.max_tokens)

    result, errors = _score(cases, verdicts)
    detector = DETECTOR_NAME[args.judge]
    record(detector, args.eval_set, result)
    print(
        f"{detector} on {args.eval_set}: n={result.n} leaks={result.leaks} clean={result.clean} "
        f"caught={result.caught} false_alarms={result.false_alarms} errors={errors}"
    )


if __name__ == "__main__":
    main()
