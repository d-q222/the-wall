# De-identification bakeoff (lane m1)

"Can we get the models to use whatever works best?" This picks the de-identification
strategy by measurement, not by taste.

    uv run python -m evals.bakeoff.run            # all detectors; model calls cached in .runtime/bakeoff/
    uv run python -m evals.bakeoff.run --skip claude,river_tuned

Output: `/Users/dqi26/the-wall/.runtime/deid_strategy.json` (`detectors`, `chosen`, `chosen_at`,
`rule`, `metrics` for every candidate). `wall.deid_strategy.load()` returns the chosen list
(default `["facts", "rules"]` if the file is missing). `wall.deid_strategy.detect(text, practice, matter_id)`
runs the chosen detectors and returns merged, non-overlapping spans. A detector that fails at
run time (no key, River down) is skipped, so the free detectors always run.

## Eval set and scorer

The split and scorer are k3's (`evals/deid/run.py`), reused unchanged. Held-out matters are
o1-halliday, o1-brandt, o1-almeida and o1-duarte: **82 paragraphs, 123 identifier
occurrences, 5 quasi-identifier phrase occurrences and 2,253 non-identifier word tokens**.
An identifier counts as removed when at least 80% of its characters are covered.
Over-redaction is the share of non-identifier tokens that were removed.

**Selection condition.** The answer key is the matter fact sheets. The `facts` detector *is*
that key, so if it can see the paragraph's own sheet it scores 123/123 by construction. The
selection therefore scores `facts` **blind to the paragraph's own matter**: it only knows the
other matters' sheets, as it would for a new document whose identifiers are not listed yet.
The "own sheet known" numbers are also in the JSON under `metrics_own_fact_sheet_known`.

## Results (unseen condition, n = 82 paragraphs)

| Candidate | Identifiers removed | Quasi phrases | Over-redaction | Latency / para | Cost / 1k paras |
|---|---|---|---|---|---|
| facts (other matters' sheets) | 4/123 (3%) | 0/5 | 0/2253 (0.0%) | <0.1 ms | $0 |
| rules (`wall.pii`) | 88/123 (72%) | 0/5 | 117/2253 (5.2%) | <0.1 ms | $0 |
| claude (claude-sonnet-5, k3 prompt) | 119/123 (97%) | 5/5 | 644/2253 (28.6%) | 3,768 ms | $4.42 |
| river_base (Qwen3.6-35B-A3B, untuned) | 118/123 (96%) | 0/5 | 202/2253 (9.0%) | 246 ms* | not priced |
| river_tuned (k3 LoRA, step 20) | 121/123 (98%) | 3/5 | 639/2253 (28.4%) | 220 ms* | not priced |
| rules+facts | 92/123 (75%) | 0/5 | 117/2253 (5.2%) | <0.1 ms | $0 |
| rules+facts+river_base | 118/123 (96%) | 0/5 | 274/2253 (12.2%) | 246 ms* | not priced |
| rules+facts+claude | 123/123 (100%) | 5/5 | 727/2253 (32.3%) | 3,768 ms | $4.42 |
| rules+facts+river (tuned) | 121/123 (98%) | 3/5 | 681/2253 (30.2%) | 220 ms* | not priced |
| rules+facts+river+claude | 123/123 (100%) | 5/5 | 874/2253 (38.8%) | 3,988 ms | not priced |

\* River runs all 82 paragraphs in one batched session. Latency is total wall time divided by 82.
Claude is called once per paragraph, 8 at a time. River cost is "not priced" because River
billing is not exposed to us, so no number is invented.

Own fact sheet known: `facts` scores 123/123 with 5/5 quasi phrases and 0/2253 over-redaction,
and `rules+facts` scores the same recall with 117/2253 over-redaction.

## Chosen strategy

**Rule:** maximise identifier recall subject to over-redaction ≤ `WALL_DEID_MAX_OVERREDACT`
(default 0.10); break ties on quasi recall, then latency.

**Winner: `river_base`** (118/123, 9.0% over-redaction). `facts` is always kept as a floor
because it is free and removed 0 clean tokens in every condition. The written strategy is
**`["facts", "river_base"]`**. On documents whose fact sheet exists, that floor restores
123/123.

Claude and the tuned River model both find more (119 and 121 of 123, and they are the only
ones that catch the paraphrased quasi-identifiers). Both break the 10% cap: they remove about
28% of the tokens the key calls clean.

## Caveat: the answer key undercounts what the policy asks to remove

The key is the matter fact sheets: names, IDs, employers and some distinctive phrases.
The firm policy that Claude and the River de-identifier follow (`fixtures/policy.json`,
k3's prompt) also removes award names, years, press outlets and locations, which the sheets
do not list. Much of the measured "over-redaction" for claude and river_tuned is therefore
policy-correct removal that this key counts as a false alarm. The 10% cap favours
detectors that stay close to the fact sheets. If the firm wants policy-level redaction,
raise `WALL_DEID_MAX_OVERREDACT` (at 0.35, `rules+facts+claude` wins with 123/123 and 5/5)
or label a policy-level answer key. Only 5 quasi-phrase occurrences exist, so quasi recall
is a weak signal.

Presidio + spaCy (candidate c) was not run, to make the 16:05 deadline.
