# Walls: GBrain isolation per matter (FR-1, FR-2)

Verified 2026-09-27 on GBrain 0.59.0.0 (PGLite, no embeddings, keyword search only).

## Run the live attack (demo)

```sh
uv run python walls/attack.py
```

Runs as the `chen` matter agent against `delmarva`. Prints one big PASS/FAIL per check and a
final `WALL HOLDS` / `WALL FAILED` banner; exits non-zero on any FAIL.

| # | Call as the `chen` client | Expected |
|---|---|---|
| 1 | `search "Harborview"` (own fact) | hits, all `source_id == "chen"` |
| control | `search "Delmarva"` as the `delmarva` client | hits (the data really exists) |
| 2 | `search "Delmarva"` | 0 hits |
| 3 | `search "Delmarva"`, `source_id: "__all__"` | 0 hits (clamped to chen's grant) |
| 4 | `get_page "session-demand-letter"`, `source_id: "delmarva"` | `permission_denied` |

## Runtime state (absolute paths, gitignored, shared by every worktree)

Under `/Users/dqi26/.superset/projects/The-Wall/.runtime/`:

| Path | What |
|---|---|
| `clients/<matter_id>.json` | `{"url", "client_id", "client_secret", "source_id"}` for `chen`, `delmarva`, `reyes` |
| `matters/<matter_id>/` | Git repo per matter (copy of `fixtures/matters/<id>/*.md`); the GBrain source path |
| `logs/gbrain-serve.log` | Server log |
| `gbrain-serve.pid` | Server PID |

Server: `http://localhost:3131/mcp` (MCP streamable HTTP, OAuth 2.1). Health: `/health`.
Sources are `--no-federated`; each client is `--scopes read --source <id> --federated-read <id>`.

## How A2 (matter agent) recalls

Use `walls/client.py` (stdlib only). One client per matter; never a local/stdio GBrain.

```python
from walls.client import Client
c = Client("chen")                 # token + MCP session for the chen-agent OAuth client
hits = c.search("Harborview")      # list of {slug, title, chunk_text, source_id, score, ...}
page = c.get_page("intake")        # dict with compiled_truth, title, ...; each matter has "intake"
raw  = c.call("search", {"query": "x"})   # raw MCP tools/call result
```

`get_page` returns `{"error": "permission_denied" | "page_not_found", ...}` on refusal.
`search` raises `PermissionError` if the server returns an error payload.
Tokens live 3600s: create a fresh `Client` per request or per run.

Exact wire calls, if not using Python:

1. `POST http://localhost:3131/token`, form-encoded
   `grant_type=client_credentials&client_id=...&client_secret=...&scope=read` -> `access_token`.
2. `POST /mcp` with `Authorization: Bearer <token>`, `Content-Type: application/json`,
   `Accept: application/json, text/event-stream`. Send `initialize`
   (`protocolVersion: "2025-06-18"`), keep the `Mcp-Session-Id` response header, send
   `notifications/initialized`, then `tools/call`. SSE replies: parse the last `data:` line.
3. `{"name": "search", "arguments": {"query": "Harborview"}}` -> JSON list in `result.content[0].text`.
   `{"name": "get_page", "arguments": {"slug": "intake"}}` -> JSON page in `result.content[0].text`.

Search is keyword-only (no embedding provider): query with terms that appear in the notes.

## From-scratch setup: `walls/setup.sh`

Copies fixtures to `.runtime/matters/<id>` as git repos, `sources add --no-federated`,
`sync --no-pull`, `auth register-client --scopes read --source <id> --federated-read <id>`,
writes `clients/<id>.json` (mode 600, secret never printed), then starts `serve --http` in the
background with a pid file. `--init` also runs `gbrain init --pglite --no-embedding`.

**Not run on the demo machine.** The live wall there was built by hand with the same steps.
The script refuses to run while a server answers on :3131.

## Ops caveat

- PGLite allows one process: while `serve` runs, `gbrain sync`, `sources`, `auth` CLI commands fail
  (`live_serve`). Stop the server first (`kill $(cat .runtime/gbrain-serve.pid)`), run the
  command, then restart:
  `nohup gbrain serve --http --port 3131 > .runtime/logs/gbrain-serve.log 2>&1 < /dev/null & disown`
- On the demo machine the server is owned by one session: ask the coordinator, do not restart it.
- Never connect a matter agent over stdio `gbrain serve` or `claude mcp add gbrain`: a local
  trusted caller sees all three matters.
- Dream cycle: always pass `--source <matter>`.
