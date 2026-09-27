#!/usr/bin/env bash
# Stop the demo stack started by scripts/demo.sh. Never touches GBrain on :3131.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$REPO_ROOT/.runtime/demo"
API_PORT="${API_PORT:-8788}"  # override for dev ports, e.g. API_PORT=8805

stop_pidfile() {
    local pidfile="$1" label="$2"
    if [ -f "$pidfile" ]; then
        local pid
        pid="$(cat "$pidfile")"
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            echo "Stopped $label (pid $pid)."
        fi
        rm -f "$pidfile"
    fi
}

stop_pidfile "$RUNTIME_DIR/api.pid" "API"

# Fallback: in case demo.sh wasn't the one that started it, the pidfile is
# stale, or `uv run` left its uvicorn child behind. Never touches :3131 (GBrain).
pid="$(lsof -ti tcp:"$API_PORT" 2>/dev/null || true)"
if [ -n "$pid" ]; then
    kill $pid 2>/dev/null
    echo "Stopped process on :$API_PORT (pid $pid)."
fi

echo "Done. GBrain on :3131 was left untouched."
