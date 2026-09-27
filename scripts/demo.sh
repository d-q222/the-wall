#!/usr/bin/env bash
# One command for a demo-ready stack: API + scoreboard static server.
# Never starts, stops, or restarts GBrain -- that server is owned by another session.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

API_PORT=8788
STATIC_PORT=8790
GBRAIN_HEALTH_URL="http://localhost:3131/health"
RUNTIME_DIR="$REPO_ROOT/.runtime/demo"
RESULTS_FILE="${WALL_RESULTS:-$HOME/the-wall/results/results.json}"

mkdir -p "$RUNTIME_DIR"

echo "Checking GBrain at :3131 (never started/stopped by this script)..."
if curl -fsS --max-time 3 "$GBRAIN_HEALTH_URL" >/dev/null 2>&1; then
    echo "  GBrain is up."
else
    echo "  WARNING: GBrain is not reachable at $GBRAIN_HEALTH_URL." >&2
    echo "  The matter agent's live recall will fail; ask the coordinator, don't start it yourself." >&2
fi

# The scoreboard fetches ../results/results.json relative to /scoreboard/, but the
# shared results file lives outside the repo (per CONTRACT.md). Symlink it into place
# so the static server can reach it; the whole path is gitignored.
mkdir -p "$(dirname "$RESULTS_FILE")"
touch "$RESULTS_FILE"
if [ ! -e "$REPO_ROOT/results" ]; then
    ln -s "$(dirname "$RESULTS_FILE")" "$REPO_ROOT/results"
fi

echo "Starting API on :$API_PORT..."
uv run uvicorn wall.server:app --port "$API_PORT" \
    > "$RUNTIME_DIR/api.log" 2>&1 &
API_PID=$!
echo "$API_PID" > "$RUNTIME_DIR/api.pid"

echo "Starting scoreboard static server on :$STATIC_PORT..."
python3 -m http.server "$STATIC_PORT" --directory "$REPO_ROOT" \
    > "$RUNTIME_DIR/static.log" 2>&1 &
STATIC_PID=$!
echo "$STATIC_PID" > "$RUNTIME_DIR/static.pid"

cleanup() {
    echo
    echo "Stopping demo stack (GBrain left running)..."
    kill "$API_PID" "$STATIC_PID" 2>/dev/null || true
    wait "$API_PID" "$STATIC_PID" 2>/dev/null || true
    # `uv run` spawns uvicorn as a child process; killing the `uv` PID alone can
    # leave that child holding the port. Fall back to killing by port.
    for port in "$API_PORT" "$STATIC_PORT"; do
        pid="$(lsof -ti tcp:"$port" 2>/dev/null || true)"
        [ -n "$pid" ] && kill $pid 2>/dev/null || true
    done
    rm -f "$RUNTIME_DIR/api.pid" "$RUNTIME_DIR/static.pid"
    echo "Stopped."
}
trap cleanup INT TERM

sleep 1
echo
echo "=================================================="
echo "  API:        http://localhost:$API_PORT"
echo "  Demo UI:    http://localhost:$API_PORT/demo/"
echo "  Scoreboard: http://localhost:$STATIC_PORT/scoreboard/"
echo "=================================================="
echo "Ctrl-C to stop (GBrain on :3131 is left running)."

wait "$API_PID" "$STATIC_PID"
