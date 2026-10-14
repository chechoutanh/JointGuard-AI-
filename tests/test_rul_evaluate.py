"""The evaluation harness: the two splits, scoring, the summary, the cache loader and the command."""

import numpy as np
import pytest

import config
from features import cache
from features.snapshot import feature_names
from rul import evaluate
from rul.data import Unit, load_units, share_of_life_left
from sources.recording import Recording
from tools import rul as tool


def unit(unit_id, condition, t_hours):
    t = np.array(t_hours, dtype=float)
    return Unit(unit_id=unit_id, condition=condition, t_hours=t, life_hours=float(t[-1]),
                s=share_of_life_left(t, t[-1]), x=np.ones((len(t), 1)), names=["rms"])


def ids(units):
    return [u.unit_id for u in units]


def test_leave_one_bearing_out_tests_each_bearing_once_and_never_trains_on_it():
    units = [unit(name, "a", [0, 1]) for name in "ABCD"]

    folds = evaluate.leave_one_bearing_out(units)

    assert [ids(test) for _, test in folds] == [["A"], ["B"], ["C"], ["D"]]
    assert [ids(train) for train, _ in folds] == [["B", "C", "D"], ["A", "C", "D"], ["A", "B", "D"], ["A", "B", "C"]]


def test_leave_one_condition_out_holds_out_every_bearing_of_a_condition():
    units = [unit("A", "35Hz", [0, 1]), unit("B", "35Hz", [0, 1]), unit("C", "40Hz", [0, 1]), unit("D", "37Hz", [0, 1])]

    folds = evaluate.leave_one_condition_out(units)

    assert [(ids(train), ids(test)) for train, test in folds] == [
        (["C", "D"], ["A", "B"]), (["A", "B", "C"], ["D"]), (["A", "B", "D"], ["C"])]


def test_a_bearing_is_scored_by_a_model_that_never_saw_it():
    units = [unit("A", "a", [0, 0.5, 1]), unit("B", "a", [0, 1, 2]), unit("C", "a", [0, 15, 30])]

    result = evaluate.evaluate(units, evaluate.leave_one_bearing_out(units))
    row = {r["unit_id"]: r for r in result["elapsed time"]["bearings"]}["B"]

    # B is predicted from the lives of A and C only: median 15.5 h, so 1, 1 - 1/15.5, 1 - 2/15.5
    # against the truth 1, 0.5, 0. Had B's own 2 hours been used, the median would be 2 and the error 0.
    assert row["mae"] == pytest.approx((13.5 / 31 + 27 / 31) / 3)


def test_the_summary_averages_over_bearings_not_over_snapshots():
    units = [unit("short", "a", [0, 1]), unit("long", "a", [0, 1, 2, 3, 4]), unit("other", "a", [0, 1, 2, 3, 4])]

    result = evaluate.evaluate(units, evaluate.leave_one_bearing_out(units))
    summary = evaluate.summarise(result["constant 0.5"])

    # always saying 0.5: error 0.5 for the 2-snapshot bearing, 0.3 for each 5-snapshot one
    assert summary["mae"] == pytest.approx((0.5 + 0.3 + 0.3) / 3)
    assert summary["bearings"] == 3
    assert summary["beat_guessing"] == 0


def test_the_summary_counts_the_bearings_that_beat_guessing():
    rows = [{"mae": 0.10, "recall": 1.0, "hours_error": 1.0, "percent_error": 10.0, "rank": 0.9, "coverage": 0.9, "width": 0.5},
            {"mae": 0.30, "recall": 0.0, "hours_error": 3.0, "percent_error": 70.0, "rank": 0.1, "coverage": 0.7, "width": 0.3},
            {"mae": 0.249, "recall": 0.5, "hours_error": 2.0, "percent_error": 40.0, "rank": 0.5, "coverage": 0.8, "width": 0.1}]

    summary = evaluate.summarise({"bearings": rows, "triage": 0.75})

    assert summary["beat_guessing"] == 2
    assert summary["recall"] == pytest.approx(0.5)
    assert (summary["hours_error"], summary["percent_error"]) == (2.0, 40.0)      # medians over bearings
    assert (summary["rank"], summary["triage"]) == (pytest.approx(0.5), 0.75)
    assert (summary["coverage"], summary["width"]) == (pytest.approx(0.8), pytest.approx(0.3))


BANDS = config.RUL_BANDS_HZ


def save_bearing(unit_id, condition, rms_by_channel):
    """Cache file for a bearing whose raw rms per snapshot and channel is given; other features are 1."""
    rms = np.array(rms_by_channel, dtype=float)
    names = feature_names(BANDS)
    raw = np.ones((len(rms), rms.shape[1], len(names)))
    raw[:, :, names.index("rms")] = rms
    rec = Recording(source="xjtu", unit_id=unit_id, run_id=unit_id, condition=condition, fs=25600.0,
                    t_hours=np.arange(len(rms)) / 60, failure_hours=(len(rms) - 1) / 60, fault_class=None,
                    channels=("horizontal", "vertical"), snapshot=None)
    cache.save(cache.path("xjtu", unit_id), rec, raw, np.zeros(len(rms), dtype=int), BANDS)


@pytest.fixture
def empty_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROCESSED_DIR", str(tmp_path))
    return tmp_path


def test_units_are_read_from_the_cache_as_relative_features(empty_cache, monkeypatch):
    monkeypatch.setattr(config, "HEALTHY_SNAPSHOTS", 2)
    save_bearing("Bearing1_1", "35Hz_12kN", [[2, 10], [2, 10], [4, 10]])

    (got,) = load_units("xjtu")

    # sensor 0 doubles against its own start, sensor 1 does not move: the larger change is kept
    assert got.x[:, got.names.index("rms")].tolist() == [1.0, 1.0, 2.0]
    assert got.s.tolist() == [1.0, 0.5, 0.0]
    assert (got.unit_id, got.condition, got.life_hours) == ("Bearing1_1", "35Hz_12kN", 2 / 60)


def test_the_command_reports_every_baseline_for_both_splits(empty_cache, capsys):
    rng = np.random.default_rng(0)
    for c, condition in enumerate(("35Hz_12kN", "37.5Hz_11kN", "40Hz_10kN")):
        for b in range(2):
            n = int(rng.integers(20, 40))
            growth = np.linspace(1.0, rng.uniform(3.0, 9.0), n) ** 2
            save_bearing(f"Bearing{c + 1}_{b + 1}", condition, np.column_stack([growth, growth * 0.5]))

    tool.main(["evaluate"])
    out = capsys.readouterr().out

    assert out.count("leave one bearing out") == 1 and out.count("leave one condition out") == 1
    for name in ("constant 0.5", "elapsed time", "rms only"):
        assert out.count(name) >= 2
