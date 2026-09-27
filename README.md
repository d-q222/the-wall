# The Wall — Ethical Wall Brain

**O-1 de-identification for small immigration firms: train on your firm's petitions without training on your clients.**

Agent memory for small law firms that compounds the firm's know-how across matters while walling off every client's facts — *compound the how, wall the what.* Built in one afternoon at the *Own Your Intelligence* hackathon (Sept 27, 2026).

## What it does

- **A wall per client.** Every matter gets its own isolated GBrain source. A matter's agent connects with a scoped OAuth client that can read only its own source — never a local trusted caller — and [`walls/attack.py`](walls/attack.py) runs a live cross-matter attack that prints `permission_denied`. ([`walls/client.py`](walls/client.py), [`walls/README.md`](walls/README.md))
- **De-identify, then verify.** `POST /deidentify` detects a petition draft's identifiers — beneficiary name, employer, salary, award years, A-number, receipt/passport number, plus generic PII ([`wall/pii.py`](wall/pii.py)) — replaces each with a typed placeholder (`[NAME]`, `[ORG]`, `[AMOUNT]`, …), then a judge reads what's left for a *paraphrased* description that could still re-identify the beneficiary. ([`wall/deid.py`](wall/deid.py), [`wall/judge.py`](wall/judge.py), contract in [`wall/contract.py`](wall/contract.py))
- **Policy per practice area.** Every matter carries a practice tag ([`fixtures/policy.json`](fixtures/policy.json)) that sets what may compound — procedures, checklists, research — against what never does: beneficiary identity, employer, salary, strategy, witness or recommender details. [`wall/scrub.py`](wall/scrub.py) enforces the policy before a procedure can be shared, and the scrubbed trace is what reaches Memorable ([`memorable/ingest.sh`](memorable/ingest.sh)).

Full request path and de-identification pipeline: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## 60-second quickstart

```sh
uv sync
uv run pytest -q
scripts/demo.sh
```

`scripts/demo.sh` checks GBrain, starts the API on `:8788`, and serves everything from one origin (Ctrl-C stops just the API; GBrain is left running). Then open:

| URL | What |
|---|---|
| `http://localhost:8788/demo/wall.html` | Live wall attack, two rooms side by side |
| `http://localhost:8788/demo/compound.html` | A procedure learned on one matter improving another, facts stripped |
| `http://localhost:8788/demo/policy.html`, `/demo/audit.html`, `/demo/training.html` | Practice-policy editor, audit log, attorney-correction/retrain loop |
| `http://localhost:8788/scoreboard/` | Leak-detection scoreboard, reads `results/results.json` live |
| `http://localhost:8788/results/results.json` | Raw numbers behind the scoreboard |

Live wall attack from a terminal (prints `permission_denied` for a cross-matter read):

```sh
uv run python walls/attack.py
```

## The numbers

Headline is the **hard** held-out set (`judge_eval_hard.jsonl`, n=200: 102 paraphrased leaks with synonyms never seen in training, 98 clean drafts) — the set where naive pattern matching is known to score 0/102. The **independent** set (n=80, written by teammates who never opened the training data, across formats/paraphrase/adversarial/immigration cases) is the number to trust most. All figures are read live from `results/results.json`; blanks are eval sets not yet run.

| Detector | Eval set | Leaks caught | False alarms | n |
|---|---|---|---|---|
| Regex fingerprint | hard | 0/102 | 0/98 | 200 |
| Carryover (6-gram) | hard | 0/102 | 0/98 | 200 |
| Prompt judge (frontier, no tuning) | hard | 59/102 | 7/98 | 200 |
| Base Qwen (no tuning) | hard | 39/102 | 5/98 | 200 |
| **River-tuned judge** | hard | **102/102** | **0/98** | 200 |
| Regex fingerprint | independent (written by teammates blind to training data, most trusted) | 7/40 | 0/40 | 80 |
| Carryover (6-gram) | independent | 3/40 | 0/40 | 80 |
| Base Qwen (no tuning) | independent | 38/40 | 2/40 | 80 |
| Prompt judge (frontier, no tuning) | independent | 40/40 | 3/40 | 80 |
| **River-tuned judge** | independent | **40/40** | 6/40 | 80 |
| Regex fingerprint | `o1_demo` (self-written, never the headline) | 5/20 | 0/20 | 40 |
| Carryover (6-gram) | `o1_demo` (self-written, never the headline) | 5/20 | 0/20 | 40 |
| Regex / carryover | standard (`judge_eval.jsonl`, sanity check only) | — | — | — |
| All detectors | blind (Daniel's hand-written set, `data/blind.jsonl`) | — | — | — |

Cost (n=20, live `claude-sonnet-5` calls): prompt judge runs **$1.34 per 1,000 judgments**, p50 latency 1.6s. River judge cost is not yet measured — no deployment/pricing path confirmed as of this run. Method and caveats: [`evals/cost/README.md`](evals/cost/README.md).

## Hosts

| Host | Job in this product | Where |
|---|---|---|
| **GBrain** | The wall — one isolated source per matter, a scoped read-only OAuth client per matter agent | `walls/` |
| **River** | Owned leak judge — base Qwen plus a LoRA checkpoint SFT-tuned on synthetic leak/clean examples with zero real client data | `river/`, `evals/run_judges.py` |
| **Memorable** | Procedural memory — ingests a scrubbed session trace so a procedure (not a fact) becomes firm know-how | `memorable/` |
| **QM** | Room-per-matter, scoped skill promotion — scoped out of this build; the wall and web demo carry that story instead | `docs/PRD.md` |

## What this is not

- **Not a compliance guarantee.** It reduces one measured cross-client leak risk. Consent duties under ABA Formal Opinion 512 remain.
- **Not HIPAA or GDPR anonymization.** We measure a residual-leakage rate on held-out data with n stated; we don't claim the legal status of "de-identified" or "anonymized" data under either regime, and neither statute governs a US immigration petition.
- **Weights are served on River, not exported.** The `river-client` SDK we use exposes sampling and training calls, not an export or download call, so the tuned adapter doesn't leave River's infrastructure.
- **Never auto-paraphrases a draft to beat a detector.** A flag sends the lawyer back to the client's own account; the system does not rewrite text.

More: pitch script, slides, and the full say/don't-say table in [`docs/pitch/`](docs/pitch/); product requirements in [`docs/PRD.md`](docs/PRD.md); branch ownership and endpoint contract in [`docs/CONTRACT.md`](docs/CONTRACT.md).
