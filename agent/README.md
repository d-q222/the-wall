# Matter agent (A2)

Scoped recall (matter's own GBrain client) -> draft with the in-product LLM -> `/check` guard.
Never mentions another matter's names, orgs, amounts, or details.

Start the API first (from repo root):

```sh
uv run uvicorn wall.server:app --port 8788
```

`WALL_API_URL` (default `http://localhost:8788`) selects the API base for both commands below.

## Demo 1: live chen draft

```sh
uv run python -m agent.draft --matter chen --task "Write a status update letter to the client summarizing where the matter stands."
```

Recalls chen's own facts through its scoped GBrain client, drafts with the LLM, then posts the
draft to `/check`. Expect verdict `clean` with no hits (no delmarva/reyes facts).

## Demo 2: the compounding beat

```sh
agent/demo_compounding.sh
```

Scrubs Delmarva's litigation procedure via `POST /scrub` (matter facts stripped, structure kept),
saves it under `.runtime/`, then drafts the chen letter with `--procedure` pointing at that file.
Shows the procedure's structure (sections, deadline, exhibits) carried over into an unrelated
matter with zero Delmarva facts — confirmed by `/check`.

## Offline (no live API/LLM)

```sh
uv run python -m agent.draft --matter chen --task "..." --offline
```

Reads fixtures directly instead of live GBrain recall; used by `agent/test_draft.py`, never for a
live draft.
