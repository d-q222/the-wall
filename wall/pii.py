"""Owned by C3. Generic PII detection (no known-fact list needed). Stub until that branch lands."""

from typing import NamedTuple


class Span(NamedTuple):
    start: int
    end: int
    kind: str  # name, org, email, phone, ssn, a_number, receipt, passport, date, address, url, amount


def find(text: str) -> list[Span]:
    """Non-overlapping PII spans in `text`, sorted by start."""
    raise NotImplementedError("C3 implements find")
