#!/usr/bin/env bash
# The compounding beat (PRD demo, ~0:45): scrub a litigation procedure from one
# matter (Delmarva) and reuse its structure to draft a letter for an unrelated
# matter (Chen) — the procedure compounds across matters, the client facts
# never do. Requires the API running first:
#   uv run uvicorn wall.server:app --port 8788
set -euo pipefail
cd "$(dirname "$0")/.."

API_URL="${WALL_API_URL:-http://localhost:8788}"
mkdir -p .runtime
PROCEDURE=".runtime/delmarva-procedure-scrubbed.md"

echo "== 1. Scrub fixtures/matters/delmarva/session-demand-letter.md (practice: litigation) =="
uv run python - "$API_URL" "$PROCEDURE" <<'PY'
import json
import sys
import urllib.request

api_url, out_path = sys.argv[1], sys.argv[2]
text = open("fixtures/matters/delmarva/session-demand-letter.md").read()
body = json.dumps({"matter_id": "delmarva", "practice": "litigation", "text": text}).encode()
req = urllib.request.Request(
    f"{api_url}/scrub", body, {"Content-Type": "application/json"}, method="POST"
)
resp = json.load(urllib.request.urlopen(req))
open(out_path, "w").write(resp["text"])
print(f"removed={resp['removed']} spans -> saved scrubbed procedure to {out_path}")
PY

echo
echo "== 2. Draft the chen letter reusing that procedure's structure (live recall + /check) =="
uv run python -m agent.draft \
    --matter chen \
    --task "Write a demand letter for this matter using the firm's standard procedure." \
    --procedure "$PROCEDURE"
