"""Firm compounding policy: what may cross matters, per practice area.

Owned by g2-policy. Served at GET/POST /demo/api/policy.

get() returns fixtures/policy.json merged with the firm's override file
(/Users/dqi26/the-wall/.runtime/policy_override.json); an override entry
replaces that whole practice area. save(policy) validates the shape
{practice: {may_compound: [...], never_compounds: [...]}} and writes the
override file. Fixtures are never edited.
"""

import json
from copy import deepcopy
from pathlib import Path

FIXTURES_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "policy.json"
OVERRIDE_PATH = Path("/Users/dqi26/the-wall/.runtime/policy_override.json")

REQUIRED_LISTS = ("may_compound", "never_compounds")


def _read_json(path: Path) -> dict:
    try:
        text = path.read_text()
    except FileNotFoundError:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid policy JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"policy in {path} must be a JSON object")
    return data


def _validate(policy: dict) -> dict:
    if not isinstance(policy, dict) or not policy:
        raise ValueError("policy must be a non-empty object of practice -> lists")
    for practice, entry in policy.items():
        if not isinstance(practice, str) or not practice.strip():
            raise ValueError(f"practice name must be a non-empty string, got {practice!r}")
        if not isinstance(entry, dict):
            raise ValueError(f"practice {practice!r} must be an object")
        for key in REQUIRED_LISTS:
            if key not in entry:
                raise ValueError(f"practice {practice!r} is missing {key!r}")
            items = entry[key]
            if not isinstance(items, list) or not all(
                isinstance(item, str) and item.strip() for item in items
            ):
                raise ValueError(
                    f"practice {practice!r} field {key!r} must be a list of non-empty strings"
                )
    return policy


def get() -> dict:
    """Fixtures merged with the override file (override wins per practice)."""
    merged = deepcopy(_read_json(FIXTURES_PATH))
    for practice, entry in _read_json(OVERRIDE_PATH).items():
        merged[practice] = deepcopy(entry)
    return merged


def save(policy: dict) -> dict:
    """Validate and persist the override file; never edits fixtures."""
    _validate(policy)
    OVERRIDE_PATH.parent.mkdir(parents=True, exist_ok=True)
    OVERRIDE_PATH.write_text(json.dumps(policy, indent=2, sort_keys=True) + "\n")
    return get()
