import json

from wall.contract import DeidentifyRequest
from wall.deid import deidentify
from wall.matters import documents, matters


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


def test_judge_stub_is_tolerated():
    resp = deidentify(DeidentifyRequest(text=_delmarva_session_log(), matter_id="delmarva"))

    assert resp.residual is None
    assert resp.judge is None


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
    assert rows[0]["residual_verdict"] is None

    out = capsys.readouterr().out
    assert "docs=1" in out
    assert "residual_leaks=0" in out
