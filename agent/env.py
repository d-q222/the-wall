"""Load secrets from the shared, gitignored .env — never print or commit them."""

import os
from pathlib import Path

ENV_PATH = Path("/Users/dqi26/the-wall/.env")


def load_env() -> None:
    """Populate os.environ from ENV_PATH, without overriding already-set vars."""
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())
