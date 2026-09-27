#!/usr/bin/env bash
# Stop the demo stack started by scripts/demo.sh. Never touches GBrain on :3131.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$REPO_ROOT/.runtime/demo"
API_PORT=8788
STATIC_PORT=8790

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
stop_pidfile "$RUNTIME_DIR/static.pid" "scoreboard static server"

# Fallback: in case demo.sh wasn't the one that started them (or the pidfile is stale),
# kill anything still bound to our two ports. Never touches :3131 (GBrain).
for port in "$API_PORT" "$STATIC_PORT"; do
    pid="$(lsof -ti tcp:"$port" 2>/dev/null || true)"
    if [ -n "$pid" ]; then
        kill $pid 2>/dev/null
        echo "Stopped process on :$port (pid $pid)."
    fi
done

echo "Done. GBrain on :3131 was left untouched."
