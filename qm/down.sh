#!/usr/bin/env bash
# Stop QM's dev instance app layer. Leaves the shared qm-dev-postgres container running
# (other worktrees/tasks may reuse it) -- only `docker stop qm-dev-postgres` removes that.
set -euo pipefail

QM_DIR="/Users/dqi26/the-wall/.runtime/qm"
cd "$QM_DIR"

echo "[qm/down] stopping dev instance..."
npm run dev-instance:down
