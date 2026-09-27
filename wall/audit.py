"""Owned by G5. Stub until that branch lands.

Interface: record(event: dict) -> None; recent(limit: int = 100) -> list[dict]
"""


def record(event: dict) -> None:
    """Append-only; must never raise into the caller's request path."""


def recent(limit: int = 100) -> list[dict]:
    return []
