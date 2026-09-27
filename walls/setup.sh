#!/usr/bin/env bash
# From-scratch GBrain wall: one isolated source + one read-scoped OAuth client per matter,
# then `gbrain serve --http` in the background.
# NOT RUN ON THE DEMO MACHINE: the live wall there was built by hand with these same steps.
# Usage: walls/setup.sh [--init]      (--init also runs `gbrain init --pglite --no-embedding`)
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
RT="${WALL_RUNTIME:-/Users/dqi26/.superset/projects/The-Wall/.runtime}"
PORT="${GBRAIN_PORT:-3131}"
# /token is rate-limited per IP (default 50 per 15 min) and every localhost lane shares
# that bucket; the limit is read only at startup, so raise it for every serve we launch.
export GBRAIN_OAUTH_TOKEN_RATE_LIMIT_MAX="${GBRAIN_OAUTH_TOKEN_RATE_LIMIT_MAX:-100000}"
MATTERS="chen delmarva reyes"

# Refuse to touch a live wall (PGLite is single-process; CLI commands fail while serve runs).
if curl -fsS "http://localhost:$PORT/health" >/dev/null 2>&1; then
  echo "gbrain serve is already running on :$PORT. Stop it first: kill \$(cat $RT/gbrain-serve.pid)" >&2
  exit 1
fi

mkdir -p "$RT/matters" "$RT/clients" "$RT/logs"
chmod 700 "$RT/clients"

[[ "${1:-}" == "--init" ]] && gbrain init --pglite --no-embedding

for m in $MATTERS; do
  # 1. Matter folder as a git repo with a commit (required before `sources add`).
  dir="$RT/matters/$m"
  mkdir -p "$dir"
  cp "$REPO/fixtures/matters/$m/"*.md "$dir/"
  git -C "$dir" init -q
  git -C "$dir" add -A
  git -C "$dir" -c user.name=wall -c user.email=wall@localhost commit -qm "matter $m" || true

  # 2. Isolated source, synced from the folder.
  gbrain sources add "$m" --path "$dir" --no-federated
  gbrain sync --source "$m" --no-pull

  # 3. Read-only OAuth client that can only see its own source. Secret never hits stdout.
  out="$(gbrain auth register-client "$m-agent" --scopes read --source "$m" --federated-read "$m")"
  cid="$(awk -F': *' '/Client ID:/ {print $2}' <<<"$out" | tr -d ' ')"
  sec="$(awk -F': *' '/Client Secret:/ {print $2}' <<<"$out" | tr -d ' ')"
  [[ -n "$cid" && -n "$sec" ]] || { echo "could not parse client for $m" >&2; exit 1; }
  (umask 077
   printf '{"url": "http://localhost:%s/mcp", "client_id": "%s", "client_secret": "%s", "source_id": "%s"}\n' \
     "$PORT" "$cid" "$sec" "$m" > "$RT/clients/$m.json")
  echo "matter $m: source + client ready ($RT/clients/$m.json)"
done

gbrain sources list

# 4. Serve over HTTP (OAuth 2.1). macOS has no setsid: nohup + disown keeps it alive.
nohup gbrain serve --http --port "$PORT" > "$RT/logs/gbrain-serve.log" 2>&1 < /dev/null &
echo $! > "$RT/gbrain-serve.pid"
disown
for _ in $(seq 1 30); do
  curl -fsS "http://localhost:$PORT/health" >/dev/null 2>&1 && { echo "serve up on :$PORT (pid $(cat "$RT/gbrain-serve.pid"))"; exit 0; }
  sleep 1
done
echo "serve did not come up; see $RT/logs/gbrain-serve.log" >&2
exit 1
