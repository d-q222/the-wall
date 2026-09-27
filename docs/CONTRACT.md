# Contract and ownership

Every agent's brief is this file plus `docs/PRD.md` (and `ACCESS.md` once it lands).
No agent invents an endpoint. Contract changes go through the coordinator and land on `main`.

## Endpoints (`wall/contract.py`, served by `wall/server.py`)

| Endpoint | Input | Output | Implemented in |
|---|---|---|---|
| POST /check | matter_id, draft | verdict, hits[] of {detector, matter, evidence} | `wall/guard.py` (B1) |
| POST /scrub | matter_id, practice, text | text, removed | `wall/scrub.py` (B3) |
| POST /judge | current, protected[], draft | verdict, matter, evidence | `wall/judge.py` (B2) |
| results/results.json | `wall.results.record()` | {detector: {eval_set: {caught, leaks, false_alarms, clean, n}}} | eval runners |

Run the API: `uv run uvicorn wall.server:app --port 8787`

Eval set names in results.json: `standard` (judge_eval.jsonl), `hard` (judge_eval_hard.jsonl),
`demo` (demo_leak_cases.jsonl), `blind` (blind.jsonl).
Detector names: `regex`, `carryover`, `prompt_judge`, `base_judge` (base Qwen), `river_judge`.

## Shared, read-only for agents (edit only on `main`)

`wall/contract.py`, `wall/server.py`, `wall/matters.py`, `wall/results.py`, `fixtures/`, `docs/`, `pyproject.toml`.
Need a dependency? Add it with `uv add` and say so in your handoff; the coordinator resolves lockfile conflicts.

## Ownership (one agent per worktree, never two agents on the same files)

| Agent | Branch | Owns | Done when |
|---|---|---|---|
| A1 walls | `a1-walls` | `walls/` | `walls/attack.py` prints permission_denied for the matter-B client on matter A |
| A2 agent | `a2-agent` | `agent/` | Draft for chen uses only chen facts and passes /check |
| A3 scoreboard | `a3-scoreboard` | `scoreboard/` | Renders every detector in results.json with n |
| B1 guard | `b1-guard` | `wall/guard.py`, `evals/run_guard.py`, `tests/test_guard.py` | Reproduces 79/97 (standard) and 0/102 (hard) baselines |
| B2 river | `b2-river` | `wall/judge.py`, `river/`, `evals/run_judges.py`, `tests/test_judge.py` | Three-judge rows in results.json (prompt judge first) |
| B3 scrub | `b3-scrub` | `wall/scrub.py`, `memorable/`, `tests/test_scrub.py` | Scrubbed Delmarva procedure has 0 client facts; memorable ingest accepts it |

## Cross-branch handoffs

- **A1 → A2**: A1 writes one credentials file per matter at `.runtime/clients/<matter_id>.json`
  (`{"url": ..., "client_id": ..., "client_secret": ..., "source_id": ...}`) and documents recall
  in `walls/README.md`. A2 reads only that file. Agents never run as local trusted callers.
- **A2 → B1**: A2 calls `POST /check` over HTTP; until B1 lands it tolerates a 500.
- **B3 → B1**: scrub acceptance is "checks clean against every other matter" — B3 tests with its own
  fact list from `wall.matters`; the /check round-trip is verified at integration.
- **all → A3**: the scoreboard reads only `results/results.json`.

## Rules

- No real client data. Synthetic matters live in `fixtures/matters/`.
- Never auto-paraphrase a draft to beat a detector. Flags go to a human.
- Every reported number is held-out and states n.
- Don't commit `data/` or anything under `.runtime/`.
- Agents don't merge each other's work; the coordinator reviews every merge.
