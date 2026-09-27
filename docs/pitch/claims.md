# Say / don't say — O-1 de-identification

Every claim here must be checkable against a source (ABA 512, `docs/PRD.md`, a citation) or a
number stated with n on a screen. If a number isn't measured yet, say so or don't say it — never
round up a blank.

## Say / don't say

| Say | Don't say | Why |
|---|---|---|
| "Removes identifiers, with residual leakage measured at **__/__** on held-out data" | "De-identified" (as a legal status), "anonymized" | De-identification and anonymization are defined legal/regulatory terms (HIPAA safe harbor, GDPR Art. 4(5)/Recital 26) with tests we haven't run against. We measure a residual-leakage rate; we don't claim the legal status. |
| "Not HIPAA-compliant, not GDPR-compliant — not what this measures" | "HIPAA-compliant," "GDPR-compliant" | Neither statute governs a US immigration petition; naming them at all implies a compliance claim we have not tested and that doesn't apply to this data. |
| "Consent duties under ABA 512 remain" | "This satisfies 512" / "makes the firm 512-compliant" | 512 requires specific informed consent for a self-learning tool; de-identification reduces one measured risk, it doesn't substitute for consent. |
| "The headline number — 0/102, __/102 — is from held-out **legal drafts**, not O-1 petitions" | Implying the 102-case headline is O-1 data | The hard held-out set (`judge_eval_hard.jsonl`) is synthetic legal-drafting leaks across matters in general, built before the O-1 pivot. The O-1-specific eval (`o1_demo`, self-written) is a sanity check, never the headline — see `docs/CONTRACT.md`. |
| "Weights are served on River; not exported to run locally" | "You can download the tuned model" | Verified against the `river-client` SDK surface (sampling and training calls only, no export/download call) as of today. |
| "Trained on synthetic petitions; no real client data, ever" | "No client data ever leaves the firm" | Inference calls to River or the LLM API do send the draft text at query time; the training set itself has zero real client facts. |
| "Reduces a measured cross-client leak risk" | "Eliminates the risk" / "guarantees privacy" | We report a rate with n, not zero. |
| "On n = 102 held-out cases" (always state n) | Any number without n | A rate with no denominator is not checkable. |

## Q&A prep

**Will my petition train your model?**
No draft trains anything by default. Only a de-identified, judge-verified procedure — never a
specific petition — is eligible to be promoted into the firm's shared know-how, and that promotion
is a deliberate, logged step, not automatic on every draft. The base leak-detection judge is
trained once, up front, on synthetic O-1 data with zero real client facts; it does not retrain on
a firm's petitions during use.

**Doesn't stripping identity gut the petition?**
No — we strip identifiers (name, employer, salary, exact award year, A-number, receipt/passport
number), not the argument structure, the criteria mapping, or the legal reasoning. What's left is
exactly what compounds across matters: how a strong O-1 case is built, not whose case it is. See
`fixtures/policy.json` → `immigration.may_compound` vs `never_compounds`.

**Why not just use regex or Presidio?**
We do run a regex/fingerprint pass first — it's fast and catches the literal cases (names, IDs,
amounts in known formats). On the held-out hard set it catches 0/102 paraphrased leaks, because a
paraphrased description ("the founder of the delivery startup that raised its Series A last year")
has no fixed pattern to match. That's exactly the gap a trained judge is built to close; we report
its held-out number next to regex's, not instead of it.

**Where do the weights live?**
Served on River; the SDK we use exposes sampling and training calls, not an export or download
call, so the tuned adapter doesn't leave River's infrastructure. Verified against the
`river-client` SDK as of today; if River's terms change, this line changes with them.
