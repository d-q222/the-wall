"""Run one judge detector over one eval set, write wall.results.record() (PRD FR-7/FR-9).

    uv run python -m evals.run_judges --judge prompt --set hard
    uv run python -m evals.run_judges --judge base   --set hard
    uv run python -m evals.run_judges --judge river  --set hard

`base` and `river` sample the Qwen judge model on River (untuned vs the LoRA
checkpoint from river/train.py); `prompt` calls wall.judge.judge() (anthropic).
Responses are cached under .runtime/eval_cache/ so a rerun over the same
judge+set only samples the rows that weren't cached yet.

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

_CURRENT_RE = re.compile(r"CURRENT MATTER (.+)")
_PROTECTED_RE = re.compile(r"^- (.+)$", re.MULTILINE)
_DRAFT_RE = re.compile(r"DRAFT:\n(.*)", re.DOTALL)


def _load_set(name: str) -> list[dict]:
    path = DATA_DIR / SET_FILES[name]
    with path.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def _ground_truth(row: dict) -> str:
    return row["meta"]["label"].strip().lower()


def _to_judge_request(user_text: str) -> JudgeRequest:
    current = _CURRENT_RE.search(user_text).group(1).strip()
    protected = _PROTECTED_RE.findall(user_text)
    draft = _DRAFT_RE.search(user_text).group(1).strip()
    return JudgeRequest(current=current, protected=protected, draft=draft)


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


def _score(rows: list[dict], verdicts: list[str | None]) -> tuple[EvalResult, int]:
    n = len(rows)
    leaks = clean = caught = false_alarms = errors = 0
    for row, verdict in zip(rows, verdicts):
        truth = _ground_truth(row)
        if truth == "leak":
            leaks += 1
        else:
            clean += 1
        if verdict is None:
            errors += 1
            continue
        if verdict == "leak":
            if truth == "leak":
                caught += 1
            else:
                false_alarms += 1
    return EvalResult(caught=caught, leaks=leaks, false_alarms=false_alarms, clean=clean, n=n), errors


def _judge_one(row: dict) -> str | None:
    req = _to_judge_request(row["messages"][1]["content"])
    try:
        return run_prompt_judge(req).verdict
    except JudgeError:
        return None


def run_prompt(rows: list[dict], cache_path: Path, *, concurrency: int = 6) -> list[str | None]:
    cache = _load_cache(cache_path)
    verdicts: list[str | None] = [cache.get(idx) for idx in range(len(rows))]
    pending = [(idx, row) for idx, row in enumerate(rows) if idx not in cache]
    if not pending:
        return verdicts

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        for (idx, _row), verdict in zip(pending, pool.map(_judge_one, (row for _, row in pending))):
            verdicts[idx] = verdict
            _append_cache(cache_path, idx, verdict)
    return verdicts


def run_sampled(
    rows: list[dict], cache_path: Path, *, checkpoint: "river.Checkpoint | None", max_tokens: int
) -> list[str | None]:
    cache = _load_cache(cache_path)
    pending = [(idx, row) for idx, row in enumerate(rows) if idx not in cache]
    verdicts: list[str | None] = [cache.get(idx) for idx in range(len(rows))]
    if not pending:
        return verdicts

    renderer = get_renderer(BASE_MODEL, thinking=False)
    stop = renderer.get_stop_strings()
    prompts = [renderer.build_sample_prompt(row["messages"][:-1]).prompt for _, row in pending]

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

    for (idx, _row), text in zip(pending, sampled_texts):
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

    rows = _load_set(args.eval_set)
    if args.limit:
        rows = rows[: args.limit]
    cache_path = _cache_path(args.judge, args.eval_set)

    if args.judge == "prompt":
        verdicts = run_prompt(rows, cache_path)
    elif args.judge == "base":
        verdicts = run_sampled(rows, cache_path, checkpoint=None, max_tokens=args.max_tokens)
    else:
        ckpt = _load_river_checkpoint()
        verdicts = run_sampled(rows, cache_path, checkpoint=ckpt, max_tokens=args.max_tokens)

    result, errors = _score(rows, verdicts)
    detector = DETECTOR_NAME[args.judge]
    record(detector, args.eval_set, result)
    print(
        f"{detector} on {args.eval_set}: n={result.n} leaks={result.leaks} clean={result.clean} "
        f"caught={result.caught} false_alarms={result.false_alarms} errors={errors}"
    )


if __name__ == "__main__":
    main()
