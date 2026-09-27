#!/usr/bin/env bash
# Add the O-1 beneficiary matters (fixtures/matters/o1-*/) as isolated GBrain sources on the
# ALREADY-RUNNING live wall server. NOT run by this worker: the GBrain server on :3131 is owned
# by another session. Hand this to that session (stop serve, run this, restart serve).
#
# PGLite is single-process (see walls/README.md "Ops caveat"): `sources`/`sync`/`auth` CLI
# commands fail while `gbrain serve` is up, so this script stops the server first and restarts
# it when done, using the same nohup/disown incantation as walls/setup.sh.
#
# Usage: walls/o1/add_sources.sh
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
RT="${WALL_RUNTIME:-/Users/dqi26/.superset/projects/The-Wall/.runtime}"
PORT="${GBRAIN_PORT:-3131}"
# /token is rate-limited per IP (default 50 per 15 min) and every localhost lane shares
# that bucket; the limit is read only at startup, so raise it for every serve we launch.
export GBRAIN_OAUTH_TOKEN_RATE_LIMIT_MAX="${GBRAIN_OAUTH_TOKEN_RATE_LIMIT_MAX:-100000}"
PIDFILE="$RT/gbrain-serve.pid"

# Discover the O-1 matters landed by c1-o1-corpus; don't hardcode ids.
shopt -s nullglob
MATTER_DIRS=("$REPO"/fixtures/matters/o1-*/)
shopt -u nullglob
if [[ ${#MATTER_DIRS[@]} -eq 0 ]]; then
  echo "no fixtures/matters/o1-*/ found -- nothing to add" >&2
  exit 1
fi

mkdir -p "$RT/matters" "$RT/clients" "$RT/logs"
chmod 700 "$RT/clients"

WAS_RUNNING=0
if curl -fsS "http://localhost:$PORT/health" >/dev/null 2>&1; then
  WAS_RUNNING=1
  echo "stopping gbrain serve (pid $(cat "$PIDFILE" 2>/dev/null || echo '?')) to run CLI commands..."
  pid="$(cat "$PIDFILE")"
  kill "$pid" 2>/dev/null || true
  # Wait for the process to exit, not just /health: it holds the PGLite lock until it does.
  for _ in $(seq 1 30); do
    kill -0 "$pid" 2>/dev/null || break
    sleep 1
  done
fi

for dir in "${MATTER_DIRS[@]}"; do
  m="$(basename "$dir")"

  # 1. Matter folder as a git repo with a commit (required before `sources add`).
  rt_dir="$RT/matters/$m"
  mkdir -p "$rt_dir"
  cp "$dir"*.md "$rt_dir/"   # .md only, like walls/setup.sh (matter.json is the answer key)
  git -C "$rt_dir" init -q
  git -C "$rt_dir" add -A
  git -C "$rt_dir" -c user.name=wall -c user.email=wall@localhost commit -qm "matter $m" || true

  # 2. Isolated source, synced from the folder.
  gbrain sources add "$m" --path "$rt_dir" --no-federated
  gbrain sync --source "$m" --no-pull

  # 3. Read-only OAuth client that can only see its own source. Secret never hits stdout.
  out="$(gbrain auth register-client "$m-agent" --scopes read --source "$m" --federated-read "$m")"
  cid="$(awk -F': *' '/Client ID:/ {print $2}' <<<"$out" | tr -d ' ')"
  sec="$(awk -F': *' '/Client Secret:/ {print $2}' <<<"$out" | tr -d ' ')"
  [[ -n "$cid" && -n "$sec" ]] || { echo "could not parse client for $m" >&2; exit 1; }
  (umask 077
   printf '{"url": "http://localhost:%s/mcp", "client_id": "%s", "client_secret": "%s", "source_id": "%s"}\n' \
     "$PORT" "$cid" "$sec" "$m" > "$RT/clients/$m.json")
  chmod 600 "$RT/clients/$m.json"
  echo "matter $m: source + client ready ($RT/clients/$m.json)"
done

gbrain sources list

if [[ "$WAS_RUNNING" -eq 1 ]]; then
  echo "restarting gbrain serve..."
  nohup gbrain serve --http --port "$PORT" > "$RT/logs/gbrain-serve.log" 2>&1 < /dev/null &
  echo $! > "$PIDFILE"
  disown
  for _ in $(seq 1 30); do
    curl -fsS "http://localhost:$PORT/health" >/dev/null 2>&1 && { echo "serve up on :$PORT (pid $(cat "$PIDFILE"))"; exit 0; }
    sleep 1
  done
  echo "serve did not come back up; see $RT/logs/gbrain-serve.log" >&2
  exit 1
fi
