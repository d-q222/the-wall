#!/usr/bin/env bash
# One command for a demo-ready stack. The API (wall/server.py) serves everything
# from one origin: /check /scrub /judge /deidentify, plus static /demo/,
# /scoreboard/ and /results/ (coordinator update 15:14: "one origin").
# Never starts, stops, or restarts GBrain -- that server is owned by another session.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

API_PORT="${API_PORT:-8788}"  # override for dev ports, e.g. API_PORT=8805
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

# Refuse to share a port: another server there (e.g. the coordinator's on 8788)
# is not ours to replace or kill.
if holder="$(lsof -ti tcp:"$API_PORT" -sTCP:LISTEN 2>/dev/null)"; then
    echo "ERROR: :$API_PORT is already in use (pid $holder). Stop it with scripts/stop.sh" >&2
    echo "  if it is yours, or pick another port: API_PORT=8805 scripts/demo.sh" >&2
    exit 1
fi

echo "Starting API on :$API_PORT (serves /demo/, /scoreboard/, /results/ too)..."
uv run uvicorn wall.server:app --port "$API_PORT" \
    > "$RUNTIME_DIR/api.log" 2>&1 &
API_PID=$!
echo "$API_PID" > "$RUNTIME_DIR/api.pid"

cleanup() {
    echo
    echo "Stopping demo stack (GBrain left running)..."
    # `uv run` spawns uvicorn as a child; stop that child first, then uv itself.
    # Only our own processes -- never kill by port.
    pkill -TERM -P "$API_PID" 2>/dev/null || true
    kill "$API_PID" 2>/dev/null || true
    wait "$API_PID" 2>/dev/null || true
    rm -f "$RUNTIME_DIR/api.pid"
    echo "Stopped."
}
trap cleanup INT TERM

# Wait until it actually answers; don't announce a server that never bound.
for _ in $(seq 1 60); do
    curl -fsS --max-time 1 "http://localhost:$API_PORT/docs" >/dev/null 2>&1 && break
    if ! kill -0 "$API_PID" 2>/dev/null; then
        echo "ERROR: API exited during startup. Last log lines:" >&2
        tail -5 "$RUNTIME_DIR/api.log" >&2
        rm -f "$RUNTIME_DIR/api.pid"
        exit 1
    fi
    sleep 0.5
done
echo
echo "=================================================="
echo "  API:        http://localhost:$API_PORT"
echo "  Demo UI:    http://localhost:$API_PORT/demo/"
echo "  Scoreboard: http://localhost:$API_PORT/scoreboard/"
echo "=================================================="
echo "Ctrl-C to stop (GBrain on :3131 is left running)."

wait "$API_PID"
