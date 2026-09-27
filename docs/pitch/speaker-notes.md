# Speaker notes — Daniel, live demo (2:00 + 3:00 versions)

Present from `/demo/present.html` (API on port 8788, served live). 8 tabs:
Cover → Access wall → Review → Datasets → Model (optional) → Know-how →
Evaluation → Close. The built-in clock budgets 2:00 total; each tab shows
its own time. Keys: Right-arrow/Space = next tab, click a tab = jump,
`r` = run the embedded demo again, `f` = fullscreen, `h` = hide the clock.
Each embed auto-runs when its tab opens.

Numbers below read from `/Users/dqi26/the-wall/results/results.json` and
`evals/cost/results.json` at ~16:00 PDT. Re-check both files at 16:05; every
number is stated with n. Say/don't-say per `docs/pitch/claims.md`.

## Pre-talk checklist (5 min before)

1. Open `/demo/present.html`, confirm 8 tabs and clock `0:00 / 2:00`.
2. Click through all 8 tabs once; every embed must auto-run, none may show
   the "isn't being served" panel. Start the API first if any does.
3. Evaluation tab ledger matches `results.json` hard rows right now:
   regex 0/102 (0/98 FA), base Qwen 39/102 (5/98 FA), prompt judge 59/102
   (7/98 FA), River 102/102 (0/98 FA), n = 200 each.
4. Screen recording of the wall run + review pass captured in a background
   tab. Note its timestamp here: ____:____.
5. `f` for fullscreen, `h` to hide the clock before the audience sees it.

## Recovery lines (use verbatim if a live call fails)

- Any embed fails: "The live run isn't cooperating, so this is replayed
  from the last live run at <time> — same checks, same screen."
- Scoreboard doubt: "Every number on this screen is held-out, stated with
  n. If a detector missed something, it's on this slide."

## 2-minute version (the default — skip the Model tab)

### Tab 1 — Cover, 0:00–0:10

SCREEN: cover sheet, synthetic achterberg excerpt with highlighted
identifiers and one residual span.

Say:
"A few of you have an O-1 petition sitting somewhere. The visa a lot of
founders end up filing for. Every one of those petitions is built entirely
out of one person's identity. Name. Employer. Salary. Awards. Press.
A firm that's won twenty of these has real know-how in that stack. But ABA
Formal Opinion 512 says a self-learning tool that lets one client's facts
surface in another client's file needs specific informed consent.
Boilerplate isn't enough. So today the safe advice is: don't train on
client matters at all. Firms stay safe with AI that forgets. We built AI
that remembers the argument and walls off the person."

### Tab 2 — Access wall, 0:10–0:25

CLICK: next tab; the wall attack auto-runs. Press `r` if it stalls.
SCREEN: `/demo/wall.html` refusing a cross-matter request, refusals in the
audit log.

Say:
"The base layer, before training data. One matter's agent asks for another
matter's file — and the wall refuses. Every refusal is written to the
audit log."
RECOVERY: use the replay line, never claim a live pass you didn't get.

### Tab 3 — Review, 0:25–0:50

CLICK: next tab; the de-identification auto-runs on sample o1-achterberg.
SCREEN: identifiers become typed placeholders; the judge flags what is left.

Say:
"This is a synthetic O-1 exhibit. Not a real client, never will be. Watch
what comes out the other side. Name, employer, salary, A-number, receipt
number. Gone, replaced with typed placeholders. A lawyer can still read
the argument. That's what goes into training. Here's the part regex can't
do. There's no name and no number left in that sentence. It's a
description specific enough to re-identify the beneficiary anyway. Regex
has no pattern for that. Our judge reads it as a paraphrase of an identity
and flags it. That's the difference between pattern-matching and a trained
reader."

### Tab 4 — Datasets, 0:50–1:05 (fast)

CLICK: next tab.
SCREEN: batch de-identification; only judge-cleared exhibits enter the set.

Say:
"Past petitions become a training set one cleared exhibit at a time. Only
exhibits the judge clears go in. Anything flagged stays out."

### Tabs 5–6 — Model skipped, Know-how, 1:05–1:20

CLICK: skip Model (optional tab), land on Know-how.
SCREEN: a procedure learned on one matter, applied to another.

Say:
"What worked on one petition improves the next. The facts stay behind.
What compounds is how a strong O-1 case is built. Not whose case it is."

### Tab 7 — Evaluation, 1:20–1:50

CLICK: next tab. Point at each ledger row as you name it.
SCREEN: ledger table plus bars, caveat visible underneath.

Say:
"Here's the number that matters. And it's not from O-1 petitions. It's
from a held-out set of 102 paraphrased leaks across held-out legal drafts,
n = 200 with 98 clean. Synonyms the detectors never saw in training.
Regex catches 0 of 102. The base model catches 39 of 102 at 5 false alarms
in 98. Our prompt-only judge catches 59 of 102 at 7 false alarms in 98 —
that false-alarm rate is over our 5 percent target, and it's on the slide.
The River-tuned judge, trained on synthetic data with zero real client
facts, catches 102 of 102 at zero false alarms in 98. Every number on this
screen is held-out. If a detector missed something, it's on this slide.
One caveat, also on the slide: the hard set shares its generator with
training — 69 of 200 drafts share more than half their 8-grams — so this
is an easy test for a tuned model. The hand-written blind set, 40 cases,
is the stronger one, and no detector scores are reported on it yet."

### Tab 8 — Close, 1:50–2:00

CLICK: next tab. Leave it up through applause and Q&A.
SCREEN: "Compound the how. Wall the what."

Say:
"We're not claiming this makes anyone HIPAA-compliant or GDPR-compliant.
And we're not calling the output legally de-identified. The consent duties
under 512 don't go away. What we're claiming is narrower and checkable.
Identifiers removed, residual risk measured on held-out data, every number
stated with n. That's enough for a two-lawyer immigration practice to
start compounding its own win rate instead of starting from zero on
every O-1."

## 3-minute version (extra 60 seconds)

- Cover (+15s): after "walls off the person," point at the residual span in
  the excerpt — "That last highlighted line has no name and no number, and
  it still points to one person. Remember it; it comes back in Review."
- Include the Model tab (+20s): "Every correction an attorney makes teaches
  the firm's own model. Fixes become training examples, and the River model
  retrains on them."
- Evaluation (+25s), after the River number: cost line — "The prompt judge
  costs about a dollar thirty-four per thousand judgments, about a second
  and a half each, measured over 20 calls. River-judge cost isn't measured
  yet, and I'm telling you that instead of hiding it."

## Never say (claims.md, verbatim bans)

De-identified, anonymized, HIPAA-compliant, GDPR-compliant, "satisfies
512" / "512-compliant", "download the tuned model", "no client data ever
leaves the firm", "eliminates risk" / "guarantees privacy", any number
without n, or the 102-case headline as O-1 data.

## 5 most likely judge questions (1-line answers; see docs/pitch/qa-drill.md)

1. What does 102/102 actually mean? — River judge flagged all 102 held-out
   paraphrased leaks at 0/98 false alarms, n = 200, in `results.json`.
2. Is the hard set really held out? — Held out by file with held-out
   synonyms, but same generator as training, so familiar phrasing helps;
   the 40-case hand-written blind set is the stronger test.
3. Does this satisfy ABA 512? — No; 512 needs specific informed consent,
   and de-identification reduces one measured risk, never substitutes.
4. Why not just regex? — We run regex first, but it catches 0/102
   paraphrased leaks because paraphrase has no fixed pattern to match.
5. Will my petition train your model? — No; nothing trains by default, and
   only a de-identified, judge-verified procedure is ever promoted by a
   deliberate logged step.
