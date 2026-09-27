#!/usr/bin/env bash
# Record a backup video of the live presenter (see README in record.mjs header).
# Usage: tools/record/record.sh            # records http://localhost:8788/demo/present.html
#        WALL_API_URL=http://localhost:8813 tools/record/record.sh
# Env: DWELL_SCALE (1 = each beat's data-target seconds), MAX_BEAT_S (45), HIDE_CHROME (1), KEEP_FRAMES.
set -euo pipefail
cd "$(dirname "$0")"
command -v ffmpeg >/dev/null || brew install ffmpeg
[ -d node_modules/playwright-core ] || npm ci --silent
exec node record.mjs "$@"
