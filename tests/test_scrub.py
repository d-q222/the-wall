import re
from pathlib import Path

import pytest

from wall.contract import ScrubRequest
from wall.matters import matters
from wall.scrub import scrub

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures/matters/delmarva/session-demand-letter.md"


def _all_fact_strings() -> list[str]:
    strings: list[str] = []
    for matter in matters().values():
        for values in matter["facts"].values():
            strings.extend(values)
    return strings


def _count_leaks(text: str) -> int:
    return sum(text.count(s) for s in _all_fact_strings() if s)


def test_scrub_removes_every_matter_fact_and_keeps_steps_readable():
    raw = FIXTURE.read_text()
    raw_leaks = _count_leaks(raw)
    assert raw_leaks > 0, "fixture must contain leakable facts to prove the scrubber does something"

    resp = scrub(ScrubRequest(matter_id="delmarva", practice="litigation", text=raw))

    remaining_leaks = _count_leaks(resp.text)
    print(f"{raw_leaks} raw leaks -> {remaining_leaks}")
    assert remaining_leaks == 0
    assert resp.removed > 0

    steps = re.findall(r"^\d+\.\s+(.+)$", resp.text, re.MULTILINE)
    assert len(steps) == 4
    for step in steps:
        assert len(step.strip()) > 10


def test_scrub_rejects_unknown_matter():
    with pytest.raises(ValueError):
        scrub(ScrubRequest(matter_id="nope", practice="litigation", text="text"))


def test_scrub_rejects_unknown_practice():
    with pytest.raises(ValueError):
        scrub(ScrubRequest(matter_id="delmarva", practice="nope", text="text"))
