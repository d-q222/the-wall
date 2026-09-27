"""Owned by B3.

Deterministic, rule-based scrubber (PRD FR-6): strips a matter's own names,
orgs, amounts and distinctive details, plus generic proper nouns/dates/
amount formats/exhibit references, so a procedure can compound across
matters while the facts stay put. No LLM paraphrasing here by design.
"""

import re

from wall.contract import ScrubRequest, ScrubResponse
from wall.matters import matters, policy

_MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|November|December"
    "|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
)
_DATE_RE = re.compile(
    rf"\b(?:{_MONTHS})\.?\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{4}})?\b"
    rf"|\b\d{{1,2}}[/-]\d{{1,2}}(?:[/-]\d{{2,4}})?\b"
)
_AMOUNT_RE = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?\s?(?:million|billion|M|K)?\b", re.IGNORECASE)
_EXHIBIT_RE = re.compile(r"\bExhibit\s+[A-Za-z0-9]+\b")
_SECTION_RE = re.compile(r"\bSection\s+\d+(?:\.\d+)*\b")
_MULTIWORD_PROPER_NOUN_RE = re.compile(r"\b[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*){1,3}\b")
_PROPER_TOKEN_RE = re.compile(r"\b[A-Z][a-zA-Z]{2,}\b")
_LEGAL_SUFFIXES = {"Inc", "Corp", "Ltd", "Co"}


def _replace_all(text: str, strings: list[str], placeholder: str) -> tuple[str, int]:
    removed = 0
    for s in sorted({s for s in strings if s}, key=len, reverse=True):
        text, n = re.compile(re.escape(s)).subn(placeholder, text)
        removed += n
    return text, removed


def _proper_tokens(strings: list[str]) -> set[str]:
    tokens: set[str] = set()
    for s in strings:
        for tok in _PROPER_TOKEN_RE.findall(s):
            if tok.isupper() or tok in _LEGAL_SUFFIXES:
                continue
            tokens.add(tok)
    return tokens


def scrub(req: ScrubRequest) -> ScrubResponse:
    if req.practice not in policy():
        raise ValueError(f"unknown practice {req.practice!r}")
    matter = matters().get(req.matter_id)
    if matter is None:
        raise ValueError(f"unknown matter_id {req.matter_id!r}")

    # Every defined practice's never_compounds fully covers this fixed facts
    # schema (names/orgs/amounts/distinctive), so scrubbing all of them for
    # every practice is equivalent to mapping policy categories one by one.
    facts = matter.get("facts", {})
    text = req.text
    removed = 0

    text, n = _replace_all(text, facts.get("names", []) + facts.get("orgs", []), "the counterparty")
    removed += n
    text, n = _replace_all(text, facts.get("amounts", []), "[amount]")
    removed += n
    text, n = _replace_all(text, facts.get("distinctive", []), "[redacted detail]")
    removed += n

    # Leftover single-word fragments of the matter's own proper nouns, e.g.
    # "Delmarva" surviving after the full "Delmarva Logistics" phrase above
    # was already replaced elsewhere in the text.
    leftover = _proper_tokens(facts.get("names", []) + facts.get("orgs", []) + facts.get("distinctive", []))
    text, n = _replace_all(text, list(leftover), "Counterparty")
    removed += n

    for pattern, placeholder in (
        (_EXHIBIT_RE, "the exhibit"),
        (_SECTION_RE, "the relevant section"),
        (_DATE_RE, "[date]"),
        (_AMOUNT_RE, "[amount]"),
    ):
        text, n = pattern.subn(placeholder, text)
        removed += n

    text, n = _MULTIWORD_PROPER_NOUN_RE.subn("the counterparty", text)
    removed += n

    # Cosmetic only: original text often already had "the" right before the
    # proper noun we just replaced with "the counterparty".
    text = re.sub(r"\bthe\s+the\s+counterparty\b", "the counterparty", text, flags=re.IGNORECASE)

    return ScrubResponse(text=text, removed=removed)
