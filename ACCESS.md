# Ethical Wall Brain: access + setup checklist

Everything below was verified on 2026-09-27 unless marked UNVERIFIED.
This pack contains data only. Write all code in the room.

## Tonight (do these, in order)

### 1. GBrain (verified: v0.59 installs and walls hold)
```sh
bun install -g github:garrytan/gbrain      # NOT npm: the npm "gbrain" is unrelated
gbrain init --pglite --no-embedding
```
Gotchas found in testing:
- Each matter folder must be a git repo with a commit before `sources add`.
- `gbrain sync --source <id>` needs `--no-pull`.
- Add matters with `--no-federated` so they are isolated.
- Run `gbrain serve --http` with `setsid nohup ... &` or it dies with the shell.
- Local `__all__` search sees every matter. Matter agents MUST connect remotely
  with their own client:
  `gbrain auth register-client matter-b-agent --scopes read --source mb --federated-read mb`
- Dream cycle: always pass `--source <matter>`.

### 2. River (verified: SDK installs; access UNVERIFIED)
```sh
pip install river-client          # Python 3.12+
python -m river_client.skill --install   # gives your coding agents River's own training skill
```
- Get an API key from the River team tonight. Run one tiny `client.sample(...)` to confirm.
- Data is chat `messages` format. Convert with
  `get_renderer("Qwen/Qwen3.6-35B-A3B-FP8").build_training_example(messages, train_on=TrainOnWhat.LAST_ASSISTANT).to_dict()`.
- Ask at opening: can the adapter be exported to run locally, or only served on River?

River data in `river/`:
- `judge_train.jsonl`: 600 examples (333 LEAK / 267 CLEAN), 40 synthetic matters.
- `judge_eval.jsonl`: 200 examples on 15 held-out matters with names and firms that never
  appear in training. Validated: 0 mislabeled leaks.
- Leak types: full name, partial name, org, amount (many formats), descriptive, combo.
  CLEAN includes drafts that cite the CURRENT matter's own facts (the hard negative).

### 3. Memorable (verified: `memorable-cli` 0.5.30 installs)
```sh
npm i -g memorable-cli     # NOT pip "memorable-ai", which is unrelated
memorable init gbrain      # or `memorable init` standalone
memorable enable
gbrain config set integrations.memorable.enabled true   # human accepts disclosure
```
- Your agent is not Claude Code/Codex, so use `memorable ingest -` with a JSON trace.
  Example: `demo/memorable_trace_scrubbed.json`.
- Traces that only read/search are refused. Include a write step.
- PITCH POINT: Memorable's redaction targets vendor keys and high-entropy strings.
  Client names are neither. Your scrubber runs BEFORE `memorable ingest`.

### 4. QM (UNVERIFIED; deploys to your own cloud account)
Decide tonight: deploy it, or cut it and show two panes labeled by matter.

## Parallel agents in the room (Superset worktrees)

Agree on one interface first (5 min), then launch in parallel:

| Agent | Builds | Depends on |
|---|---|---|
| A: wall | 3 isolated sources, scoped clients, server, attack script | nothing |
| B: guard | regex fingerprint guard + scrubber; score `demo/demo_leak_cases.jsonl` | matters/ |
| C: river | render data, launch SFT by 2:00, eval on `judge_eval.jsonl` | River key |
| D: agent + UI | matter agent drafts via scoped MCP; scoreboard page | A's endpoint |

You review and integrate. Budget 30 min for integration; it is always longer than you think.

## Demo targets (what the scoreboard should show)
- Wall: matter-B client gets `permission_denied` on matter A.
- Guard: on the 200 HELD-OUT eval examples (never used for tuning), regex catches 79/97 leaks (81%),
  0/12 descriptive leaks, 1/103 false alarms. Quote these, not the 14/15 on self-written demo cases.
- Judge: must beat regex on descriptive leaks. Report its held-out number whatever it is.

## Eval protocol (use v2 data)
- Train on `river/judge_train_v2.jsonl` (900: original 600 + 300 paraphrase/hard-negative).
- `judge_eval.jsonl` is EASY: its "descriptive" leaks copy exact role words, so a one-line
  string match scores 12/12. Use it only as a sanity check. Never quote it as the headline.
- `judge_eval_hard.jsonl` is the headline: 102 paraphrased leaks using synonyms that never
  appear in training, 30 hard negatives, 68 other clean drafts.
  Baselines measured: regex 0/102 on paraphrase, string match 0/102, both 98/98 on clean.
- Blind set: a teammate who has NOT read the training data writes 30 leak/clean drafts in
  the room. Report it separately. This is the number judges will trust most.
- Compare three judges on the hard set: base Qwen (no tuning), River-tuned Qwen, frontier prompt.
  The River claim is "tuned small owned model vs its own base, at what cost vs frontier",
  not "beats frontier" unless it actually does.
- Guard rule learned in testing: ALWAYS exclude the current matter's own amounts and names
  before flagging. Skipping this caused 12/30 false alarms in a quick baseline.
- River judge: accuracy on the 200 held-out eval examples vs the prompt-only baseline.
