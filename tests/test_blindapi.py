import json

import pytest

from wall import blindapi


@pytest.fixture
def blind_file(tmp_path, monkeypatch):
    path = tmp_path / "blind.jsonl"
    monkeypatch.setattr(blindapi, "BLIND_PATH", path)
    return path


def good_row(label="CLEAN"):
    return {
        "current": (
            "M1: Client Ana Ruiz (Ruiz Bakery LLC) v. Tom Hale, former landlord. "
            "Matter type: commercial lease. "
            "Confidential: settlement floor is $42,000."
        ),
        "protected": [
            (
                "M2: Client Owen Pratt (Pratt Marine Inc.) v. Lena Voss, ex-partner. "
                "Matter type: partnership dispute. "
                "Confidential: hidden account holds $310,500."
            )
        ],
        "draft": "Dear Mr. Hale, our client will not accept less than a fair resolution of the lease dispute.",
        "label": label,
    }


def test_append_valid_row_writes_one_json_line(blind_file):
    resp = blindapi.append(good_row())
    assert resp["ok"] is True
    lines = blind_file.read_text().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["label"] == "CLEAN"


def test_append_rejects_unparseable_block(blind_file):
    resp = blindapi.append({"current": "not a block", "protected": [], "draft": "x", "label": "CLEAN"})
    assert resp["ok"] is False
    assert not blind_file.exists()


def test_append_rejects_bad_label(blind_file):
    row = good_row(label="MAYBE")
    resp = blindapi.append(row)
    assert resp["ok"] is False
    assert not blind_file.exists()


def test_summary_counts_leak_clean_n(blind_file):
    assert blindapi.summary() == {"leak": 0, "clean": 0, "n": 0}
    blindapi.append(good_row("CLEAN"))
    blindapi.append(good_row("LEAK"))
    assert blindapi.summary() == {"leak": 1, "clean": 1, "n": 2}


def test_summary_skips_garbage_lines(blind_file):
    blind_file.write_text("not json\n" + json.dumps(good_row("LEAK")) + "\n")
    assert blindapi.summary() == {"leak": 1, "clean": 0, "n": 1}
