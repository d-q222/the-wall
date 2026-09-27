# Speaker notes — Daniel, live demo (2:00 + 3:00 versions)

Present from `/demo/present.html` (API on port 8788, served live). 6 slides:
1 problem, 2 wall live, 3 de-identify live, 4 numbers, 5 sponsors/built-on,
6 close. Advance with Right-arrow/Space, `#n` hash jumps, footer shows n/6.
Slides 2–4 are live: click the on-screen button, never paste into a
terminal. The numbers slide reads live from `/results/results.json` — say
the numbers ON THE SCREEN; the values below are correct as of ~16:05 PDT.
Re-check `results.json` before stage time. Every number stated with n.
Say/don't-say per `docs/pitch/claims.md`.

## Pre-talk checklist (5 min before)

1. Open `/demo/present.html`, confirm 6 slides, footer `1 / 6`.
2. Slide 2: click "Run the attack live", confirm refusal rows appear (no
   "GBrain did not answer"). Slide 3: click "De-identify", confirm
   placeholders + judge verdict appear (no "did not answer"). Re-click both
   buttons to reset to the pre-run state before the talk.
3. Slide 4: read the numbers and confirm they match Beat 4 below — regex
   hard 0/102; blind Claude 19/20, River 20/20, FA 1/20 each, n = 40;
   independent River 100/100 vs Claude 99/100, FA 12/100 vs 3/100.
4. Screen recording of both live runs captured in a background tab. Note its
   timestamp here: ____:____.

## Recovery lines (use verbatim if a live call fails)

- Wall button fails ("GBrain did not answer", or rows don't hold): "The
  live run isn't cooperating, so this is replayed from the last live run
  at <time> — same checks, same screen." Run `walls/attack.py` in a
  terminal, or cut to the recording.
- De-identify button fails: "The API is down, so this is replayed from the
  last live run at <time> — synthetic draft in, placeholders out, same as
  you see here." Cut to the recording.
- Any scoreboard doubt: "Every number on this screen is held-out, stated
  with n. If a detector missed something, it's on this slide."

## 2-minute version (the default)

### Slide 1 — Problem, 0:00–0:20

SCREEN: "Law firms can't let AI learn from past cases."

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

### Slide 2 — Wall holds, 0:20–0:40

CLICK: advance, then click "Run the attack live".
SCREEN: per-check rows; final row "Wall held n of n", GBrain.

Say:
"Before training data, the base layer. Chen's agent asks for another
client's file — and it's refused. Every refusal is written to the audit
log."
[Let it run. Say "Wall held" only with the exact n on screen; if it
doesn't hold live, use the recovery line and move on.]
"That's the base layer everything else sits on. Now the new piece."

### Slide 3 — Live de-identification, 0:40–1:10

CLICK: advance, then click "De-identify".
SCREEN: yellow identifiers become blue placeholders; underlined residual
span; verdict line with judge name.

Say:
"This is a synthetic O-1 draft. Not a real client, never will be. Watch
what comes out the other side."
[Click. Pause one beat.]
"Name, employer, salary, A-number. Gone, replaced with typed placeholders.
A lawyer can still read the argument. That's what goes into training.
Here's the part regex can't do. There's no name and no number left in that
underlined sentence. It's a description specific enough to re-identify the
beneficiary anyway. Regex has no pattern for that. Our judge reads it as a
paraphrase of an identity and flags it. That's the difference between
pattern-matching and a trained reader."

### Slide 4 — Numbers, 1:10–1:40

CLICK: advance. Point at each big number as you name it. Read the screen;
values below are as of 16:05.
SCREEN: three big numbers + note line (all rendered live from results.json).

Say:
"Here's the number that matters. Pattern matching catches 0 of 102
paraphrased leaks on the held-out hard set, n = 200 with 98 clean. On the
hand-written blind set — the stronger test, 20 leaks plus 20 clean, n =
40 — Claude catches 19 of 20 at 1 false alarm in 20, and our small
River-tuned model, which the firm owns, catches 20 of 20 at 1 false alarm
in 20. Pattern matching gets 12 of 20 there, because the blind set has
literal leaks too. One honest footnote, on the slide: on the larger
agent-written set the River model over-flags more, 12 false alarms in 100
clean against Claude's 3 — calibrating that is next."
[If any of these moved on screen, say what's on screen. The hard-set
caveat stands: it shares its generator with training, so familiar phrasing
helps.]

### Slide 5 — Built on, 1:40–1:50 (fast)

CLICK: advance. Don't linger; one breath per row, or cut to two rows.

Say:
"Built on four pieces. GBrain, the wall. River, the models the firm owns.
Memorable, the know-how after scrubbing. QM, a room per matter. Built by
forty-plus coding agents in parallel."

### Slide 6 — Close, 1:50–2:00

CLICK: advance. Leave it up through applause and Q&A.
SCREEN: "Compound the how. Wall the what." + repo URL.

Say:
"We're not claiming this makes anyone HIPAA-compliant or GDPR-compliant.
And we're not calling the output legally de-identified. The consent duties
under 512 don't go away. What we're claiming is narrower and checkable.
Identifiers removed, residual risk measured on held-out data, every number
stated with n. That's enough for a two-lawyer immigration practice to
start compounding its own win rate instead of starting from zero on
every O-1."

## 3-minute version (extra 60 seconds)

- Slide 1 (+15s): after "walls off the person" — "What compounds is how a
  strong O-1 case is built. Not whose case it is."
- Slide 3 (+20s): after the residual flag — "We strip identifiers. Name,
  employer, salary, exact award year, A-number, receipt and passport
  numbers. Not the argument structure, not the criteria mapping, not the
  legal reasoning."
- Slide 4 (+25s): cost line — "The prompt judge costs about a dollar
  thirty-four per thousand judgments, about a second and a half each,
  measured over 20 calls. River-judge cost isn't measured yet, and I'm
  telling you that instead of hiding it."

## Never say (claims.md, verbatim bans)

De-identified, anonymized, HIPAA-compliant, GDPR-compliant, "satisfies
512" / "512-compliant", "download the tuned model", "no client data ever
leaves the firm", "eliminates risk" / "guarantees privacy", any number
without n, or the headline as O-1 data. The hard-set caveat and the
River over-flagging sentence stay in — they are on the slide.

## 5 most likely judge questions (1-line answers; see docs/pitch/qa-drill.md)

1. What does the headline number actually mean? — Read the slide: regex
   0/102 hard; River model 100/100 vs Claude 99/100 on the independent set,
   n stated, all in `results.json`.
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
