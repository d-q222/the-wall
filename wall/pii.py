"""Owned by C3. Generic PII detection (no known-fact list needed).

Deterministic: regex + light heuristics only. No LLM, no NER model downloads.
Precision is prioritized over recall for `name`/`org` — see the docstrings on
`_find_names` and `_find_orgs` for the specific limits this implies.
"""

from __future__ import annotations

import re
from typing import NamedTuple


class Span(NamedTuple):
    start: int
    end: int
    kind: str  # name, org, email, phone, ssn, a_number, receipt, passport, date, address, url, amount


# Lower number = more specific / wins ties on overlap against a higher number,
# regardless of length. Within the same kind, the longer match wins.
_PRIORITY = {
    "a_number": 0,
    "receipt": 1,
    "passport": 2,
    "email": 3,
    "url": 4,
    "ssn": 5,
    "phone": 6,
    "date": 7,
    "amount": 8,
    "address": 9,
    "org": 10,
    "name": 11,
}

_Candidate = tuple[int, int, str]  # start, end, kind


# ---------------------------------------------------------------------------
# Generic PII
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

_URL_RE = re.compile(r"\b(?:https?://|www\.)[^\s<>\"')]+", re.IGNORECASE)

_SSN_RE = re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")

_PHONE_RES = [
    # US: (202) 555-0143 / 202-555-0143 / 202.555.0143, optional +1
    re.compile(r"(?<!\d)(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}(?!\d)"),
    # International: +<country> <2-4> <2-4> <2-4>
    re.compile(r"(?<!\d)\+\d{1,3}[-.\s]?\d{1,4}(?:[-.\s]\d{2,4}){2,3}(?!\d)"),
]

_MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|"
    "November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
)

_DATE_RES = [
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),  # 2024-03-03
    re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"),  # 03/03/2024
    re.compile(rf"\b(?:{_MONTHS})\.?\s+\d{{1,2}},?\s+\d{{4}}\b"),  # March 3, 2024 / Mar. 3 2024
    re.compile(rf"\b\d{{1,2}}\s+(?:{_MONTHS})\.?,?\s+\d{{4}}\b"),  # 3 March 2024
]

_AMOUNT_RES = [
    re.compile(r"\$\s?\d{1,3}(?:,\d{3})*(?:\.\d+)?(?:\s?[kKmMbB]\b)?"),  # $418,250 / $418K
    re.compile(r"\bUSD\s?\d{1,3}(?:,\d{3})*(?:\.\d+)?\b", re.IGNORECASE),  # USD 418,250
    re.compile(r"\b\d{1,3}(?:,\d{3})*\s+(?:thousand|million|billion)\s+dollars\b", re.IGNORECASE),
]

_STREET_SUFFIX = (
    r"Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|Boulevard|Blvd\.?|Lane|Ln\.?|Drive|Dr\.?|"
    r"Court|Ct\.?|Way|Place|Pl\.?|Parkway|Pkwy\.?|Circle|Cir\.?|Terrace|Ter\.?|Square|Sq\.?|"
    r"Highway|Hwy\.?"
)

_ADDRESS_RE = re.compile(
    rf"\b\d{{1,6}}\s+(?:[A-Z][A-Za-z0-9.'-]*\s+){{1,4}}(?:{_STREET_SUFFIX})\b"
    rf"(?:,?\s+(?:Suite|Ste\.?|Apt\.?|Unit|#)\s*\w+)?",
)

# ---------------------------------------------------------------------------
# Immigration identifiers
# ---------------------------------------------------------------------------

# A-Number: "A" + 8-9 digits, dashes/spaces optional in various groupings.
_A_NUMBER_RE = re.compile(
    r"\bA[-\s]?(?:\d{2,3}[-\s]?\d{3}[-\s]?\d{3,4}|\d{8,9})\b"
)

# USCIS receipt number: 3-letter office code + 10 digits.
_RECEIPT_RE = re.compile(
    r"\b(?:EAC|WAC|LIN|SRC|NBC|MSC|IOE|YSC)[-\s]?\d{10}\b", re.IGNORECASE
)

_PASSPORT_CONTEXT_RE = re.compile(r"passport", re.IGNORECASE)
_PASSPORT_TOKEN_RE = re.compile(r"\b[A-Za-z0-9]{6,9}\b")
_PASSPORT_WINDOW = 20


def _find_passport(text: str) -> list[_Candidate]:
    """"passport" within ~20 chars followed by a 6-9 char alphanumeric token.

    The token must contain at least one digit (so plain words like "number"
    are never mistaken for the identifier itself).
    """
    spans: list[_Candidate] = []
    for ctx in _PASSPORT_CONTEXT_RE.finditer(text):
        search_from = ctx.end()
        window = text[search_from : search_from + _PASSPORT_WINDOW + 9]
        for tok in _PASSPORT_TOKEN_RE.finditer(window):
            if tok.start() > _PASSPORT_WINDOW:
                break
            if not any(c.isdigit() for c in tok.group()):
                continue
            start = search_from + tok.start()
            end = search_from + tok.end()
            spans.append((start, end, "passport"))
            break
    return spans


# ---------------------------------------------------------------------------
# Names and orgs
# ---------------------------------------------------------------------------

_TITLE_RE = re.compile(
    r"\b(?:Mr|Ms|Mrs|Dr|Prof)\.?\s+[A-Z][a-z']+(?:\s+[A-Z][a-z']+){0,2}\b"
)
_DEAR_RE = re.compile(r"\bDear\s+([A-Z][a-z']+(?:\s+[A-Z][a-z']+){0,2})\s*[,:]")
_BARE_NAME_RE = re.compile(r"\b[A-Z][a-z']+(?:\s+[A-Z][a-z']+){1,2}\b")

# Words that make a bare capitalized-word run a legal/common term rather than
# a personal name. Checked per-word (case-sensitive on the capitalized form),
# so any match containing one of these is dropped rather than reported.
_NAME_STOPWORDS = {
    "United", "States", "Department", "Homeland", "Security", "Citizenship",
    "Immigration", "Services", "Service", "Exhibit", "Form", "Section",
    "Article", "Attorney", "General", "District", "Court", "Office", "Bureau",
    "Federal", "National", "State", "County", "City", "Board", "Appeals",
    "Case", "Matter", "Petition", "Respondent", "Petitioner", "Applicant",
    "Government", "Agency", "Administration", "Justice", "Labor", "Customs",
    "Border", "Patrol", "University", "Institute", "Foundation", "Corporation",
    "Company", "Inc", "LLC", "Ltd", "Corp", "Act", "Code", "Regulation",
    "Regulations", "Title", "Chapter", "Committee", "Congress", "Senate",
    "House", "President", "Secretary", "Director", "Officer", "Division",
}

_SENTENCE_END = {".", "!", "?"}


def _is_sentence_start(text: str, start: int) -> bool:
    """True if `start` opens a sentence (start of text, or after . / ! / ? + whitespace)."""
    if start == 0:
        return True
    i = start - 1
    while i >= 0 and text[i].isspace():
        i -= 1
    return i < 0 or text[i] in _SENTENCE_END


def _find_names(text: str) -> list[_Candidate]:
    """Capitalized personal names via heuristics; precision over recall.

    Catches: "Mr./Ms./Dr./Prof. Firstname Lastname", "Dear Firstname Lastname,"
    and bare runs of 2-3 Capitalized Words that are not sentence-initial and
    don't contain a word from a small legal/common-term stopword list.

    Known limits (documented, not fixed): misses single-word names, names in
    ALL CAPS, and names that happen to be sentence-initial; can false-positive
    on capitalized non-person phrases not in the stopword list (e.g. place
    names like "New York", product/case names).
    """
    spans: list[_Candidate] = []

    for m in _TITLE_RE.finditer(text):
        spans.append((m.start(), m.end(), "name"))

    for m in _DEAR_RE.finditer(text):
        spans.append((m.start(1), m.end(1), "name"))

    for m in _BARE_NAME_RE.finditer(text):
        words = m.group().split()
        if any(w.strip(".") in _NAME_STOPWORDS for w in words):
            continue
        if _is_sentence_start(text, m.start()):
            continue
        spans.append((m.start(), m.end(), "name"))

    return spans


_ORG_SUFFIX = r"Inc\.?|LLC|Ltd\.?|Corp\.?|University|Institute|Foundation|Labs|Society"
_ORG_RE = re.compile(rf"\b(?:[A-Z][A-Za-z&.'-]*\s+){{1,5}}(?:{_ORG_SUFFIX})\b")


def _find_orgs(text: str) -> list[_Candidate]:
    """Capitalized word run ending in a corporate/institutional suffix.

    Known limits: requires a recognized suffix (misses e.g. "Acme Group" with
    no suffix, or lowercase/informal org mentions); precision over recall.
    """
    return [(m.start(), m.end(), "org") for m in _ORG_RE.finditer(text)]


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def _regex_candidates(pattern: re.Pattern[str], text: str, kind: str) -> list[_Candidate]:
    return [(m.start(), m.end(), kind) for m in pattern.finditer(text)]


def find(text: str) -> list[Span]:
    """Non-overlapping PII spans in `text`, sorted by start.

    On overlap, the more specific kind wins (see `_PRIORITY`); ties within the
    same kind go to the longer match.
    """
    candidates: list[_Candidate] = []
    candidates += _regex_candidates(_EMAIL_RE, text, "email")
    candidates += _regex_candidates(_URL_RE, text, "url")
    candidates += _regex_candidates(_SSN_RE, text, "ssn")
    for pat in _PHONE_RES:
        candidates += _regex_candidates(pat, text, "phone")
    for pat in _DATE_RES:
        candidates += _regex_candidates(pat, text, "date")
    for pat in _AMOUNT_RES:
        candidates += _regex_candidates(pat, text, "amount")
    candidates += _regex_candidates(_ADDRESS_RE, text, "address")
    candidates += _regex_candidates(_A_NUMBER_RE, text, "a_number")
    candidates += _regex_candidates(_RECEIPT_RE, text, "receipt")
    candidates += _find_passport(text)
    candidates += _find_orgs(text)
    candidates += _find_names(text)

    candidates.sort(key=lambda c: (_PRIORITY[c[2]], -(c[1] - c[0])))

    accepted: list[_Candidate] = []
    for start, end, kind in candidates:
        if any(start < a_end and end > a_start for a_start, a_end, _ in accepted):
            continue
        accepted.append((start, end, kind))

    accepted.sort(key=lambda c: c[0])
    return [Span(start=s, end=e, kind=k) for s, e, k in accepted]
