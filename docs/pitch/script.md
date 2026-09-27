# Pitch script — O-1 de-identification (2:00)

Every line below must be checkable against a source (ABA 512, a citation in `docs/PRD.md`) or a
number that is on screen when it's said. Fill blanks from `/Users/dqi26/the-wall/results/results.json`
right before the talk — never state a number that isn't in that file.

Delivery note: the room is largely founders and engineers, a lot of whom have filed for or thought
about an O-1. Use that once, lightly, in the opener — never as a joke at their expense.

---

## 0:00–0:20 — The problem

**On screen:** title slide, ABA 512 citation.

> "A few of you in this room have an O-1 petition sitting somewhere — extraordinary ability,
> the visa a lot of founders end up filing for. Every one of those petitions is built entirely
> out of one person's identity: their name, their employer, their salary, their awards, their
> press.
>
> A small immigration firm that's won twenty of these has real know-how in that stack of
> petitions. But ABA Formal Opinion 512 says a self-learning tool that lets one client's facts
> surface in another client's file needs specific informed consent — boilerplate in an
> engagement letter isn't enough. So today the standard advice is: don't train on client
> matters at all. Firms stay safe with AI that forgets.
>
> We built AI that can learn from the firm's past petitions without carrying any one
> beneficiary's identity into the next one."

## 0:20–0:40 — The wall holds

**On screen:** terminal running `uv run python walls/attack.py` live.

> "Before we even get to training data: a matter agent is scoped to one matter. Here it asks
> for another matter's file directly, and asks for `__all__` sources — and it's refused."

Let the script run; it prints PASS/FAIL per check and a final `WALL HOLDS: n/n checks PASS` line.
Say the line only if it holds live; if it doesn't, skip straight to the recording (see Backup).

> "That's the base layer everything else sits on. Now the new piece."

## 0:40–1:10 — Live de-identification

**On screen:** browser at `/demo`, calling `POST /deidentify`.

> "This is a synthetic O-1 draft — not a real client, never will be. Watch what comes out the
> other side."

Paste the prepared synthetic paragraph, click de-identify.

> "Name, employer, salary, award year, A-number — gone, replaced with typed placeholders. A
> lawyer can still read the argument. That's what goes into training.
>
> Here's the part regex can't do: [point to the flagged residual span]. There's no name and no
> number left in that sentence — it's a *description* specific enough to re-identify the
> beneficiary anyway. Regex has no pattern for that. Our judge reads it as a paraphrase of an
> identity and flags it. That's the difference between pattern-matching and a trained reader."

## 1:10–1:40 — The honest scoreboard

**On screen:** scoreboard page, hard held-out set, n stated.

> "Here's the number that matters, and it's not from O-1 petitions — it's from a held-out set
> of 102 paraphrased leaks across held-out legal drafts, synonyms the detectors never saw in
> training. Pattern matching — regex — catches 0 of 102. Our prompt-only judge catches __ of
> 102. The River-tuned judge, trained on synthetic data with zero real client facts, catches __
> of 102, at [n]% false alarms on 98 clean drafts.
>
> Every number on this screen is held-out. If a detector missed something, it's on this slide."

## 1:40–2:00 — Close

**On screen:** say/don't-say headline: "identifiers removed, residual leakage measured at X/n."

> "We're not claiming this makes anyone HIPAA-compliant or GDPR-compliant, and we're not
> calling the output legally 'de-identified' — the consent duties under 512 don't go away. What
> we're claiming is narrower and checkable: identifiers removed, residual risk measured on
> held-out data, every number stated with n. That's enough for a two-lawyer immigration
> practice to start compounding its own win rate instead of starting from zero on every O-1."

---

## Backup

Screen recording of `walls/attack.py` and the `/demo` de-identification pass, captured before the
talk, in case the live network or GBrain server is down. State on screen that it's a recording.

## Timing budget

| Beat | Start | Length |
|---|---|---|
| Problem | 0:00 | 20s |
| Wall attack | 0:20 | 20s |
| De-identification demo | 0:40 | 30s |
| Scoreboard | 1:10 | 30s |
| Close | 1:40 | 20s |
