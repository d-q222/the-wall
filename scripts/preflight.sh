#!/usr/bin/env bash
# Pre-demo checklist. Read-only: never starts/stops GBrain or the API, never
# prints secret values or data-file contents. Exits non-zero if anything critical fails.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

ENV_FILE="/Users/dqi26/the-wall/.env"
DATA_DIR="/Users/dqi26/the-wall/data"
RESULTS_FILE="${WALL_RESULTS:-$HOME/the-wall/results/results.json}"
API_PORT=8788

fail=0
GREEN=$'\033[32m'; RED=$'\033[31m'; YELLOW=$'\033[33m'; BOLD=$'\033[1m'; RESET=$'\033[0m'

pass() { echo "  ${GREEN}${BOLD}PASS${RESET}  $1"; }
warn() { echo "  ${YELLOW}${BOLD}WARN${RESET}  $1"; }
bad()  { echo "  ${RED}${BOLD}FAIL${RESET}  $1"; fail=1; }

echo "${BOLD}1. GBrain up on :3131${RESET}"
if curl -fsS --max-time 3 http://localhost:3131/health >/dev/null 2>&1; then
    pass "GBrain /health responded"
else
    bad "GBrain not reachable at http://localhost:3131/health"
fi

echo "${BOLD}2. walls/attack.py${RESET}"
if [ -f walls/attack.py ]; then
    if uv run python walls/attack.py >/tmp/wall_attack_out.$$ 2>&1; then
        pass "wall attack: all checks PASS"
    else
        bad "wall attack reported a failure (see output below)"
        tail -n 20 /tmp/wall_attack_out.$$
    fi
    rm -f /tmp/wall_attack_out.$$
else
    bad "walls/attack.py not found"
fi

echo "${BOLD}3. API up on :$API_PORT${RESET}"
if curl -fsS --max-time 3 "http://localhost:$API_PORT/docs" >/dev/null 2>&1 \
    || curl -s -o /dev/null -w '%{http_code}' --max-time 3 "http://localhost:$API_PORT/check" | grep -qE '^(200|405|422)$'; then
    pass "API responding on :$API_PORT"
else
    bad "API not reachable on :$API_PORT (run scripts/demo.sh)"
fi

echo "${BOLD}4. Results file has a regex/hard row${RESET}"
if [ -f "$RESULTS_FILE" ] && python3 -c "
import json, sys
data = json.load(open('$RESULTS_FILE'))
sys.exit(0 if 'hard' in data.get('regex', {}) else 1)
" 2>/dev/null; then
    pass "$RESULTS_FILE has regex/hard"
else
    bad "$RESULTS_FILE missing or has no regex/hard row"
fi

echo "${BOLD}5. .env has required keys (names only)${RESET}"
if [ -f "$ENV_FILE" ]; then
    keys="$(grep -oE '^[A-Z_]+=' "$ENV_FILE" | tr -d '=' | sort -u | tr '\n' ' ')"
    if [ -n "$keys" ]; then
        pass "keys present: $keys"
    else
        bad "$ENV_FILE has no KEY= lines"
    fi
    for k in ANTHROPIC_API_KEY RIVER_API_KEY; do
        grep -q "^${k}=" "$ENV_FILE" && pass "$k is set" || warn "$k not found in .env"
    done
else
    bad "$ENV_FILE not found"
fi

echo "${BOLD}6. Data files present (names only)${RESET}"
if [ -d "$DATA_DIR" ]; then
    names="$(ls "$DATA_DIR" | tr '\n' ' ')"
    if [ -n "$names" ]; then
        pass "files in $DATA_DIR: $names"
    else
        bad "$DATA_DIR is empty"
    fi
else
    bad "$DATA_DIR not found"
fi

echo
if [ "$fail" -eq 0 ]; then
    echo "${GREEN}${BOLD}##### PREFLIGHT: ALL CHECKS PASS #####${RESET}"
else
    echo "${RED}${BOLD}##### PREFLIGHT: SOME CHECKS FAILED #####${RESET}"
fi
exit "$fail"
