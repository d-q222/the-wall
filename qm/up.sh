#!/usr/bin/env bash
# Boot QM's local dev instance (mock LLM, local Postgres) with a seeded org admin and
# a fixed CAPABILITY_SECRET so rooms.py / promote.py can mint capability tokens without
# ever needing the email-link sign-in broker. See qm/README.md.
set -euo pipefail

QM_DIR="/Users/dqi26/the-wall/.runtime/qm"
STATE_DIR="/Users/dqi26/the-wall/.runtime/qm-state"
LOG="$STATE_DIR/up.log"
ADMIN_PRINCIPAL="qm-admin"
CAPABILITY_SECRET="55fde2eb25cdd3c1a0dac5a1c0fb96e18e1eb7094cbd071f70d6efcb5f4756a3"

mkdir -p "$STATE_DIR"
cd "$QM_DIR"

echo "[qm/up] doctor..."
npm run dev-instance:doctor

echo "[qm/up] booting (mock LLM turns, local Postgres, admin=${ADMIN_PRINCIPAL})..."
DEV_INSTANCE_ALLOW_MOCK=1 \
  ADMIN_GRANTS="${ADMIN_PRINCIPAL}:org_admin" \
  CAPABILITY_SECRET="$CAPABILITY_SECRET" \
  DEV_INSTANCE_POSTGRES_CONTAINER="${DEV_INSTANCE_POSTGRES_CONTAINER:-qm-dev-postgres}" \
  npm run dev-instance:no-slack 2>&1 | tee "$LOG"

CORE_URL=$(grep -oE 'core[[:space:]]*:[[:space:]]*http://localhost:[0-9]+' "$LOG" | grep -oE 'http://localhost:[0-9]+' | head -1)
PORTAL_URL=$(grep -oE 'portal[[:space:]]*:[[:space:]]*http://localhost:[0-9]+' "$LOG" | grep -oE 'http://localhost:[0-9]+' | head -1)

if [ -z "$CORE_URL" ]; then
  echo "[qm/up] could not find the core URL in dev-instance output -- see $LOG" >&2
  exit 1
fi

echo -n "$CORE_URL" > "$STATE_DIR/core_url"
[ -n "$PORTAL_URL" ] && echo -n "$PORTAL_URL" > "$STATE_DIR/portal_url"

echo "[qm/up] core:   $CORE_URL"
echo "[qm/up] portal: ${PORTAL_URL:-<none>}"
echo "[qm/up] state:  $STATE_DIR"
