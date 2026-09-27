"""Tests for wall.policyapi (owned by g2-policy).

The real override path (/Users/dqi26/the-wall/.runtime/...) is never touched;
every test monkeypatches wall.policyapi.OVERRIDE_PATH into tmp_path.
"""

import json

import pytest

from wall import policyapi


@pytest.fixture()
def override_path(tmp_path, monkeypatch):
    path = tmp_path / "policy_override.json"
    monkeypatch.setattr(policyapi, "OVERRIDE_PATH", path)
    return path


def test_get_returns_fixtures_when_no_override(override_path):
    policy = policyapi.get()
    assert set(policy) >= {"litigation", "trusts_estates", "immigration", "asylum"}
    assert "letter templates" in policy["litigation"]["may_compound"]
    assert "parties" in policy["litigation"]["never_compounds"]
    assert not override_path.exists()


def test_get_merges_override_per_practice(override_path):
    override_path.write_text(
        json.dumps(
            {
                "litigation": {
                    "may_compound": ["drafting procedures"],
                    "never_compounds": ["everything else"],
                }
            }
        )
    )
    policy = policyapi.get()
    assert policy["litigation"] == {
        "may_compound": ["drafting procedures"],
        "never_compounds": ["everything else"],
    }
    # Untouched practices still come from fixtures.
    assert "letter templates" not in policy["litigation"]["may_compound"]
    assert "family facts" in policy["trusts_estates"]["never_compounds"]


def test_get_rejects_malformed_override(override_path):
    override_path.write_text("{not json")
    with pytest.raises(ValueError):
        policyapi.get()


def test_save_writes_override_and_returns_merged(override_path):
    base = policyapi.get()
    updated = json.loads(json.dumps(base))
    updated["immigration"]["may_compound"].append("cover-letter structure")
    merged = policyapi.save(updated)
    assert merged["immigration"]["may_compound"][-1] == "cover-letter structure"
    assert json.loads(override_path.read_text()) == updated
    assert policyapi.get() == merged


def test_save_allows_new_practice_and_extra_keys(override_path):
    base = policyapi.get()
    base["tax"] = {"may_compound": [], "never_compounds": ["client holdings"]}
    base["asylum"]["demo"] = False
    merged = policyapi.save(base)
    assert merged["tax"]["never_compounds"] == ["client holdings"]
    assert merged["asylum"]["demo"] is False


@pytest.mark.parametrize(
    "bad",
    [
        {},
        [],
        "litigation",
        {"litigation": {"may_compound": ["x"]}},  # missing never_compounds
        {"litigation": {"never_compounds": ["y"]}},  # missing may_compound
        {"litigation": {"may_compound": "x", "never_compounds": []}},
        {"litigation": {"may_compound": [], "never_compounds": ["", "y"]}},
        {"litigation": {"may_compound": [1], "never_compounds": []}},
        {"": {"may_compound": [], "never_compounds": []}},
        {"litigation": ["may_compound"]},
    ],
)
def test_save_rejects_bad_shape(override_path, bad):
    with pytest.raises(ValueError):
        policyapi.save(bad)
    assert not override_path.exists()


def test_save_never_edits_fixtures(override_path):
    before = policyapi.FIXTURES_PATH.read_text()
    updated = policyapi.get()
    updated["litigation"]["may_compound"].append("something new")
    policyapi.save(updated)
    assert policyapi.FIXTURES_PATH.read_text() == before
