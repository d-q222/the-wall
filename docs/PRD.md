

# Ethical Wall Brain: Hackathon PRD
 · 

## Summary
Ethical Wall Brain is agent memory for small law firms that compounds the firm's know-how while walling off each client's facts. We build it in 3h45 at the Own Your Intelligence hackathon (YC, Sept 27, 1:15 to 5:00 PM) with 2 people and parallel coding agents.

Pitch line: Today, firms stay safe by using AI that forgets. We let it remember the firm's know-how without remembering one client inside another's work.

Core idea: compound the how, wall the what. Procedures learn across matters; facts never cross them.

What we demo: a live wall attack that fails, a scrubbed procedure improving another matter's draft, and a held-out leak scoreboard.

Hosts used for real: GBrain (walls), Memorable (procedures), River (owned leak judge), QM (room per matter). Superset runs our parallel build.

## Problem
Small firms must choose between AI that learns and AI that is safe. ABA Formal Opinion 512 makes self-learning tools the risky case.

The rule: 512 warns that a self-learning tool can disclose one client's information in another client's work, even inside one firm. Using one requires specific informed consent; boilerplate in an engagement letter is not enough (
dizon.law).

Today's workaround is forgetting: standard compliance advice is to prefer zero-retention configurations and avoid tools that train on inputs (
legalaiinsights). The AI stays safe by learning nothing.

Big Law has walls; small firms do not: Harvey now enforces Intapp Walls across Assistant, Vault and Spaces, but it needs an Intapp cloud license plus a separate Harvey connector license (
Harvey). Those public materials describe access control, meaning who can open what, not what a memory learns.

The gap: no small-firm tool lets memory compound while proving that client facts stay put.
Why the compounding policy must vary by practice area (asylum example). Under Matter of R-K-K- (BIA 2015), strikingly similar declarations across unrelated applicants can support an adverse credibility finding. In Matter of V-S-A- (BIA 2026), DHS pointed to 12 declarations with boilerplate hallmarks and the Board reversed a grant (
EOIR). In asylum, shared narrative phrasing is itself the harm, so narrative text must never compound. In most litigation, shared letter templates are a firm asset.

## Users, goals, non-goals
The user is a solo or small-firm attorney who wants AI that gets better with every matter without risking a cross-client leak.
Users

Attorney (primary): drafts letters, briefs and filings across 10 to 50 active matters. Owns the compounding policy.

Paralegal: works inside one matter room at a time. Must never see another matter by accident.

Demo persona: a 3-matter firm with synthetic clients (Delmarva Logistics, Chen trust, Reyes tenancy). No real client data anywhere.
Goals for the hackathon

Show a wall that holds under a live attack, using GBrain's own permission system.

Show one procedure learned on matter A improving matter B's draft, with zero A facts carried over.

Report honest held-out leak detection numbers, including where each detector fails.

Use four hosts for distinct, real jobs.
Non-goals

Not a compliance guarantee. We reduce one measured risk; consent duties under 512 remain.

No real client data, ever, including in River training.

Never auto-paraphrase a draft to lower a similarity score. Flags send the lawyer back to the client's own account.

No asylum demo data. Asylum appears on one slide as the policy example.

## Product principles
The firm decides what may compound, per practice area, and the system enforces it.

Compound the how, wall the what. Procedures, checklists and research may cross matters after scrubbing. Names, amounts, strategy and distinctive details never cross.

Policy per practice area. Each matter carries a practice tag that sets what may compound:
 | 
Practice | 
May compound | 
Never compounds
 | 
Litigation | 
Drafting procedures, letter templates, research | 
Parties, amounts, strategy, witness details
 | 
Trusts and estates | 
Accounting checklists, filing steps | 
Family facts, balances, allegations
 | 
Asylum (slide only) | 
Checklists, country-conditions research, legal argument | 
Any narrative text from a declaration

Memory as guard. Where text must not repeat, memory keeps every past document so new drafts can be checked against all of them. A tool that forgets cannot run this check.

Flags go to a human. The system blocks and explains. It never rewrites text to beat a detector.

Every number is held-out. We quote only results on data the detectors were never tuned on.

## Architecture
Five layers keep facts inside their matter, and one scrubbed loop lets procedures compound.
A request enters a matter's QM room. The agent recalls only its own GBrain source, drafts, and every draft passes the output guard before the attorney sees it. Finished sessions pass the scrubber before they can become firm-wide skills.
Three detectors, each for a different leak
 | 
Detector | 
Catches | 
Misses | 
Status
 | 
Regex fingerprint | 
Names, orgs, amounts in many formats | 
Descriptions, paraphrase | 
Tested: 81% on held-out leaks
 | 
Carryover (6-gram) | 
Distinctive phrases unique to one other matter | 
Paraphrase | 
Tested: 4/4 on toy corpus
 | 
River judge | 
Paraphrased descriptions | 
Unknown until trained | 
Target of the build
Host mapping
 | 
Host | 
Job in this product | 
Integration point
 | 
GBrain | 
The wall | 
Isolated source per matter, register-client --source --federated-read, dream --source
 | 
Memorable | 
Procedural memory | 
memorable ingest - with a scrubbed JSON trace
 | 
River | 
Owned leak judge | 
SFT on synthetic data via river-client
 | 
QM | 
Room per matter, skill promotion | 
Room scopes; admin-gated skill promotion; screening proxy if its contract allows
 | 
Superset | 
Build tool, not product | 
Parallel coding agents in worktrees
UFO is out of scope. A forced integration costs more credibility than it earns.

## Functional requirements
P0 items alone make a complete demo. P1 adds the hosts that strengthen it. P2 is only for spare time.
 | 
ID | 
Requirement | 
Priority | 
Acceptance check
 | 
FR-1 | 
One isolated GBrain source per matter, synced from its folder | 
P0 | 
sources list shows 3 isolated sources
 | 
FR-2 | 
One scoped OAuth client per matter agent; agents never run as local trusted callers | 
P0 | 
Matter-B client gets permission_denied on matter A, and __all__ returns only B
 | 
FR-3 | 
Matter agent recalls through its scoped client and drafts a letter | 
P0 | 
Draft for B cites B's facts only
 | 
FR-4 | 
Regex guard that subtracts the current matter's own names and amounts first | 
P0 | 
Held-out eval: at least 79/97 leaks, at most 1/103 false alarms
 | 
FR-5 | 
Carryover detector: flags 6-grams found in exactly one other matter, ignores shared boilerplate | 
P0 | 
Flags A's distinctive detail in B's draft; passes firm boilerplate
 | 
FR-6 | 
Scrubber applies the practice policy before any procedure is shared | 
P0 | 
Scrubbed procedure checks clean against every other matter
 | 
FR-7 | 
Prompt-based LLM judge as the fallback third detector | 
P0 | 
Runs on judge_eval_hard.jsonl and reports a number
 | 
FR-8 | 
Scoreboard page: per-detector results, n stated, false alarms shown | 
P0 | 
One screen, readable from the back of the room
 | 
FR-9 | 
River-tuned judge replaces the prompt judge if it beats base Qwen | 
P1 | 
Three-way comparison on the hard eval
 | 
FR-10 | 
Scrubbed traces go to memorable ingest - | 
P1 | 
Ingest accepted; trace includes a write step
 | 
FR-11 | 
QM room per matter, with scrubbed skills promoted through the admin gate | 
P1 | 
Two rooms; a skill promoted from A is visible in B
 | 
FR-12 | 
River judge wired as QM's screening proxy on recall results | 
P2 | 
Only if the proxy contract is simple
 | 
FR-13 | 
Practice-tag policy editor in the UI | 
P2 | 
Toggle what may compound per practice

## Evaluation
The headline number comes from the hard held-out set, where regex and string matching both score 0/102. Anything the judge catches there is real.
Datasets (in the hackathon pack)
 | 
File | 
Size | 
Use
 | 
judge_train_v2.jsonl | 
900 | 
River SFT: 600 original plus 300 paraphrase and hard-negative examples
 | 
judge_eval_hard.jsonl | 
200 | 
Headline: 102 paraphrased leaks with held-out synonyms, 30 hard negatives, 68 clean
 | 
judge_eval.jsonl | 
200 | 
Sanity check only: its descriptive leaks are templated
 | 
demo_leak_cases.jsonl | 
20 | 
Live demo cases; self-written, so never the headline
 | 
Blind set | 
30 | 
Written in the room by whoever has not opened the training files
Measured baselines (Sept 27)
 | 
Detector | 
Eval set | 
Leaks caught | 
Clean drafts correct
 | 
Regex | 
Held-out standard | 
79/97 | 
102/103
 | 
Regex | 
Hard paraphrase | 
0/102 | 
98/98
 | 
Role and industry string match | 
Hard paraphrase | 
0/102 | 
98/98
Protocol

Compare three judges on the hard set: base Qwen, River-tuned Qwen, frontier prompt.

Report River as tuned vs its own base, plus cost vs frontier. Claim beating frontier only if it does.

Report the blind set separately. It is the number judges will trust most.

State n on every slide.
Targets

River-tuned judge beats base Qwen on hard paraphrase leaks.

False alarms stay at or under 5% of clean drafts.

Any result is reported, including a miss.

## Demo script
The demo runs 2 minutes in four beats, with a screen recording as backup.
 | 
Time | 
Beat | 
On screen | 
Line
 | 
0:00 | 
The problem | 
One slide: ABA 512 and the "AI that forgets" workaround | 
"Firms stay safe today by using AI that learns nothing."
 | 
0:20 | 
The wall | 
Matter-B agent asks for everything; permission_denied on A | 
"The matter-B agent cannot see matter A, even when it asks for all sources."
 | 
0:45 | 
The compounding | 
Procedure learned on Delmarva, scrubbed, improves the Chen letter | 
"The firm's know-how carried over. Delmarva's facts did not."
 | 
1:15 | 
The honest scoreboard | 
Per-detector results on the hard set, n shown | 
"Regex catches 0 of 102 paraphrased leaks. Our judge catches __."
 | 
1:45 | 
The policy | 
Asylum slide: V-S-A- and the per-practice policy table | 
"In asylum, even the firm's writing style is a liability. The firm sets what compounds."
Scoreboard layout

Rows: regex, carryover, prompt judge, River judge (if ready).

Columns: leaks caught, false alarms, n.

One highlighted cell: the River judge on hard paraphrase leaks.

Blind-set result in its own box beneath.

## Pitch and claim rules
Every sentence in the pitch must be checkable against a source or a result on screen.
Opener (fill the blank on the day)
An AI that remembers everything is a liability for a lawyer. ABA Opinion 512 warns that a tool that learns from one client can leak into another client's work, even inside the same firm. So today, firms use AI that forgets. We built memory that compounds the firm's know-how but walls off each client's facts. On 102 held-out paraphrased leaks, pattern matching catches zero. Our judge, trained on River with no real client data, catches __.
Say / don't say
 | 
Say | 
Don't say | 
Why
 | 
"Reduces a measured cross-client leak risk" | 
"Makes firms 512-compliant" | 
Consent duties remain
 | 
"Trained without client data" | 
"No client data ever leaves" | 
Inference on River may see drafts
 | 
"Their public materials describe access control" | 
"Harvey can't do this" | 
Unverified
 | 
"The pattern DHS argued in V-S-A-" | 
"DHS uses AI to detect copying" | 
Unknown
 | 
"On n = 102 held-out cases" | 
Any number without n | 
Credibility
 | 
"The scrubber on this example" | 
"The scrubber works" | 
Tested on one procedure
Q&A prep

Does it replace consent? No. It makes consent specific: only scrubbed procedure crosses clients, and the logs show it.

Why not Harvey? Enterprise licensing; we target firms of 1 to 10 lawyers.

Could the similarity check hide copied claims? Flags return the lawyer to the client's own account. The system never rewrites to beat a detector.

Where do the weights live? Ask River at opening; answer from what they say.

## Team and delegation
Two people each run 2 to 3 coding agents in parallel worktrees, then meet at one integration gate at 3:30. The split follows the architecture: Daniel owns the path a request takes; the teammate owns everything that judges a draft.
If River is not training by 2:00, drop it to the roadmap slide. Whatever is not connected at 3:30 gets cut, not debugged.
Ownership
 | 
Person | 
Owns | 
Why
 | 
Daniel | 
GBrain walls, matter agent, QM or panes, blind set, pitch | 
Knows the wall setup from testing; has not opened the training files, so can write the blind set
 | 
Teammate | 
Regex and carryover guard, scrubber, Memorable, River training and eval | 
Self-contained pipeline with clear numbers
Agent briefs (one agent per worktree, never two agents on the same files)
 | 
Agent | 
Owner | 
Builds | 
Model tier | 
Done when
 | 
A1 walls | 
Daniel | 
3 isolated sources, scoped clients, HTTP server, attack script | 
Strong | 
Attack prints permission_denied
 | 
A2 agent | 
Daniel | 
Matter agent: scoped recall, drafts letter, calls /check | 
Strong | 
Draft for B uses only B facts
 | 
A3 scoreboard | 
Daniel | 
One-page scoreboard reading results.json | 
Cheap | 
Renders all detectors with n
 | 
B1 guard | 
Teammate | 
Regex plus carryover behind /check; eval runner over all eval files | 
Strong | 
Reproduces 79/97 and 0/102 baselines
 | 
B2 River | 
Teammate | 
Render JSONL with River's renderer, launch SFT, poll, run 3-judge eval | 
Cheap for rendering, strong for eval code | 
Three-judge table in results.json
 | 
B3 scrub | 
Teammate | 
/scrub with practice policy; memorable ingest - of scrubbed trace | 
Strong | 
Scrubbed trace accepted
Delegation rules

Menial work goes to cheaper models: rendering data, running evals, scaffolding the UI, formatting results.

Judgment stays with the humans: the interface contract, integration, what to cut, the pitch.

Every agent gets the contract below plus ACCESS.md as its brief. No agent invents an endpoint.

A human reviews every merge. Agents do not merge each other's work.
Interface contract (agree in the first 5 minutes)
 | 
Endpoint | 
Input | 
Output
 | 
POST /check | 
matter_id, draft | 
verdict, hits[] of detector, matter, evidence
 | 
POST /scrub | 
matter_id, practice, text | 
text, removed count
 | 
POST /judge | 
current, protected[], draft | 
verdict, matter, evidence (same JSON as the training labels)
 | 
results.json | 
written by eval runners | 
per detector, per eval set: caught, false alarms, n

## Tonight checklist
Tonight is for access and data only. No product code before 1:15.
Daniel

Install GBrain with bun install -g github:garrytan/gbrain and walk through the gotchas in ACCESS.md

Get QM running (check whether the repo's local mode avoids a cloud deploy), or decide now to cut it

Read QM's SECURITY.md for the screening proxy and skill promotion contracts

Do not open judge_train_v2.jsonl or judge_eval_hard.jsonl (keeps you blind for the blind set)

Draft the opener and the asylum slide

Optional: a 5-minute call with an attorney to confirm the pain
Teammate

Get a River API key and run one client.sample(...) call

pip install river-client and python -m river_client.skill --install so coding agents know the SDK

npm i -g memorable-cli, then memorable init and memorable enable

Test the prompt-judge prompt on 10 hard-set examples with your own API key

Read the eval protocol and the say / don't say table
Both

Confirm the hackathon rules allow bringing data files

Agree on the interface contract and the agent briefs

Set up Superset or worktrees so each agent has its own

## Risks, cut lines, open questions
The biggest risk is River access at 1:15; the demo survives without it.
 | 
Risk | 
Likelihood | 
Fallback
 | 
No River key or slow training | 
Medium | 
Prompt judge on the scoreboard; River becomes the roadmap slide
 | 
QM not running | 
High | 
Two panes labeled by matter; mention QM hooks in one sentence
 | 
Memorable ingest refuses trace | 
Medium | 
Store procedures in a shared firm-skills GBrain source
 | 
Judge scores poorly on hard set | 
Medium | 
Report it honestly; the 0/102 baseline still makes the case
 | 
Frontier prompt beats River | 
Medium | 
Claim tuned vs base Qwen and cost, not beating frontier
 | 
Pre-written code rule | 
Low | 
All code written in the room; only data brought
 | 
Asylum reads as fraud help | 
Low | 
Say the no-rewrite rule before anyone asks
Cut order when time slips: QM, then Memorable, then River, then carryover. Never cut the wall attack or the scoreboard.
Open questions

Can River export tuned weights to run locally, or only serve them?

What is QM's screening proxy contract?

Does QM's local mode work without Fly or AWS?

Do the rules allow bringing data files?

## Appendix: tested results and setup gotchas
Everything below was run on Sept 27 on GBrain v0.59 with synthetic matters.
Test log
 | 
Test | 
Result
 | 
Matter-B scoped client: default search | 
Returns only matter B
 | 
Matter-B scoped client: source_id: __all__ | 
Clamped to matter B
 | 
Matter-B scoped client: get_page on matter A | 
permission_denied
 | 
Local trusted caller: __all__ | 
Sees all 3 matters (why agents must connect remotely)
 | 
Regex guard, held-out standard set | 
79/97 leaks, 1/103 false alarms
 | 
Regex guard, hard paraphrase set | 
0/102 leaks, 98/98 clean correct
 | 
Baseline without subtracting current matter | 
12/30 false alarms on own-fact drafts
 | 
Carryover detector, toy corpus | 
4/4 correct
 | 
Scrubber on one procedure | 
6 raw leaks to 0; all 4 steps usable
 | 
Declaration similarity, AI template vs own words | 
41% vs 0% (5-gram overlap)
Setup gotchas

GBrain installs from GitHub with bun; the npm package named gbrain is unrelated.

Each matter folder needs a git repo with a commit before sources add.

gbrain sync --source <id> needs --no-pull.

Start gbrain serve --http with setsid nohup, or it dies with the shell.

Memorable is memorable-cli on npm; the pip package memorable-ai is unrelated.

Memorable refuses traces that only read or search; include a write step.

Memorable redaction targets vendor keys and high-entropy strings, not client names. Scrub first.