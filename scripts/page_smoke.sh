#!/usr/bin/env bash
# Render every demo page in headless Chrome (1440x900) against a RUNNING API and
# flag pages whose <main> is empty after JS runs -- the symptom of a page that
# doesn't follow the nav.js shell contract (content must sit in <main class="app-main">).
# Read-only: never starts or stops a server. Screenshots land in $OUT for a look.
#   API_PORT=8805 scripts/page_smoke.sh
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

API_PORT="${API_PORT:-8788}"
OUT="${OUT:-.runtime/page_smoke}"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
mkdir -p "$OUT"

curl -fsS --max-time 3 "http://localhost:$API_PORT/docs" >/dev/null \
    || { echo "API not reachable on :$API_PORT" >&2; exit 1; }

fails=0
for path in $(cd demo && ls *.html | sed 's|^|/demo/|') /scoreboard/; do
    url="http://localhost:$API_PORT$path"
    name="$(echo "$path" | tr '/' '_' | sed 's/^_//; s/_$//')"
    "$CHROME" --headless=new --disable-gpu --hide-scrollbars --window-size=1440,900 \
        --virtual-time-budget=8000 --screenshot="$OUT/$name.png" "$url" >/dev/null 2>&1
    chars="$("$CHROME" --headless=new --disable-gpu --virtual-time-budget=8000 --dump-dom "$url" 2>/dev/null \
        | python3 -c '
import re, sys
s = sys.stdin.read()
m = re.search(r"<main[^>]*>(.*?)</main>", s, re.S)
t = re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", m.group(1) if m else "", flags=re.S)
print(len(" ".join(t.split())))')"
    if [ "${chars:-0}" -lt 40 ]; then
        echo "EMPTY  $path  (<main> has $chars chars of text)"; fails=$((fails + 1))
    else
        echo "ok     $path  ($chars chars)"
    fi
done
echo "screenshots: $OUT/"
[ "$fails" = 0 ] && echo "PAGE SMOKE: ALL PAGES RENDER" || { echo "PAGE SMOKE: $fails EMPTY PAGE(S)"; exit 1; }
