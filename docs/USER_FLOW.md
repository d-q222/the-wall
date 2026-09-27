# User flow

The canonical path a first-time visitor takes, screen by screen. Every screen must work without
onboarding state; `localStorage["wall.onboarding"].done === true` only hides the "Finish setup"
nudge in the sidebar foot.

| # | Screen | URL | Entry points | Primary action | Next step |
|---|---|---|---|---|---|
| 1 | Landing | `/demo/welcome.html` (`/` redirects here) | Root URL; sidebar brand mark | "Set up your firm" (becomes "Resume setup" or "Open the workspace" from saved state) | Onboarding |
| 2 | Onboarding: Firm | `/demo/onboarding.html#firm` | Landing CTA; sidebar "Finish setup" | Confirm firm name (prefilled "Okafor & Lind Immigration") | Practice policy |
| 3 | Onboarding: Practice policy | `#policy` | Step 1; stepper | "Use this policy" (read from `GET /demo/api/policy`) | Matters and walls |
| 4 | Onboarding: Matters and walls | `#matters` | Step 2; stepper | "Continue" over the immigration matters (`GET /demo/api/matters`), each with its own wall | First petition |
| 5 | Onboarding: First petition | `#petition` | Step 3; stepper | "Open in Review" sets `done: true` and the matter | Review |
| 6 | Review | `/demo/?matter=<id>` | Onboarding step 4; sidebar | De-identify, read the judge's verdict, "Add to training set" | Datasets |
| 7 | Datasets | `/demo/datasets.html` | Review; sidebar | De-identify all, export JSONL | Model |
| 8 | Model | `/demo/training.html` | Datasets; sidebar (Workflow group) | Record attorney corrections, retrain | Access wall |
| 9 | Access wall | `/demo/wall.html` | Sidebar (Proof) | Run the cross-matter request; it is refused | Know-how |
| 10 | Know-how | `/demo/compound.html` | Sidebar (Proof) | A procedure compounds, facts stripped | Evaluation |
| 11 | Evaluation | `/scoreboard/` | Sidebar (Proof); landing proof strip | Read measured numbers with n | Policy |
| 12 | Policy | `/demo/policy.html` | Sidebar (Firm); onboarding step 2 | Edit may / never compound | Audit log |
| 13 | Audit log | `/demo/audit.html` | Sidebar (Firm) | Inspect every de-identify, refusal and export | Matters |
| 14 | Matters | `/demo/matters.html` | Sidebar (Firm); breadcrumb firm name | Firm home: every matter and its wall | Review |

Onboarding state (`wall.onboarding`): `{ firm, step (1-4, furthest reached), completed (0-4),
matter, done, dismissed }`. The step is also in the URL hash, so a refresh or a shared link
resumes in place. Stepper and layout follow Cal.com (`packages/ui/components/form/step/Steps.tsx`,
`apps/web/modules/getting-started/[[...step]]/onboarding-view.tsx`); the sidebar nudge follows
Mattermost's onboarding task list (`webapp/channels/src/components/onboarding_tasklist/onboarding_tasklist.tsx`).

Keyboard path: Tab to "Set up your firm", Enter; on each step focus lands on the first field or the
primary button, Enter submits; step 4 Enter opens Review.
