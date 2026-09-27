# Contract and ownership

Every agent's brief is this file plus `docs/PRD.md` (and `ACCESS.md` once it lands).
No agent invents an endpoint. Contract changes go through the coordinator and land on `main`.

## Endpoints (`wall/contract.py`, served by `wall/server.py`)

| Endpoint | Input | Output | Implemented in |
|---|---|---|---|
| POST /check | matter_id, draft | verdict, hits[] of {detector, matter, evidence} | `wall/guard.py` (B1) |
| POST /scrub | matter_id, practice, text | text, removed | `wall/scrub.py` (B3) |
| POST /judge | current, protected[], draft | verdict, matter, evidence | `wall/judge.py` (B2) |
| results/results.json (shared: `$WALL_RESULTS`, default `~/the-wall/results/results.json`, gitignored) | `wall.results.record()` | {detector: {eval_set: {caught, leaks, false_alarms, clean, n}}} | eval runners |

Run the API: `uv run uvicorn wall.server:app --port 8788` (8787 is taken on the demo machine by an unrelated proxy). Clients read the base URL from env `WALL_API_URL`, default `http://localhost:8788`.

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

### O-1 de-identification demo (added 14:58; pivot ruled by Daniel: narrow demo, O-1 framing, small immigration firms, River stays)

| Agent | Branch | Owns | Done when |
|---|---|---|---|
| C1 corpus | `c1-o1-corpus` | `fixtures/matters/o1-*/` | 3 synthetic O-1 beneficiaries with matter.json + petition documents |
| C2 pipeline | `c2-deid` | `wall/deid.py`, `deid/`, `tests/test_deid.py` | POST /deidentify and `deid/run.py in.jsonl out.jsonl` produce cleaned text + judge-verified residual report |
| C3 PII | `c3-pii` | `wall/pii.py`, `tests/test_pii.py` | `wall.pii.find()` catches generic + immigration identifiers with tests |
| C4 demo UI | `c4-demo-ui` | `demo/` | Before/after O-1 page at /demo calling /deidentify |
| C5 O-1 eval | `c5-o1-eval` | `evals/o1/` | Synthetic O-1 leak set scored for regex, carryover, prompt judge (+ River when ready) as eval set `o1_demo` |
| C6 pitch | `c6-pitch` | `docs/pitch/` | 2-minute script, slides, say/don't-say and Q&A for the O-1 framing |

| E1 redteam | `e1-redteam` | `redteam/` | Injection + evasion attacks reported honestly |
| E2 cost | `e2-cost` | `evals/cost/` | Measured cost per 1k judgments and latency, prompt vs River |
| E3 docs | `e3-docs` | `README.md`, `docs/ARCHITECTURE.md` | Repo reads like a product in 60 seconds |
| E4 review | `e4-review` | nothing (read-only) | Blocker/major findings on main and lane branches |
| E5 O-1 wall | `e5-o1-wall` | `walls/o1/` | O-1 beneficiaries walled in GBrain + O-1 attack script |
| E6 stats | `e6-stats` | `evals/stats.py`, `tests/test_stats.py` | 95% Wilson intervals for every results row |
| D1 integration | `d1-integration` | `scripts/`, `tests/test_e2e.py` | One-command demo + preflight + e2e tests |

C4 (front-end) also owns `scoreboard/` from 15:05.

Interfaces: `wall.pii.find(text) -> list[Span(start, end, kind)]`; `POST /deidentify` (DeidentifyRequest -> DeidentifyResponse in `wall/contract.py`).
`o1_demo` numbers are self-written: never the headline. The headline stays the held-out hard set.

## Cross-branch handoffs

- **GBrain (live)**: server `http://localhost:3131/mcp`; one credentials file per matter at
  `/Users/dqi26/.superset/projects/The-Wall/.runtime/clients/<matter_id>.json`
  (`{"url", "client_id", "client_secret", "source_id"}`). The GBrain server is owned by a separate
  session: never run gbrain CLI commands or restart it; ask the coordinator. Agents never run as local
  trusted callers.
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
