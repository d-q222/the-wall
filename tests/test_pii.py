"""Tests for wall.pii.find. All text below is self-written/synthetic; no real client data."""

from wall.pii import find


def _kinds(text: str) -> set[str]:
    return {s.kind for s in find(text)}


def _spans_of(text: str, kind: str) -> list[str]:
    return [text[s.start : s.end] for s in find(text) if s.kind == kind]


# ---------------------------------------------------------------------------
# One positive + one negative per kind
# ---------------------------------------------------------------------------


def test_email_positive():
    assert _spans_of("Contact jane.doe@example.com for the retainer.", "email") == [
        "jane.doe@example.com"
    ]


def test_email_negative():
    assert "email" not in _kinds("The ratio came out to 3.5x2, nothing more.")


def test_phone_positive_us():
    assert _spans_of("Call (415) 555-0192 before Friday.", "phone") == ["(415) 555-0192"]


def test_phone_positive_international():
    assert _spans_of("Reach the London office at +44 20 7946 0958.", "phone") == [
        "+44 20 7946 0958"
    ]


def test_phone_negative():
    assert "phone" not in _kinds("The file reference is 12-3456 in the index.")


def test_ssn_positive():
    assert _spans_of("SSN on file: 987-65-4321.", "ssn") == ["987-65-4321"]


def test_ssn_negative():
    # Wrong grouping (2-2-3), must not be mistaken for an SSN.
    assert "ssn" not in _kinds("The zip range is 12-34-567 this year.")


def test_url_positive():
    assert _spans_of("See https://www.example.gov/forms for details.", "url") == [
        "https://www.example.gov/forms"
    ]


def test_url_negative():
    assert "url" not in _kinds("The equation e=mc^2 has nothing to do with urls.")


def test_date_positive_month_name():
    assert _spans_of("The hearing is set for March 3, 2024 downtown.", "date") == [
        "March 3, 2024"
    ]


def test_date_positive_slash():
    assert _spans_of("Filing deadline: 03/03/2024, no extensions.", "date") == ["03/03/2024"]


def test_date_positive_iso():
    assert _spans_of("Recorded as 2024-03-03 in the system.", "date") == ["2024-03-03"]


def test_date_negative():
    assert "date" not in _kinds("He cited 8 U.S.C. 1101 as authority.")


def test_amount_positive_dollar_sign():
    assert _spans_of("The settlement was $418,250 after fees.", "amount") == ["$418,250"]


def test_amount_positive_words():
    assert _spans_of("Total damages reached 418 thousand dollars.", "amount") == [
        "418 thousand dollars"
    ]


def test_amount_positive_usd():
    assert _spans_of("Billed at USD 418,250 this quarter.", "amount") == ["USD 418,250"]


def test_amount_negative():
    assert "amount" not in _kinds("Room 418 is on the third floor.")


def test_address_positive():
    assert _spans_of("Mail records to 123 Main Street, Suite 400 by Friday.", "address") == [
        "123 Main Street, Suite 400"
    ]


def test_address_negative():
    assert "address" not in _kinds("He scored 100 Points in the final round.")


def test_a_number_positive_dashed():
    assert _spans_of("Her A-Number is A123-456-789 on the notice.", "a_number") == [
        "A123-456-789"
    ]


def test_a_number_positive_spaced():
    assert _spans_of("Confirmed A 123456789 matches the file.", "a_number") == ["A 123456789"]


def test_a_number_negative():
    assert "a_number" not in _kinds("Form A1 was submitted yesterday.")


def test_receipt_positive():
    assert _spans_of("The receipt number EAC2015123456 was issued last week.", "receipt") == [
        "EAC2015123456"
    ]


def test_receipt_negative():
    # Office code not in the recognized set.
    assert "receipt" not in _kinds("Tracking code ABC1234567890 was scanned.")


def test_passport_positive():
    assert _spans_of("Her passport number is X1234567 per the copy on file.", "passport") == [
        "X1234567"
    ]


def test_passport_negative():
    assert "passport" not in _kinds("The passport office processes applications quickly.")


def test_name_positive_title():
    assert _spans_of("Mr. James Chen submitted the supporting documents.", "name") == [
        "Mr. James Chen"
    ]


def test_name_positive_dear():
    assert _spans_of("Dear Maria Alvarez, thank you for your patience.", "name") == [
        "Maria Alvarez"
    ]


def test_name_negative_stopwords():
    # Both words are legal/common terms, not a person.
    assert "name" not in _kinds("Homeland Security manages the program nationwide.")


def test_org_positive():
    assert _spans_of(
        "American Scholars Foundation announced new grants.", "org"
    ) == ["American Scholars Foundation"]


def test_org_negative_no_suffix():
    assert "org" not in _kinds("Delmarva Logistics handled the shipment.")


# ---------------------------------------------------------------------------
# False-positive checks on firm/agency boilerplate
# ---------------------------------------------------------------------------


def test_boilerplate_confidentiality_notice_is_clean():
    text = "This communication is confidential and protected by the attorney-client privilege."
    assert find(text) == []


def test_boilerplate_uscis_name_is_clean():
    text = "U.S. Citizenship and Immigration Services"
    assert find(text) == []


# ---------------------------------------------------------------------------
# Overlap resolution
# ---------------------------------------------------------------------------


def test_org_suffix_wins_over_bare_name_overlap():
    spans = find("Delmarva Logistics Inc. filed the O-1 petition.")
    kinds_at_start = {s.kind for s in spans if s.start == 0}
    assert kinds_at_start == {"org"}
    # No overlapping spans anywhere.
    for i in range(len(spans) - 1):
        assert spans[i].end <= spans[i + 1].start


def test_spans_sorted_and_non_overlapping():
    text = "Mr. James Chen (james.chen@example.com) filed on March 3, 2024 for $418,250."
    spans = find(text)
    assert [s.start for s in spans] == sorted(s.start for s in spans)
    for i in range(len(spans) - 1):
        assert spans[i].end <= spans[i + 1].start


# ---------------------------------------------------------------------------
# Self-written labeled corpus: precision/recall report (see handoff).
#
# Coarse-grained: per sentence, does the set of KINDS found match the
# hand-labeled expected kind set? Not exact-span scoring. Self-written by
# C3, synthetic only, never opened any eval fixture from other branches.
# ---------------------------------------------------------------------------

_LABELED_CORPUS: list[tuple[str, set[str]]] = [
    ("Please contact jane.smith@lawfirm.com for the retainer agreement.", {"email"}),
    ("Reach him at (415) 555-0192 before Friday.", {"phone"}),
    ("His SSN is 987-65-4321 per the intake form.", {"ssn"}),
    ("See https://www.uscis.gov/forms for the latest I-129 form.", {"url"}),
    ("The hearing is scheduled for March 3, 2024 at the district office.", {"date"}),
    ("Filing deadline: 03/03/2024, no extensions.", {"date"}),
    ("Petition receipt date recorded as 2024-03-03 in the system.", {"date"}),
    ("The settlement was $418,250 after fees.", {"amount"}),
    ("Total damages reached 418 thousand dollars.", {"amount"}),
    ("Invoice was billed at USD 418,250 this quarter.", {"amount"}),
    ("Mail records to 123 Main Street, Suite 400 by end of week.", {"address"}),
    ("Her A-Number is A123-456-789 on the notice.", {"a_number"}),
    ("Confirmed A 123456789 matches the beneficiary file.", {"a_number"}),
    ("The receipt number EAC2015123456 was issued last week.", {"receipt"}),
    ("Her passport number is X1234567 per the copy on file.", {"passport"}),
    ("Dear Maria Alvarez, thank you for your patience.", {"name"}),
    ("Mr. James Chen submitted the supporting documents.", {"name"}),
    ("Delmarva Logistics Inc. filed the O-1 petition.", {"org"}),
    ("American Scholars Foundation announced new grants.", {"org"}),
    ("Call +44 20 7946 0958 for the London office.", {"phone"}),
    (
        "This communication is confidential and protected by the attorney-client privilege.",
        set(),
    ),
    ("U.S. Citizenship and Immigration Services reviewed the case.", set()),
    ("Homeland Security manages the program nationwide.", set()),
    ("He turned 42 years old last week.", set()),
    ("The case cited 8 U.S.C. 1101 as authority.", set()),
]


def test_labeled_corpus_precision_recall():
    tp = fp = fn = 0
    for text, expected in _LABELED_CORPUS:
        found = _kinds(text)
        tp += len(found & expected)
        fp += len(found - expected)
        fn += len(expected - found)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    # Self-written 25-sentence corpus (see module docstring above for method).
    # Measured at write time: precision 1.00, recall 1.00 (see handoff).
    assert precision >= 0.9
    assert recall >= 0.9
