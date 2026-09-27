# Held-out O-1 de-identification eval

`uv run python -m evals.deid.run` scores four de-identifiers on the O-1 matters
the River de-identifier never saw in training (o1-halliday, o1-brandt,
o1-almeida from h17-o1-more, plus o1-duarte, which `river/deid/make_data.py`
also holds out). Each document is split into paragraphs, the unit the model was
trained on.

Detectors (rows in results.json, eval set `o1_deid_heldout`):

| detector | what it is |
|---|---|
| `deid_rules` | `wall.pii` regex/pattern candidates only, no matter fact sheet |
| `deid_rules_with_facts` | the same plus exact matches of the matter's fact strings. The ground truth *is* those strings, so recall is 100% by construction; it is the ceiling when an attorney has typed in every fact |
| `river_deid_base` | untuned Qwen/Qwen3.6-35B-A3B-FP8, same policy prompt |
| `river_deid_tuned` | the LoRA checkpoint from `river/deid/train.py` |

## Metric mapping onto `EvalResult`

- **Identifiers** = every occurrence of every string in the matter's
  `matter.json` facts (names, orgs, amounts, distinctive quasi-identifiers,
  A-/receipt/passport numbers) found in a paragraph.
- `leaks` = number of identifier occurrences; `caught` = those with at least 80%
  of their characters inside predicted spans. `caught/leaks` is identifier recall.
- `clean` = word tokens (`\w+`) that do not overlap any identifier;
  `false_alarms` = those a detector removed anyway. `false_alarms/clean` is the
  over-redaction rate.
- `n = leaks + clean`.

Caveat: the fact sheet is the only ground truth, so a detector that removes a
real identifier the fact sheet omits (a date, a city) is counted as
over-redacting.

## Results (2026-09-27, 82 held-out paragraphs, 4 matters)

| detector | identifiers removed | quasi-identifier phrases | over-redacted tokens |
|---|---|---|---|
| `deid_rules` | 88/123 | 0/5 | 115/2253 (5.1%) |
| `deid_rules_with_facts` | 123/123 (by construction) | 5/5 | 115/2253 (5.1%) |
| `river_deid_base` | 117/123 | 0/5 (1/5 on an earlier run; temperature-0 sampling was not fully deterministic) | 198/2253 (8.8%) |
| `river_deid_tuned` | 119/123 | 5/5 | 644/2253 (28.6%) |

"Quasi-identifier phrases" are the multi-word `distinctive` facts (n=5; too
small for strong claims). The tuned model's over-redaction is almost all
`quasi_identifier` spans: 38 spans that remove 517 non-fact tokens. Claude's
training labels mark whole clauses as quasi-identifying, and the model learned
those boundaries. A small part of the gap is policy kinds the fact sheet omits
(awards, publications: 56 tokens). The next training round should tighten
quasi-identifier span boundaries in the labels.

Training: 465 rows (1 dropped for invalid label JSON; 3,040 spans, every one an
exact substring), 59 steps x batch 8, LoRA rank 16, lr 1e-4, 997 s on River,
final loss 0.016. Sources: 440 Claude-written synthetic passages about invented
people plus paragraphs of o1-achterberg and o1-umeh only.
