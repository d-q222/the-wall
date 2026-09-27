#!/usr/bin/env bash
# One command for a demo-ready stack. The API (wall/server.py) serves everything
# from one origin: /check /scrub /judge /deidentify, plus static /demo/,
# /scoreboard/ and /results/ (coordinator update 15:14: "one origin").
# Never starts, stops, or restarts GBrain -- that server is owned by another session.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

API_PORT=8788
GBRAIN_HEALTH_URL="http://localhost:3131/health"
RUNTIME_DIR="$REPO_ROOT/.runtime/demo"

mkdir -p "$RUNTIME_DIR"

echo "Checking GBrain at :3131 (never started/stopped by this script)..."
if curl -fsS --max-time 3 "$GBRAIN_HEALTH_URL" >/dev/null 2>&1; then
    echo "  GBrain is up."
else
    echo "  WARNING: GBrain is not reachable at $GBRAIN_HEALTH_URL." >&2
    echo "  The matter agent's live recall will fail; ask the coordinator, don't start it yourself." >&2
fi

echo "Starting API on :$API_PORT (serves /demo/, /scoreboard/, /results/ too)..."
uv run uvicorn wall.server:app --port "$API_PORT" \
    > "$RUNTIME_DIR/api.log" 2>&1 &
API_PID=$!
echo "$API_PID" > "$RUNTIME_DIR/api.pid"

cleanup() {
    echo
    echo "Stopping demo stack (GBrain left running)..."
    kill "$API_PID" 2>/dev/null || true
    wait "$API_PID" 2>/dev/null || true
    # `uv run` spawns uvicorn as a child process; killing the `uv` PID alone can
    # leave that child holding the port. Fall back to killing by port.
    pid="$(lsof -ti tcp:"$API_PORT" 2>/dev/null || true)"
    [ -n "$pid" ] && kill $pid 2>/dev/null || true
    rm -f "$RUNTIME_DIR/api.pid"
    echo "Stopped."
}
trap cleanup INT TERM

sleep 1
echo
echo "=================================================="
echo "  API:        http://localhost:$API_PORT"
echo "  Demo UI:    http://localhost:$API_PORT/demo/"
echo "  Scoreboard: http://localhost:$API_PORT/scoreboard/"
echo "=================================================="
echo "Ctrl-C to stop (GBrain on :3131 is left running)."

wait "$API_PID"
