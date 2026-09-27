# QA drill — 25 hardest judge questions

Numbers below were read from `/Users/dqi26/the-wall/results/results.json`
and `evals/cost/results.json` on main at **16:10 PDT** (final refresh).
Every answer is true of the repo on main; the proving file is named per
question. "**Not yet**" marks the honest gaps.

## The score

**1. What exactly does "102/102" mean?**
It means the River-tuned judge flagged all 102 paraphrased leaks in
`judge_eval_hard.jsonl` (n = 200: 102 leaks + 98 clean, 0/98 false alarms) —
currently in `results.json` under `river_judge.hard`. Cross-checks that
landed at 16:05: blind 20/20 (1/20 false alarms), independent 100/100
(12/100 false alarms — see Q6).
Proof: `/Users/dqi26/the-wall/results/results.json`, `evals/run_judges.py`.

**2. Is the hard set really held out, or did the model train on it?**
Held out by file (train = `judge_train_v2.jsonl`, 900 rows; eval =
`judge_eval_hard.jsonl`, 200 rows) with held-out synonyms — but both files
come from the same synthetic generator, so they share phrasing templates
(see Q3). Proof: `/Users/dqi26/the-wall/data/README.md`, `docs/PRD.md`
("Evaluation").

**3. What is the template-overlap caveat?**
Because train and hard sets share a generator, many hard drafts share
phrasing with training drafts (my 5-gram check: 99/200 hard drafts share
over half their 5-grams with training; the deck states 69/200 by its own
method) — so 102/102 partly reflects familiar templates, and the
hand-written blind set is the stronger test. Proof: `docs/pitch/slides.html`
(scoreboard note); verify with `evals/run_judges.py`.

**4. What does the blind set say?**
The hand-written blind file per `docs/BLIND_SET.md` has landed (40 rows:
20 LEAK / 20 CLEAN, flat `{current, protected[], draft, label}` format) and
is scored: River 20/20, prompt judge 19/20, base Qwen 19/20 (each 1/20
false alarms), regex 12/20, carryover 0/20. This is the number judges
should trust most — no generator overlap. Proof:
`/Users/dqi26/the-wall/data/blind.jsonl`, `/Users/dqi26/the-wall/results/results.json`,
`evals/check_blind.py`.

**5. The prompt-judge number moved (37 vs 59 of 102) — which is it?**
Both were true at different times: earlier runs scored ~37/102, current
`results.json` says 59/102 with 7/98 false alarms. The judge is a live LLM
call with no fixed seed, so re-runs vary; quote the current file with its
timestamp, and note `results/ci.json` is currently stale (no `river_judge`
entry). Proof: `/Users/dqi26/the-wall/results/results.json`,
`/Users/dqi26/the-wall/results/ci.json`, `wall/judge.py`.

**6. What are the false-alarm rates, and what is the target?**
Currently on hard (of 98 clean): regex 0, carryover 0, base Qwen 5,
prompt judge 7, River judge 0 — but on the independent set (of 100 clean)
River has 12 false alarms (12%, worst in any slice: 5/20 on immigration),
over the PRD target of at most 5%; say both numbers, not just hard.
Proof: `/Users/dqi26/the-wall/results/results.json`, `docs/PRD.md`
("Targets").
Proof: `/Users/dqi26/the-wall/results/results.json`, `docs/PRD.md`
("Targets").

**7. What does the base Qwen score, and why does it matter?**
Base (untuned) Qwen catches 39/102 at 5/98 false alarms, so the River-tuned
adapter's lift is 39 → 102 on the same set — the "tuned vs its own base"
comparison the PRD requires before claiming anything vs frontier.
Proof: `/Users/dqi26/the-wall/results/results.json`, `docs/PRD.md`
("Protocol"), `river/train.py` (base `Qwen/Qwen3.6-35B-A3B-FP8`).

## Scope honesty

**8. Is the 102-case headline O-1 data?**
No — the hard set is general synthetic legal-drafting leaks built before
the O-1 pivot; the O-1-specific `o1_demo` set is a self-written sanity
check, never the headline. Proof: `docs/pitch/claims.md`, `docs/CONTRACT.md`.

**9. What are the O-1 numbers?**
On `o1_demo` (n = 40: 20 leaks + 20 clean): regex 5/20, carryover 5/20,
prompt judge 14/20, River judge 20/20, all 0/20 false alarms. Five
independent slices also landed (formats, immigration, paraphrase,
adversarial, mixups; 20/20 each): judges catch ~all, regex only the
literal slices (2–16/20) and carryover near zero — but the independent
files live outside this worktree's data dir, so cite them as "recorded in
results.json" and let the coordinator confirm provenance.
Proof: `/Users/dqi26/the-wall/results/results.json`.

**10. What is the "standard" set, and why isn't it the headline?**
`judge_eval.jsonl` (n = 200) is a sanity check whose descriptive leaks are
templated — detectors can match the template rather than the leak — so it
never headlines. Proof: `docs/PRD.md` ("Evaluation"), `docs/CONTRACT.md`.

## Why not the obvious alternative

**11. Why not regex or Presidio?**
We do run a regex/fingerprint pass first (`wall/guard.py`) — it scores
79/97 on the templated standard set — but it catches 0/102 hard paraphrase
leaks because a paraphrased description has no fixed pattern to match; that
gap is exactly what the trained judge closes, reported side by side, not
instead. Proof: `wall/guard.py`, `docs/PRD.md`, `docs/pitch/claims.md`.

**12. What does the regex pass actually catch?**
Names, orgs, amounts in many formats via fingerprint patterns plus amount
re-phrasings ("$418,250" vs "418250"), and 6-gram carryover catches phrases
unique to one other matter; both miss paraphrase by design.
Proof: `wall/guard.py` (`regex_fingerprint_hits`, `carryover_hits`,
`NGRAM_N = 6`).

**13. What does the PII finder cover?**
`wall.pii.find()` returns spans in 12 kinds: name, org, email, phone, ssn,
a_number, receipt, passport, date, address, url, amount — generic plus
immigration identifiers (A-number, receipt/passport numbers).
Proof: `wall/pii.py` (`Span`, `find`), `tests/test_pii.py`.

## Models, weights, cost

**14. What are the two models in this story?**
The fallback judge is prompted Claude (`WALL_LLM_MODEL`, default
`claude-sonnet-5`) via the Anthropic SDK; the owned judge is Qwen
`Qwen3.6-35B-A3B-FP8` plus a LoRA adapter tuned with SFT on 900 synthetic
rows (600 original + 300 paraphrase/hard-negative). Proof: `wall/judge.py`,
`river/train.py`, `docs/PRD.md`.

**15. Where do the tuned weights live — can a firm download them?**
Served on River; the `river-client` SDK surface we use exposes sampling and
training calls, not an export/download call, so the adapter doesn't leave
River's infrastructure (re-check if River's terms change).
Proof: `docs/pitch/claims.md`, `river/train.py`, `evals/run_judges.py`.

**16. What does the judge cost vs Claude?**
Prompt judge: $1.34 per 1,000 judgments, p50 1.63s / p95 1.90s (n = 20,
claude-sonnet-5) — River-judge cost is **not yet** measured (no
deployment/sampling path priced on main), which closes when the coordinator
re-runs `evals/cost/measure.py` against the River endpoint.
Proof: `evals/cost/results.json`, `evals/cost/measure.py`.

**17. Did any real client data touch training?**
No — training is 900 synthetic rows with zero real client facts, and the
demo matters (Delmarva, Chen, Reyes; O-1 beneficiaries achterberg, umeh,
duarte) are synthetic fixtures; only draft text is sent to River/LLM APIs
at inference time. Proof: `docs/PRD.md` ("Non-goals"), `fixtures/matters/`,
`docs/pitch/claims.md`.

## Law and consent

**18. Does this satisfy ABA Formal Opinion 512?**
No — 512 requires specific informed consent for a self-learning tool
(boilerplate is not enough); de-identification reduces one measured risk
and never substitutes for consent. Proof: `docs/PRD.md`, `docs/pitch/claims.md`.

**19. Is the output "de-identified" / "anonymous" / HIPAA- or GDPR-compliant?**
We don't claim any of those: they are legal/regulatory statuses with tests
we haven't run (and HIPAA/GDPR don't govern a US immigration petition), so
we say "identifiers removed, residual leakage measured at X/102, n = 200."
Proof: `docs/pitch/claims.md`.

**20. Will my petition train your model?**
No draft trains anything by default: only a de-identified, judge-verified
procedure — never a specific petition — may be promoted into firm know-how
as a deliberate logged step, and the base judge trains once on synthetic
data, never retraining on a firm's petitions in use.
Proof: `docs/pitch/claims.md`, `docs/PRD.md` (skill-promotion gate).

## Failure modes

**21. What happens when the model is wrong and misses a leak?**
The miss is reported, not hidden — every number including misses goes on
the scoreboard — and at runtime the guard blocks and explains while flags
go to the attorney; the system never auto-paraphrases a draft to beat a
detector. Proof: `docs/PRD.md` ("Any result is reported", "Flags go to a
human"), `wall/deid.py` (residual report).

**22. What happens on a false alarm?**
The attorney reviews the flagged span (evidence is quoted in the verdict);
7/98 for the prompt judge is disclosed as over the 5% target, and the
River judge is currently 0/98 on the same set.
Proof: `wall/contract.py` (`JudgeResponse`: verdict, matter, evidence),
`/Users/dqi26/the-wall/results/results.json`.

**23. What do injection and evasion attacks show? — Not yet.**
The redteam lane (`redteam/`, injection + evasion attacks reported
honestly) has not landed on main, so adversarial robustness is unmeasured;
closes when E1 merges. Proof: `docs/CONTRACT.md` (E1 row); absence on main.

**24. Doesn't stripping identity gut the petition?**
No — the pipeline strips identifiers (name, employer, salary, exact award
year, A-number, receipt/passport numbers), not argument structure, criteria
mapping, or legal reasoning, per the per-practice policy (`may_compound`
vs `never_compounds`); what's left is what compounds across matters.
Proof: `fixtures/policy.json`, `docs/pitch/claims.md`, `wall/deid.py`.

**25. Why must the compounding policy vary — what's the asylum example?**
Under Matter of R-K-K- (BIA 2015) strikingly similar declarations across
unrelated applicants can support an adverse credibility finding, and in
Matter of V-S-A- (BIA 2026) DHS pointed at 12 boilerplate-hallmark
declarations and the Board reversed a grant — so in asylum no narrative
text ever compounds, while in litigation shared letter templates are a
firm asset. Proof: `docs/PRD.md`, `fixtures/policy.json` (asylum row).

## Open items for the coordinator (after 16:10)

- Confirm provenance of the five `indep_*` slices in `results.json` (source
  files not in this worktree's data dir).
- b2-river owes: why training state says n_examples=640 vs 900 rows in
  `judge_train_v2.jsonl` (holdout vs dropped rows).
- River-judge cost row still unmeasured (`evals/cost/results.json` says
  "not measured"); `results/ci.json` still has no `river_judge` entry.
- E1 redteam findings, if merged, supersede Q23.
