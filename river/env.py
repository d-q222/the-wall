"""Load secrets from the hackathon's shared .env without a new dependency."""

import os
from pathlib import Path

DEFAULT_ENV_PATH = Path("/Users/dqi26/the-wall/.env")


def load_dotenv(path: Path = DEFAULT_ENV_PATH) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)
