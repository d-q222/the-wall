# Design v2: the petition binder

Daniel's call (15:15): the previous UI was "too simple and not professional". The demo is the product.
Every page is a screen in ONE application for a small immigration firm turning past O-1 petitions
into a training set. It must look like software a firm would pay for, not a hackathon form.

## Subject
O-1 petitions are binders: a cover letter plus tabbed exhibits (recommendation letters, criteria
evidence), USCIS receipt notices, federal forms. Users are immigration attorneys and paralegals.

## Tokens (demo/assets/theme.css is the single source; c4 owns it)
- Paper `#FBFBF9` (document sheets)      - Canvas `#E6E9ED` (app background)
- Ink `#14213D` (text, sidebar)            - Form blue `#1F4E9E` (primary actions, links, focus)
- Found `#FFE58A` (identifier highlight)   - Risk `#C2410C` (residual identifier)   - Cleared `#1E7B4F`
- Dark mode exists (prefers-color-scheme + toggle) but LIGHT is the default and the demo mode.
- Type: Public Sans (UI; the US Web Design System face) + Source Serif 4 (document text only).
  Google Fonts only. Tabular figures for numbers. Scale 13/15/17/21/28/40.
- Radius by hierarchy: sheet 2px, chip 4px, panel 8px. Shadows only on the document sheet.

## App shell (demo/assets/nav.js renders it; every page uses it)
Left sidebar (ink): firm name "Okafor & Lind Immigration" (fictional), then
Review · Datasets · Matters · Access wall · Know-how · Policy · Evaluation · Audit log, and a
"Present" button at the bottom. Top bar: breadcrumb + matter switcher. Content area on canvas.

## Screens and owners
| Screen | File | Owner |
|---|---|---|
| Review workspace (hero) | demo/index.html | c4 |
| Datasets (batch de-identify -> training set) | demo/datasets.html | g1 |
| Policy (what may compound per practice) | demo/policy.html | g2 |
| Evaluation (scoreboard v2) | scoreboard/index.html | g3 |
| Matters (firm overview) | demo/matters.html | g4 |
| Audit log | demo/audit.html | g5 |
| Access wall | demo/wall.html | f1 |
| Know-how (compounding) | demo/compound.html | f2 |
| Present (story mode) | demo/present.html | f3 |
| Blind-set entry (Daniel only) | demo/blind.html | h1 |

## Review workspace (the hero)
Left: binder exhibit tabs (Cover letter, Exhibit A: Recommendation, Exhibit B: Criteria evidence...).
Center: the petition as a paper sheet in Source Serif, with an Original / Redline / Clean toggle.
Right inspector: identifiers found, grouped by type with counts; the judge's verdict with its evidence
quote; "Add to training set". The one orchestrated motion: on De-identify, identifiers highlight in
Found yellow, then collapse one by one into typed placeholder chips; the verdict lands last.

## Rules
- Spend boldness in one place per screen; everything else quiet and dense like real legal software.
- Real content only (fixtures, live API). Demo-safe replay: show a small "Replayed" tag, never fake.
- No all-caps eyebrow labels, no monospace small labels, no "→" on buttons, no middle-dot meta strings,
  no identical card grids, no gradient washes. Sentence case. Buttons say exactly what happens.
- Responsive to 1280px wide minimum (projector); keyboard focus visible; reduced motion respected.
- Before calling a screen done: headless Chrome screenshot at 1440x900, look at it, fix, repeat.
