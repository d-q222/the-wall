import json

import pytest

from wall import deid as deid_module
from wall.contract import DeidentifyRequest, JudgeResponse
from wall.deid import deidentify
from wall.matters import documents, matters


@pytest.fixture(autouse=True)
def clean_judge(monkeypatch):
    """No live LLM calls: the judge returns clean unless a test overrides it."""
    calls = []

    def fake(req):
        calls.append(req.draft)
        return JudgeResponse(verdict="clean")

    monkeypatch.setattr(deid_module.judge_module, "judge", fake)
    return calls


def _all_fact_strings() -> list[str]:
    strings = []
    for matter in matters().values():
        for values in matter.get("facts", {}).values():
            strings.extend(v for v in values if v)
    return strings


def _delmarva_session_log() -> str:
    return documents("delmarva")["session-demand-letter.md"]


def test_session_log_removes_every_matter_fact_string():
    resp = deidentify(DeidentifyRequest(text=_delmarva_session_log(), matter_id="delmarva"))

    for fact in _all_fact_strings():
        assert fact not in resp.text


def test_spans_point_at_the_right_original_substrings():
    text = _delmarva_session_log()
    resp = deidentify(DeidentifyRequest(text=text, matter_id="delmarva"))

    assert resp.spans, "expected at least one detected span"
    for span in resp.spans:
        matched = text[span.start : span.end]
        assert matched  # non-empty, offsets are into the ORIGINAL text
        assert span.replacement.startswith("[") and span.replacement.endswith("]")


def test_placeholders_are_consistent_for_a_repeated_entity():
    text = "Marcus Pruitt signed the letter. Marcus Pruitt also filed the exhibit."
    resp = deidentify(DeidentifyRequest(text=text, matter_id="delmarva"))

    pruitt_spans = [s for s in resp.spans if text[s.start : s.end] == "Marcus Pruitt"]
    assert len(pruitt_spans) == 2
    assert pruitt_spans[0].replacement == pruitt_spans[1].replacement
    assert "Marcus Pruitt" not in resp.text
    assert resp.text.count(pruitt_spans[0].replacement) == 2


def test_distinct_entities_of_the_same_kind_get_distinct_placeholders():
    text = "Marcus Pruitt met with Dana Whitcombe about the schedule."
    resp = deidentify(DeidentifyRequest(text=text, matter_id="delmarva"))

    pruitt = next(s.replacement for s in resp.spans if text[s.start : s.end] == "Marcus Pruitt")
    whitcombe = next(
        s.replacement for s in resp.spans if text[s.start : s.end] == "Dana Whitcombe"
    )
    assert pruitt != whitcombe


def test_no_matter_id_still_scrubs_cross_client_facts():
    # No matter_id given: detection still runs over every fixture matter's
    # facts, so a cross-client name can never survive.
    resp = deidentify(DeidentifyRequest(text=_delmarva_session_log()))

    for fact in _all_fact_strings():
        assert fact not in resp.text


def test_judge_failure_is_tolerated(monkeypatch):
    def boom(req):
        raise RuntimeError("judge down")

    monkeypatch.setattr(deid_module.judge_module, "judge", boom)
    resp = deidentify(DeidentifyRequest(text=_delmarva_session_log(), matter_id="delmarva"))

    assert resp.residual is None
    assert resp.judge is None
    assert resp.removed > 0


def test_clean_verdict_is_reported(clean_judge):
    resp = deidentify(DeidentifyRequest(text=_delmarva_session_log(), matter_id="delmarva"))

    assert resp.residual.verdict == "clean"
    assert resp.judge
    assert len(clean_judge) == 1


def test_partial_names_and_org_short_forms_share_the_full_placeholder():
    text = (
        "Adaeze Umeh founded Terraform Grid Systems, Inc. "
        "Before Terraform, Adaeze led grid software at Voltaic. Umeh's work is cited."
    )
    resp = deidentify(DeidentifyRequest(text=text, matter_id="o1-umeh"))

    for leftover in ("Adaeze", "Umeh", "Terraform", "Voltaic"):
        assert leftover not in resp.text
    by_text = {text[s.start : s.end]: s.replacement for s in resp.spans}
    assert by_text["Adaeze"] == by_text["Adaeze Umeh"] == by_text["Umeh"]
    assert by_text["Terraform"] == by_text["Terraform Grid Systems, Inc."]


def test_judge_flagged_evidence_is_redacted_and_rejudged(monkeypatch):
    text = "Adaeze Umeh is the only founder in Lagos who rebuilt the national grid twice."
    evidence = "the only founder in Lagos who rebuilt the national grid twice"
    drafts = []

    def fake(req):
        drafts.append(req.draft)
        if evidence in req.draft:
            return JudgeResponse(verdict="leak", matter="M1", evidence=evidence)
        return JudgeResponse(verdict="clean")

    monkeypatch.setattr(deid_module.judge_module, "judge", fake)
    resp = deidentify(DeidentifyRequest(text=text, matter_id="o1-umeh"))

    assert len(drafts) == 2
    assert evidence not in resp.text
    assert resp.residual.verdict == "clean"
    flag = next(s for s in resp.spans if s.kind == "judge_flag")
    assert text[flag.start : flag.end] == evidence
    assert flag.replacement.startswith("[QUASI_IDENTIFIER")


def test_judge_evidence_spanning_a_placeholder_maps_back_to_original(monkeypatch):
    text = "Letter: Adaeze Umeh rebuilt the Lagos grid twice. End."

    def fake(req):
        if "rebuilt the Lagos grid" in req.draft:
            # Evidence quoted from the de-identified draft, including a placeholder.
            start = req.draft.index("[")
            end = req.draft.index("twice") + len("twice")
            return JudgeResponse(verdict="leak", matter="M1", evidence=req.draft[start:end])
        return JudgeResponse(verdict="clean")

    monkeypatch.setattr(deid_module.judge_module, "judge", fake)
    resp = deidentify(DeidentifyRequest(text=text, matter_id="o1-umeh"))

    flag = next(s for s in resp.spans if s.kind == "judge_flag")
    assert text[flag.start : flag.end] == "Adaeze Umeh rebuilt the Lagos grid twice"
    assert resp.text == f"Letter: {flag.replacement}. End."


def test_run_cli_writes_cleaned_rows_and_prints_summary(tmp_path, capsys):
    from deid.run import main

    infile = tmp_path / "in.jsonl"
    outfile = tmp_path / "out.jsonl"
    infile.write_text(
        json.dumps({"text": _delmarva_session_log(), "matter_id": "delmarva"}) + "\n"
    )

    main([str(infile), str(outfile), "--practice", "immigration"])

    rows = [json.loads(line) for line in outfile.read_text().splitlines()]
    assert len(rows) == 1
    for fact in _all_fact_strings():
        assert fact not in rows[0]["text"]
    assert rows[0]["removed"] > 0
    assert rows[0]["residual_verdict"] == "clean"

    out = capsys.readouterr().out
    assert "docs=1" in out
    assert "residual_leaks=0" in out
