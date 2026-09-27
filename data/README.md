# Data pack (not committed)

Drop these files here; `data/*` is gitignored.

| File | Size | Use |
|---|---|---|
| judge_train_v2.jsonl | 900 | River SFT |
| judge_eval_hard.jsonl | 200 | Headline eval (102 paraphrased leaks, 30 hard negatives, 68 clean) |
| judge_eval.jsonl | 200 | Sanity check only |
| demo_leak_cases.jsonl | 20 | Live demo cases, never the headline |
| blind.jsonl | 30 | Written by hand by Daniel in the room |

Daniel must not open judge_train_v2.jsonl or judge_eval_hard.jsonl.
