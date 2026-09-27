"""Owned by B1: regex fingerprint + carryover leak detectors behind /check (PRD FR-4, FR-5).

Detection logic is split into two reusable, matter-agnostic functions
(`regex_fingerprint_hits`, `carryover_hits`) so `evals/run_guard.py` can run them
against eval-file facts/corpora that never touch `wall.matters`'s fixtures.
`check()` wires them to the fixture matters for the live /check endpoint.
"""

from __future__ import annotations

import re

from wall import matters as matters_mod
from wall.contract import CheckRequest, CheckResponse, Hit

_WORD_RE = re.compile(r"[A-Za-z0-9']+")
NGRAM_N = 6

Corpus = dict[str, str] | list[str]


def _amount_value(raw: str) -> int | None:
    """'$418,250' -> 418250. None if no digits found."""
    digits = re.sub(r"[^\d]", "", raw)
    return int(digits) if digits else None


def _amount_patterns(raw: str) -> list[re.Pattern[str]]:
    """Regexes matching common ways this amount is written in prose.

    Covers $418,250 / 418250 / $418K / 418 thousand dollars / $1.5 million.
    """
    value = _amount_value(raw)
    if value is None:
        return []
    patterns = {rf"\${value:,}(?:\.\d+)?", rf"(?<!\d){value}(?!\d)"}
    if value % 1000 == 0:
        k = value // 1000
        patterns.add(rf"\${k}\s*[kK]\b")
        patterns.add(rf"\b{k}\s+thousand\s+dollars\b")
        if value >= 1_000_000 and value % 100_000 == 0:
            m_str = f"{value / 1_000_000:g}"
            patterns.add(rf"\${re.escape(m_str)}\s*million\b")
    return [re.compile(p, re.IGNORECASE) for p in patterns]


def regex_fingerprint_hits(
    draft: str,
    current_facts: dict,
    protected_facts: dict[str, dict],
) -> list[Hit]:
    """Flag names/orgs/amounts belonging to OTHER matters in `draft`.

    Always subtracts the current matter's own names/orgs/amounts first: a value
    that also belongs to the current matter is never treated as a leak, even if
    another matter happens to share it (e.g. a reused settlement amount).
    """
    own_names = {n.lower() for n in current_facts.get("names", [])}
    own_orgs = {o.lower() for o in current_facts.get("orgs", [])}
    own_amounts = {v for a in current_facts.get("amounts", []) if (v := _amount_value(a)) is not None}

    hits: list[Hit] = []
    seen_spans: set[tuple[int, int]] = set()

    def emit(matter_id: str, pattern: re.Pattern[str]) -> None:
        for m in pattern.finditer(draft):
            span = m.span()
            if span in seen_spans:
                continue
            seen_spans.add(span)
            hits.append(Hit(detector="regex", matter=matter_id, evidence=m.group()))

    for matter_id, facts in protected_facts.items():
        for name in facts.get("names", []):
            if name.lower() in own_names:
                continue
            emit(matter_id, re.compile(re.escape(name), re.IGNORECASE))
        for org in facts.get("orgs", []):
            if org.lower() in own_orgs:
                continue
            emit(matter_id, re.compile(re.escape(org), re.IGNORECASE))
        for amount in facts.get("amounts", []):
            value = _amount_value(amount)
            if value is None or value in own_amounts:
                continue
            for pattern in _amount_patterns(amount):
                emit(matter_id, pattern)

    return hits


def _tokenize(text: str) -> list[tuple[str, int, int]]:
    return [(m.group().lower(), m.start(), m.end()) for m in _WORD_RE.finditer(text)]


def _ngrams(tokens: list[tuple[str, int, int]], n: int = NGRAM_N):
    for i in range(len(tokens) - n + 1):
        words = tuple(t[0] for t in tokens[i : i + n])
        yield words, tokens[i][1], tokens[i + n - 1][2]


def _corpus_ngrams(corpus: Corpus, n: int = NGRAM_N) -> set[tuple[str, ...]]:
    texts = corpus.values() if isinstance(corpus, dict) else corpus
    grams: set[tuple[str, ...]] = set()
    for text in texts:
        grams.update(words for words, _, _ in _ngrams(_tokenize(text), n))
    return grams


def carryover_hits(
    draft: str,
    current_corpus: Corpus,
    protected_corpora: dict[str, Corpus],
) -> list[Hit]:
    """Flag word 6-grams in `draft` that occur in exactly one other matter's corpus.

    Ignores grams also present in the current matter's own corpus, and grams
    shared by 2+ other matters (firm boilerplate, e.g. a privilege footer).
    """
    current_grams = _corpus_ngrams(current_corpus)
    protected_grams = {mid: _corpus_ngrams(corpus) for mid, corpus in protected_corpora.items()}

    spans: list[tuple[int, int, str]] = []
    for words, start, end in _ngrams(_tokenize(draft)):
        if words in current_grams:
            continue
        owners = [mid for mid, grams in protected_grams.items() if words in grams]
        if len(owners) == 1:
            spans.append((start, end, owners[0]))

    # Adjacent/overlapping n-gram windows from the same matter are one leaked
    # phrase, not several; merge them so a reviewer sees one span, not five.
    merged: list[tuple[int, int, str]] = []
    for start, end, matter_id in spans:
        if merged and merged[-1][2] == matter_id and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end), matter_id)
        else:
            merged.append((start, end, matter_id))

    return [Hit(detector="carryover", matter=matter_id, evidence=draft[start:end]) for start, end, matter_id in merged]


def check(req: CheckRequest) -> CheckResponse:
    all_matters = matters_mod.matters()
    current = all_matters.get(req.matter_id, {})
    current_facts = current.get("facts", {})
    protected_facts = {mid: m.get("facts", {}) for mid, m in all_matters.items() if mid != req.matter_id}

    hits = regex_fingerprint_hits(req.draft, current_facts, protected_facts)

    current_corpus = matters_mod.documents(req.matter_id)
    protected_corpora = {mid: matters_mod.documents(mid) for mid in all_matters if mid != req.matter_id}
    hits += carryover_hits(req.draft, current_corpus, protected_corpora)

    verdict = "leak" if hits else "clean"
    return CheckResponse(verdict=verdict, hits=hits)
