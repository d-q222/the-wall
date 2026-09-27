#!/usr/bin/env bash
# FR-10: pipe the scrubbed Delmarva procedure trace into `memorable ingest -`.
# Uses the real hosted service if `memorable` is logged in; otherwise starts
# the local extraction stub documented at
# /Users/dqi26/the-wall/.runtime/setup/memorable.md and uses that instead.
# Always prints which mode was used.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

TRACE="memorable/trace_scrubbed.json"
STUB_SCRIPT="/Users/dqi26/the-wall/.runtime/setup/memorable_extraction_stub.mjs"

export MEMORABLE_HOME="$(pwd)/.runtime/memorable-home"
mkdir -p "$MEMORABLE_HOME"

if memorable status 2>/dev/null | grep -qE "extraction api\s+configured"; then
  echo "memorable/ingest.sh: MODE=real (memorable is logged in to the hosted service)"
else
  echo "memorable/ingest.sh: MODE=stub (no real login found; using the local extraction stub)"

  STUB_OUT="$(mktemp)"
  node "$STUB_SCRIPT" >"$STUB_OUT" 2>&1 &
  STUB_PID=$!
  disown "$STUB_PID" 2>/dev/null || true
  trap 'kill "$STUB_PID" 2>/dev/null || true; rm -f "$STUB_OUT"' EXIT

  STUB_URL=""
  for _ in $(seq 1 20); do
    STUB_URL="$(grep -o 'STUB_URL=.*' "$STUB_OUT" 2>/dev/null | head -1 | cut -d= -f2- || true)"
    if [ -n "$STUB_URL" ]; then
      break
    fi
    sleep 0.2
  done
  if [ -z "$STUB_URL" ]; then
    echo "memorable/ingest.sh: stub server failed to start" >&2
    cat "$STUB_OUT" >&2
    exit 1
  fi

  export MEMORABLE_API_URL="$STUB_URL"
  export MEMORABLE_API_KEY="mk_stub_key_not_real_0000000000"
  echo "memorable/ingest.sh: stub listening at $STUB_URL"
  memorable enable >/dev/null
fi

echo "memorable/ingest.sh: ingesting $TRACE"
memorable ingest - < "$TRACE"

echo
echo "memorable/ingest.sh: recall check"
memorable recall "draft a demand letter procedure"
