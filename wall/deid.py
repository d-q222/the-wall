"""Owned by C2.

De-identification pipeline for the O-1 demo (PRD "O-1 de-identification demo"):
DETECT known + generic PII spans, REPLACE each distinct entity with a
consistent typed placeholder, VERIFY the result with the judge (stub-tolerant
until B2/C3 land).
"""

import os

from wall import judge as judge_module
from wall import pii
from wall.contract import DeidentifyRequest, DeidentifyResponse, DeidSpan, JudgeRequest
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


def _detect(text: str, matter_id: str | None) -> list[tuple[int, int, str, str]]:
    """(start, end, kind, matched original substring) candidates; may overlap."""
    candidates: list[tuple[int, int, str, str]] = []

    for value, kind in _fact_candidates(matter_id):
        for start, end in _find_all(text, value):
            candidates.append((start, end, kind, text[start:end]))

    for start, end, kind in _pii_candidates(text):
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
    """Same matched string -> same placeholder; typed by kind, numbered when a
    kind covers more than one distinct entity."""
    by_base: dict[str, list[str]] = {}
    for _, _, kind, matched in spans:
        base = kind.upper()
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


def deidentify(req: DeidentifyRequest) -> DeidentifyResponse:
    candidates = _detect(req.text, req.matter_id)
    spans = _merge(candidates)
    mapping = _assign_placeholders(spans)
    text, out_spans = _replace(req.text, spans, mapping)

    matter = matters().get(req.matter_id) if req.matter_id else None
    protected = [_identity_block(req.matter_id, matter)] if matter else []

    residual = None
    judge_name = None
    try:
        residual = judge_module.judge(JudgeRequest(current="", protected=protected, draft=text))
        judge_name = os.environ.get("WALL_JUDGE", "prompt_judge")
    except NotImplementedError:
        residual = None
        judge_name = None

    return DeidentifyResponse(
        text=text,
        spans=out_spans,
        removed=len(out_spans),
        residual=residual,
        judge=judge_name,
    )
