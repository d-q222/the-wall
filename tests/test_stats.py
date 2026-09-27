import json

from evals.stats import (
    compare_proportions,
    compare_recall,
    compute_ci,
    format_table,
    wilson_interval,
    write_ci,
)


def approx(a: float, b: float, tol: float = 1e-3) -> bool:
    return abs(a - b) < tol


def test_wilson_interval_matches_known_50_of_100():
    lo, hi = wilson_interval(50, 100)
    assert approx(lo, 0.4039)
    assert approx(hi, 0.5962)


def test_wilson_interval_zero_successes_lower_bound_is_essentially_zero():
    lo, hi = wilson_interval(0, 102)
    assert approx(lo, 0.0, tol=1e-9)
    assert hi > 0.0


def test_wilson_interval_all_successes_upper_bound_is_essentially_one():
    lo, hi = wilson_interval(102, 102)
    assert approx(hi, 1.0, tol=1e-9)
    assert lo < 1.0


def test_wilson_interval_narrows_as_n_grows():
    lo_small, hi_small = wilson_interval(50, 100)
    lo_big, hi_big = wilson_interval(500, 1000)
    assert (hi_big - lo_big) < (hi_small - lo_small)


def test_wilson_interval_rejects_empty_total():
    try:
        wilson_interval(0, 0)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_wilson_interval_rejects_successes_over_total():
    try:
        wilson_interval(5, 3)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_compare_proportions_clearly_different_does_not_overlap():
    result = compare_proportions(90, 100, 50, 100)
    assert approx(result["diff"], 0.4)
    assert result["overlap"] is False
    lo, hi = result["diff_ci"]
    assert lo > 0  # interval excludes zero: the two are distinguishable


def test_compare_proportions_similar_rates_overlap_and_include_zero():
    result = compare_proportions(50, 100, 52, 100)
    assert result["overlap"] is True
    lo, hi = result["diff_ci"]
    assert lo < 0 < hi


def test_compare_recall_pulls_counts_from_results_shape():
    data = {
        "regex": {"hard": {"caught": 0, "leaks": 102, "false_alarms": 0, "clean": 98, "n": 200}},
        "base_judge": {"hard": {"caught": 39, "leaks": 102, "false_alarms": 5, "clean": 98, "n": 200}},
    }
    result = compare_recall(data, "base_judge", "regex", "hard")
    assert approx(result["p1"], 39 / 102)
    assert approx(result["p2"], 0.0)
    assert result["overlap"] is False


def test_compute_ci_shape_matches_contract():
    data = {
        "regex": {
            "hard": {"caught": 0, "leaks": 102, "false_alarms": 0, "clean": 98, "n": 200},
        },
    }
    ci = compute_ci(data)
    assert set(ci["regex"]["hard"]) == {"recall", "false_alarm"}
    lo, hi = ci["regex"]["hard"]["recall"]
    assert approx(lo, 0.0, tol=1e-9)
    lo, hi = ci["regex"]["hard"]["false_alarm"]
    assert approx(lo, 0.0, tol=1e-9)


def test_compute_ci_skips_recall_when_no_leaks_in_set():
    data = {"detector": {"set": {"caught": 0, "leaks": 0, "false_alarms": 2, "clean": 50, "n": 50}}}
    ci = compute_ci(data)
    assert "recall" not in ci["detector"]["set"]
    assert "false_alarm" in ci["detector"]["set"]


def test_format_table_reports_counts_and_handles_missing_leaks():
    data = {"detector": {"set": {"caught": 0, "leaks": 0, "false_alarms": 1, "clean": 10, "n": 10}}}
    ci = compute_ci(data)
    table = format_table(data, ci)
    assert "n/a (0 leaks)" in table
    assert "1/10" in table


def test_write_ci_writes_expected_json_shape(tmp_path):
    ci = {"regex": {"hard": {"recall": [0.0, 0.036], "false_alarm": [0.0, 0.037]}}}
    path = tmp_path / "ci.json"
    write_ci(ci, path)
    loaded = json.loads(path.read_text())
    assert loaded == ci
