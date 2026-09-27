# Speaker notes — Daniel, live demo (2:00 + 3:00 versions)

Numbers below read from `/Users/dqi26/the-wall/results/results.json` and
`evals/cost/results.json` at ~15:45 PDT. Re-check both files at 16:05; if any
number moved, the struck line in each beat tells you what to swap in.
Every number is stated with n. Say/don't-say per `docs/pitch/claims.md`.

Presenter setup note: there is no `demo/present.html`. Present from
`docs/pitch/slides.html` (open the file directly in the browser, 6 slides,
Right-arrow/Space advances, click right-half = next, `#n` hash jumps),
plus one terminal and one `/demo` browser tab. Order of tabs left to right:
slides, terminal, `/demo`.

## Pre-talk checklist (5 min before)

1. Open `docs/pitch/slides.html`, confirm 6 slides and footer `1 / 6`.
2. Terminal ready: `uv run python walls/attack.py` typed but not run.
3. `/demo` tab loaded; prepared synthetic O-1 paragraph pasted into the
   de-identify box but not submitted.
4. Screen recording of the attack run + the de-identification pass captured
   and open in a background tab. Note its timestamp here: ____:____.
5. Scoreboard slide (slide 5) matches `results.json` hard rows right now:
   regex 0/102 (0/98 FA), base Qwen 39/102 (5/98 FA), prompt judge 59/102
   (7/98 FA), River 102/102 (0/98 FA), n = 200 each.

## Recovery lines (use verbatim if a live call fails)

- Attack script fails: "The live run isn't cooperating, so this is replayed
  from the last live run at <time> — same checks, same screen."
- De-identify call fails: "The API is down, so this is replayed from the
  last live run at <time> — synthetic draft in, placeholders out, same as
  you see here."
- Scoreboard doubt: "Every number on this screen is held-out, stated with
  n. If a detector missed something, it's on this slide."

## 2-minute version (the default)

### Beat 1 — Problem, 0:00–0:20 (slide 1 → slide 2)

CLICK: advance to slide 2 on "ABA Formal Opinion 512".
SCREEN: problem slide, both panels visible.

Say:
"A few of you have an O-1 petition sitting somewhere. The visa a lot of
founders end up filing for. Every one of those petitions is built entirely
out of one person's identity. Name. Employer. Salary. Awards. Press.
A firm that's won twenty of these has real know-how in that stack. But ABA
Formal Opinion 512 says a self-learning tool that lets one client's facts
surface in another client's file needs specific informed consent.
Boilerplate in an engagement letter isn't enough. So today the safe advice
is: don't train on client matters at all. Firms stay safe with AI that
forgets. We built AI that learns from past petitions without carrying any
one beneficiary's identity into the next one."

### Beat 2 — Wall holds, 0:20–0:40 (slide 3 + terminal)

CLICK: advance to slide 3, then run `uv run python walls/attack.py` live.
SCREEN: terminal PASS lines, final `WALL HOLDS` line.

Say:
"Before training data, the base layer. A matter agent is scoped to one
matter. Here it asks for another matter's file directly, and asks for all
sources — and it's refused."
[Let it run. Read the final line only if it passes live.]
"That's the base layer everything else sits on. Now the new piece."
RECOVERY: use attack-script line above, then move on. Never claim a live
pass you didn't get.

### Beat 3 — Live de-identification, 0:40–1:10 (slide 4 + /demo tab)

CLICK: advance to slide 4, switch to `/demo`, click de-identify.
SCREEN: placeholders out, one residual span flagged.

Say:
"This is a synthetic O-1 draft. Not a real client, never will be. Watch
what comes out the other side."
[Click. Pause one beat.]
"Name, employer, salary, award year, A-number. Gone, replaced with typed
placeholders. A lawyer can still read the argument. That's what goes into
training. Here's the part regex can't do. There's no name and no number
left in that sentence. It's a description specific enough to re-identify
the beneficiary anyway. Regex has no pattern for that. Our judge reads it
as a paraphrase of an identity and flags it. That's the difference between
pattern-matching and a trained reader."

### Beat 4 — Scoreboard, 1:10–1:40 (slide 5)

CLICK: advance to slide 5. Point at each row as you name it.
SCREEN: four-row table, n = 200 note visible.

Say:
"Here's the number that matters. And it's not from O-1 petitions. It's
from a held-out set of 102 paraphrased leaks across held-out legal drafts,
n = 200 with 98 clean. Synonyms the detectors never saw in training.
Pattern matching, regex, catches 0 of 102. The base model catches 39 of
102 at 5 false alarms in 98. Our prompt-only judge catches 59 of 102 at
7 false alarms in 98 — that false-alarm rate is over our 5 percent target,
and it's on the slide. The River-tuned judge, trained on synthetic data
with zero real client facts, catches 102 of 102 at zero false alarms in
98. Every number on this screen is held-out. If a detector missed
something, it's on this slide. One caveat, also on the slide: the hard set
shares its generator with training, so familiar phrasing helps. The
hand-written blind set, 40 cases, is the stronger test — no detector
scores on it yet."

### Beat 5 — Close, 1:40–2:00 (slide 6)

CLICK: advance to slide 6. Leave it up through applause/Q&A.
SCREEN: say/don't-say headline.

Say:
"We're not claiming this makes anyone HIPAA-compliant or GDPR-compliant.
And we're not calling the output legally de-identified. The consent duties
under 512 don't go away. What we're claiming is narrower and checkable.
Identifiers removed, residual risk measured on held-out data, every number
stated with n. That's enough for a two-lawyer immigration practice to
start compounding its own win rate instead of starting from zero on
every O-1."

## 3-minute version (extra 60 seconds)

Add 20 seconds to Beat 3, 20 to Beat 4, 20 to Beat 1. Insert exactly:

- Beat 1, after "starting from zero": one line on compounding — "What
  compounds is how a strong O-1 case is built. Not whose case it is."
- Beat 3, after the residual flag: "We strip identifiers. Name, employer,
  salary, exact award year, A-number, receipt and passport numbers. Not the
  argument structure, not the criteria mapping, not the legal reasoning."
- Beat 4, after the River number: cost line — "The prompt judge costs about
  a dollar thirty-four per thousand judgments, about a second and a half
  each, measured over 20 calls. River-judge cost isn't measured yet, and
  I'm telling you that instead of hiding it."

## Never say (claims.md, verbatim bans)

De-identified, anonymized, HIPAA-compliant, GDPR-compliant, "satisfies
512" / "512-compliant", "download the tuned model", "no client data ever
leaves the firm", "eliminates risk" / "guarantees privacy", any number
without n, or the 102-case headline as O-1 data.

## 5 most likely judge questions (1-line answers)

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
