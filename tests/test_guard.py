from wall.contract import CheckRequest
from wall.guard import carryover_hits, check, regex_fingerprint_hits


def test_carryover_flags_other_matters_distinctive_phrase_in_chen_draft():
    draft = (
        "Trustee Eleanor Chen notes that refrigerated trailer 7 left idling at the "
        "Salisbury yard for nineteen hours, similar to what we discussed."
    )
    resp = check(CheckRequest(matter_id="chen", draft=draft))
    assert resp.verdict == "leak"
    carryover = [h for h in resp.hits if h.detector == "carryover"]
    assert any(h.matter == "delmarva" for h in carryover)


def test_carryover_passes_the_shared_privilege_footer():
    draft = "This communication is confidential and protected by the attorney-client privilege."
    hits = carryover_hits(
        draft,
        current_corpus={"a": "unrelated text"},
        protected_corpora={
            "delmarva": {"intake": "This communication is confidential and protected by the attorney-client privilege."},
            "reyes": {"intake": "This communication is confidential and protected by the attorney-client privilege."},
        },
    )
    assert hits == []


def test_carryover_ignores_grams_from_current_matters_own_corpus():
    draft = "the lake house in Deep Creek that Victor says was promised to him"
    hits = carryover_hits(
        draft,
        current_corpus={"intake": "the lake house in Deep Creek that Victor says was promised to him"},
        protected_corpora={"delmarva": {"intake": "unrelated text entirely"}},
    )
    assert hits == []


def test_regex_flags_another_matters_name_and_amount():
    current_facts = {"names": ["Luisa Reyes"], "orgs": [], "amounts": ["$6,480"]}
    protected_facts = {
        "delmarva": {
            "names": ["Marcus Pruitt"],
            "orgs": ["Hollis Freight Brokers Inc."],
            "amounts": ["$418,250"],
        }
    }
    draft = "Please pay Marcus Pruitt the $418,250 owed under the agreement."
    hits = regex_fingerprint_hits(draft, current_facts, protected_facts)
    matters_hit = {h.matter for h in hits}
    assert matters_hit == {"delmarva"}
    assert any("Marcus Pruitt" in h.evidence for h in hits)
    assert any("418,250" in h.evidence for h in hits)


def test_regex_subtracts_current_matters_own_amount_first():
    # Same $ amount as another matter, but it belongs to the CURRENT matter here.
    current_facts = {"names": [], "orgs": [], "amounts": ["$120,000"]}
    protected_facts = {"other": {"names": [], "orgs": [], "amounts": ["$120,000"]}}
    draft = "Our client is prepared to discuss resolution at $120,000."
    hits = regex_fingerprint_hits(draft, current_facts, protected_facts)
    assert hits == []


def test_regex_catches_amount_format_variants():
    protected_facts = {"other": {"names": [], "orgs": [], "amounts": ["$418,000"]}}
    empty = {"names": [], "orgs": [], "amounts": []}
    assert regex_fingerprint_hits("settle for $418K", empty, protected_facts)
    assert regex_fingerprint_hits("settle for 418 thousand dollars", empty, protected_facts)
    assert regex_fingerprint_hits("settle for 418000", empty, protected_facts)


def test_clean_draft_has_no_hits():
    resp = check(CheckRequest(matter_id="reyes", draft="Please remit payment within 14 days."))
    assert resp.verdict == "clean"
    assert resp.hits == []
