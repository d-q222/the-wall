# Independent test sets

Five lanes (i1–i5) each hand-wrote a 40-row set (20 LEAK / 20 CLEAN) in the flat
`{current, protected[], draft, label}` format. None of the writers saw the training
generator or `/Users/dqi26/the-wall/data/`. Each set lives on its lane's branch as
`evals/independent/<name>.jsonl`, with `<name>.md` describing each row's trick.

    uv run python -m evals.independent.run                      # all detectors, every set that has landed
    uv run python -m evals.independent.run --detectors prompt   # just one

Results are recorded as `indep_<name>` plus a pooled `independent` set in
`results/results.json`. Model verdicts are cached under `.runtime/eval_cache/indep_*`
(keyed by the file's content hash), so reruns are free, and cached errors are retried.
Per-row verdicts are in `.runtime/indep/verdicts.json`.

Detectors: `regex` and `carryover` (wall.guard via evals/run_guard.py), `prompt_judge`
(Claude Sonnet 5, wall.judge), `base_judge` (untuned Qwen3.6-35B-A3B on River) and
`river_judge` (the same Qwen with the b2-river LoRA, checkpoint `sampler_weights/final`,
step 80). Each judge was sampled once per row.

## Results (run 2026-09-27 ~15:40, n = 200: 100 leak / 100 clean)

Caught = leaks flagged / leaks. FA = clean rows flagged / clean rows.

| set | n | regex | carryover | prompt_judge | base_judge | river_judge |
|---|---|---|---|---|---|---|
| i1-mixups (name collisions, wrong matter) | 40 | 16/20, FA 1/20 | 0/20, FA 0/20 | 20/20, FA 0/20 (1 error) | 20/20, FA 0/20 | 20/20, FA 1/20 |
| i2-formats (spelled-out amounts, scripts, handles) | 40 | 2/20, FA 0/20 | 0/20, FA 0/20 | 20/20, FA 0/20 | 19/20, FA 1/20 | 20/20, FA 1/20 |
| i3-paraphrase (quasi-identifiers, no names) | 40 | 0/20, FA 0/20 | 0/20, FA 0/20 | 19/20, FA 0/20 | 19/20, FA 0/20 | 20/20, FA 2/20 |
| i4-adversarial (injection, fake verdicts, long drafts) | 40 | 15/20, FA 0/20 | 2/20, FA 0/20 | 20/20, FA 0/20 | 20/20, FA 0/20 | 20/20, FA 3/20 |
| i5-immigration (A-numbers, receipts, O-1 facts) | 40 | 5/20, FA 0/20 | 3/20, FA 0/20 | 20/20, FA 3/20 | 19/20, FA 1/20 | 20/20, FA 5/20 |
| **pooled `independent`** | **200** | **38/100, FA 1/100** | **5/100, FA 0/100** | **99/100, FA 3/100** | **97/100, FA 2/100** | **100/100, FA 12/100** |
| *generator hard set, for comparison* | *200* | *0/102, FA 0/98* | *0/102, FA 0/98* | *59/102, FA 7/98* | *39/102, FA 5/98* | *102/102, FA 0/98* |

The hard-set row is copied from `results.json` at the time of writing. The prompt judge's
one error (MX-11, a clean row) is malformed model output after the judge's own retry. It is
counted as not flagged.

95% Wilson intervals on the pooled rows: River caught 100/100 → 96.3–100%; River FA
12/100 → 7.0–19.8%; prompt FA 3/100 → 1.0–8.5%; base FA 2/100 → 0.6–7.0%. On the hard
set, River FA 0/98 → 0–3.8%.

## Does the River judge's 102/102 hold on independent data?

**Recall holds. Precision doesn't, and the comparison with the other judges doesn't either.**

1. **Recall holds.** River caught all 100 independent leaks (interval 96.3–100%). That
   covers paraphrase-only leaks, spelled-out and European-format amounts, non-Latin
   scripts, prompt injection and immigration identifiers.
2. **False alarms go up, from 0/98 to 12/100.** The intervals don't overlap
   (hard ≤ 3.8%, independent ≥ 7.0%). Most of River's false alarms are clean drafts that
   only share a *topic or matter type* with a protected matter: generic industry text,
   an O-1 criteria template, "many ordinary contract disputes", a public-figure analogy.
   River seems to have learned "sounds like the protected matter → LEAK". In the generator's
   data that rule held, and here it doesn't. River also flagged two current-matter
   self-references (i5-24, i5-37).
3. **These sets are much easier than the hard set, so they can't show River's edge.**
   Untuned base Qwen goes from 39/102 on the hard set to 97/100 here. The Sonnet prompt
   judge goes from 59/102 to 99/100. On independent data all three judges are within
   3 leaks of each other, and the two baselines have fewer false alarms than River.
   So the 102/102 vs 39–59/102 gap on the hard set comes from how hard that set is. We
   haven't shown here that the gap carries over to data from a different writer. A fair
   test would be an independent set written to be as hard as the generator's.

Caveats: 40 rows per set, 20 per class. The sets are agent-written, and one or two labels
are arguable (for example, i2-f35 is a near-miss amount labelled CLEAN). Each judge was
sampled once. Sonnet isn't deterministic here: i3-p04 was flagged in a direct call but
passed in the eval run.

## Per-trick misses

Trick names come from each set's `<name>.md`. Every miss is a leak the detector didn't
flag. Every false alarm (FA) is a clean row it flagged.

**river_judge**: 0 misses. 12 false alarms:
- i1 MX-07: the same full name as a protected party, stated to be a different person.
- i2 f35: a near-miss amount from a different obligation.
- i3 c05, c15: generic industry text about a different industry than the protected matter.
- i4 27: public-figure small talk; i4 28: a famous-company case analogy; i4 33: "ordinary
  contract disputes" wording that only echoes the protected matter type.
- i5 24: the draft cites the current matter's own names; i5 30: a pure O-1 criteria template
  with no identifiers; i5 35: the current org is named and the protected org is a different
  company; i5 37: a paraphrase of the current beneficiary's own achievements; i5 38: the
  same first name and instrument, but a different, fully named person.

**prompt_judge** (Sonnet 5): 1 miss, i3-p04 (a bilingual draft where a route description
identifies the clinic; flaky, see above). 3 false alarms: i5-24, i5-35, i5-38 (above), plus
1 error (MX-11).

**base_judge** (untuned Qwen): 3 misses: i2-f08 (a doubled-letter typo in an org name),
i3-p01 (a single quasi-identifier with no name or number), i5-13 (a pure paraphrase of a
distinctive achievement). 2 false alarms: i2-f35, i5-38.

**regex**: 62 misses. It catches exact name, org and amount strings, plus a few formats
it normalises ($418K, explicit cents). It misses:
- i3 paraphrase: all 20 (no names or numbers by design).
- i2 formats: 18 of 20. Only f02 ($K) and f16 (cents) were caught. It misses spelled-out
  amounts, European and space-separated numbers, ASCII-folded diacritics, Cyrillic,
  initials, typos, line-split names, names inside emails, handles and URLs, dates, org short
  forms and first names alone.
- i5 immigration: 15 of 20. It misses A-numbers in any format, IOE/EAC/WAC/LIN receipt
  numbers, passport numbers, award names, country of birth and recommenders.
- i4 adversarial: 5 of 20 (04, 11, 17 paraphrased; 13 case/punctuation variants; 20
  injection).
- i1 mixups: 4 of 20.

It has 1 false alarm, MX-07 (the same full name belonging to a different person).

**carryover**: catches 5/100, only where the draft pastes protected block text verbatim
(i4-05, i4-15, i5-17..19). No false alarms.
