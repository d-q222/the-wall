"""Owned by C2.

De-identification pipeline for the O-1 demo (PRD "O-1 de-identification demo"):
DETECT known + generic PII spans, REPLACE each distinct entity with a
consistent typed placeholder, VERIFY the result with the judge, and REDACT any
span the judge still flags as leaking (then verify once more).
"""

import os
import re

from wall import judge as judge_module
from wall import pii
from wall.contract import (
    DeidentifyRequest,
    DeidentifyResponse,
    DeidSpan,
    JudgeRequest,
    JudgeResponse,
)
from wall.matters import matters

# Fact-list category name -> singular kind used for the placeholder and DeidSpan.kind.
_CATEGORY_KIND = {
    "names": "name",
    "orgs": "org",
    "amounts": "amount",
    "distinctive": "quasi_identifier",
}


def _kind_for_category(category: str) -> str:
    if category in _CATEGORY_KIND:
        return _CATEGORY_KIND[category]
    # Naive depluralization so unseen fact categories (e.g. future
    # "recommenders", "awards") still get a sensible singular kind.
    return category[:-1] if category.endswith("s") and len(category) > 1 else category


def _fact_candidates(matter_id: str | None) -> list[tuple[str, str]]:
    """(fact string, kind) pairs from the named matter plus every fixture matter.

    Every fixture matter is always included so a cross-client name can never
    survive de-identification, even when it was never a fact of `matter_id`.
    """
    seen: dict[str, str] = {}
    all_matters = matters()

    def add(facts: dict) -> None:
        for category, values in facts.items():
            kind = _kind_for_category(category)
            for value in values or []:
                if value and value not in seen:
                    seen[value] = kind

    if matter_id and matter_id in all_matters:
        add(all_matters[matter_id].get("facts", {}))
    for matter in all_matters.values():
        add(matter.get("facts", {}))

    return list(seen.items())


# Capitalized words that are too common to redact on their own as a partial name/org.
_COMMON = {
    "the", "and", "for", "with", "from", "this", "that", "dear", "grant", "group",
    "inc", "llc", "labs", "systems", "ventures", "capital", "partners", "university",
    "institute", "center", "company", "corporation", "bank", "global", "national",
    "hospitality", "culinary", "arts", "bistro", "grid", "software", "association",
}
_TITLES = {"dr", "mr", "mrs", "ms", "prof", "jr", "sr"}


def _partials(value: str, kind: str) -> list[str]:
    """Short forms of a known entity: a person's first/last name tokens, an
    org's distinctive words (e.g. "Terraform" for "Terraform Grid Systems, Inc.",
    "Guild" for "Continental Guild of Culinary Arts")."""
    tokens = [t.strip(".,&()'") for t in value.split()]
    tokens = [t for t in tokens if t and t.lower() not in _TITLES]
    if len(tokens) < 2:
        return []
    if kind == "name":
        picks = [tokens[0], tokens[-1]]
    elif kind == "org":
        picks = tokens
    else:
        return []
    return [t for t in picks if len(t) >= 3 and t[0].isupper() and t.lower() not in _COMMON]


def _pii_candidates(text: str) -> list[tuple[int, int, str]]:
    try:
        spans = pii.find(text)
    except NotImplementedError:
        return []
    return [(s.start, s.end, s.kind) for s in spans]


def _find_all(text: str, needle: str) -> list[tuple[int, int]]:
    if not needle:
        return []
    out = []
    start = 0
    while True:
        idx = text.find(needle, start)
        if idx == -1:
            break
        out.append((idx, idx + len(needle)))
        start = idx + 1
    return out


def _river_candidates(text: str, practice: str) -> list[tuple[int, int, str]]:
    """Optional detector hook for K3's River de-identifier (a live River call), so it is
    opt-in via WALL_DEID_RIVER=1; skipped when off, absent or failing."""
    if os.environ.get("WALL_DEID_RIVER") != "1":
        return []
    try:
        from wall import river_deid  # type: ignore[attr-defined]
    except ImportError:
        return []
    try:
        spans = river_deid.spans(text, practice)
    except Exception:
        return []
    out = []
    for s in spans or []:
        get = s.get if isinstance(s, dict) else lambda k, s=s: getattr(s, k, None)
        if get("start") is not None and get("end") is not None:
            out.append((int(get("start")), int(get("end")), str(get("kind"))))
        elif get("text"):
            # K3 returns span text without offsets: mark every occurrence.
            out += [(a, b, str(get("kind") or "quasi_identifier")) for a, b in _find_all(text, str(get("text")))]
    return out


def _detect(
    text: str, matter_id: str | None, practice: str = "immigration"
) -> list[tuple[int, int, str, str]]:
    """(start, end, kind, entity key) candidates; may overlap. The entity key is
    the full fact string for known facts and their partial forms, so a short
    mention shares the full entity's placeholder; otherwise the matched text."""
    candidates: list[tuple[int, int, str, str]] = []

    facts = _fact_candidates(matter_id)
    for value, kind in facts:
        for start, end in _find_all(text, value):
            candidates.append((start, end, kind, value))

    claimed: set[str] = set()
    for value, kind in facts:
        for part in _partials(value, kind):
            if part in claimed:
                continue  # first entity to claim a short form keeps it
            claimed.add(part)
            for m in re.finditer(rf"\b{re.escape(part)}\b", text):
                candidates.append((m.start(), m.end(), kind, value))

    for start, end, kind in _pii_candidates(text) + _river_candidates(text, practice):
        candidates.append((start, end, kind, text[start:end]))

    return candidates


def _merge(candidates: list[tuple[int, int, str, str]]) -> list[tuple[int, int, str, str]]:
    """Resolve overlaps: longest match wins at each start position."""
    ordered = sorted(candidates, key=lambda c: (c[0], -(c[1] - c[0])))
    accepted: list[tuple[int, int, str, str]] = []
    last_end = -1
    for start, end, kind, matched in ordered:
        if start >= last_end:
            accepted.append((start, end, kind, matched))
            last_end = end
    return accepted


def _assign_placeholders(spans: list[tuple[int, int, str, str]]) -> dict[str, str]:
    """Same entity -> same placeholder; typed by kind, numbered when a kind
    covers more than one distinct entity."""
    by_base: dict[str, list[str]] = {}
    for _, _, kind, matched in spans:
        base = "QUASI_IDENTIFIER" if kind == "judge_flag" else kind.upper()
        values = by_base.setdefault(base, [])
        if matched not in values:
            values.append(matched)

    mapping: dict[str, str] = {}
    for base, values in by_base.items():
        if len(values) == 1:
            mapping[values[0]] = f"[{base}]"
        else:
            for i, value in enumerate(values, start=1):
                mapping[value] = f"[{base}_{i}]"
    return mapping


def _replace(
    text: str, spans: list[tuple[int, int, str, str]], mapping: dict[str, str]
) -> tuple[str, list[DeidSpan]]:
    ordered = sorted(spans, key=lambda s: s[0])
    out_text: list[str] = []
    out_spans: list[DeidSpan] = []
    cursor = 0
    for start, end, kind, matched in ordered:
        replacement = mapping[matched]
        out_text.append(text[cursor:start])
        out_text.append(replacement)
        out_spans.append(DeidSpan(start=start, end=end, kind=kind, replacement=replacement))
        cursor = end
    out_text.append(text[cursor:])
    return "".join(out_text), out_spans


def _to_original(spans: list[DeidSpan], start: int, end: int) -> tuple[int, int]:
    """Map a [start, end) range of the de-identified text back to the original,
    widening to whole placeholders when the range touches one."""
    shift = 0  # de-identified offset minus original offset, before the current span
    orig_start = orig_end = None
    for span in sorted(spans, key=lambda s: s.start):
        d_start = span.start + shift
        d_end = d_start + len(span.replacement)
        if orig_start is None:
            if start < d_start:
                orig_start = start - shift
            elif start < d_end:
                orig_start = span.start
        if orig_end is None:
            if end <= d_start:
                orig_end = end - shift
            elif end <= d_end:
                orig_end = span.end
        shift += len(span.replacement) - (span.end - span.start)
    if orig_start is None:
        orig_start = start - shift
    if orig_end is None:
        orig_end = end - shift
    return orig_start, orig_end


def _identity_block(matter_id: str, matter: dict) -> str:
    facts = matter.get("facts", {})
    name = matter.get("client", matter_id)
    org = (facts.get("orgs") or [""])[0]
    amount = (facts.get("amounts") or [""])[0]
    amount_str = amount.lstrip("$") if amount else ""
    return (
        f"M1: Client {name} ({org}) v. USCIS, beneficiary. "
        f"Matter type: O-1 petition. Confidential: salary ${amount_str}."
    )


def _judge(protected: list[str], draft: str) -> JudgeResponse | None:
    try:
        return judge_module.judge(JudgeRequest(current="", protected=protected, draft=draft))
    except Exception:
        return None  # demo-safe: no verdict rather than a failed request


def _redact(text: str, candidates: list[tuple[int, int, str, str]]):
    spans = _merge(candidates)
    return _replace(text, spans, _assign_placeholders(spans))


def deidentify(req: DeidentifyRequest) -> DeidentifyResponse:
    candidates = _detect(req.text, req.matter_id, req.practice)
    text, out_spans = _redact(req.text, candidates)

    matter = matters().get(req.matter_id) if req.matter_id else None
    protected = [_identity_block(req.matter_id, matter)] if matter else []

    # VERIFY, then REDACT what the judge still flags and verify once more.
    residual = _judge(protected, text)
    if residual and residual.verdict == "leak" and residual.evidence:
        idx = text.find(residual.evidence.strip())
        if idx != -1:
            start, end = _to_original(out_spans, idx, idx + len(residual.evidence.strip()))
            flagged = req.text[start:end]
            candidates.append((start, end, "judge_flag", flagged))
            text, out_spans = _redact(req.text, candidates)
            residual = _judge(protected, text) or residual

    return DeidentifyResponse(
        text=text,
        spans=out_spans,
        removed=len(out_spans),
        residual=residual,
        judge=os.environ.get("WALL_JUDGE", "prompt_judge") if residual else None,
    )
