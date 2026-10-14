"""Collecting a dataset by name: what the collection screen does when Start is pressed, without the screen.

A collection is a few robots (runs) of one scenario. It goes to
<root>/<name>/<scenario>/run_<k>/ and never over anything that exists.
"""

import json
import os

import pandas as pd
import pytest

from robot import config
from robot.collect import SWITCHES, collect, switched
from robot.simulate import simulate

FILES = ["actual_duty.csv", "events.csv", "ground_truth.csv", "schedule.csv", "sweeps.parquet"]
TWO = (0, 3)               # two joints are enough for most of these tests, and three times faster than six


@pytest.fixture()
def fast(monkeypatch):
    """Short sweeps and wear about 100 times faster, so that 4 days already wear a joint well."""
    monkeypatch.setattr(config, "SETTLE_S", 0.1)
    monkeypatch.setattr(config, "RECORD_S", 0.05)
    monkeypatch.setattr(config, "K_WEAR", 0.22)


def read(path):
    with open(path, "rb") as f:
        return f.read()


def test_it_writes_one_folder_per_robot_and_a_note_of_what_was_asked(fast, tmp_path):
    result = collect("trial", "ramp_early", days=3, runs=2, first_seed=5, root=str(tmp_path), joints=TWO)

    folder = tmp_path / "trial"
    assert result == {"folder": str(folder), "runs_written": 2, "stopped": False}
    assert sorted(os.listdir(folder)) == ["collection.json", "ramp_early"]
    assert sorted(os.listdir(folder / "ramp_early")) == ["run_0", "run_1"]
    assert sorted(os.listdir(folder / "ramp_early" / "run_1")) == FILES
    note = json.loads((folder / "collection.json").read_text())
    assert {k: note[k] for k in ("name", "scenario", "days", "runs_asked", "runs_written", "first_seed", "switches_on", "stopped")} == {
        "name": "trial", "scenario": "ramp_early", "days": 3, "runs_asked": 2, "runs_written": 2, "first_seed": 5,
        "switches_on": [], "stopped": False}
    assert note["seconds_at_each_speed"] == [0.1, 0.05]


def test_robot_k_is_the_run_of_first_seed_plus_k(fast, tmp_path):
    collect("trial", "ramp_early", days=3, runs=2, first_seed=5, root=str(tmp_path), joints=TWO)
    simulate("ramp_early", 3, seed=6, out_dir=str(tmp_path / "alone"), joints=TWO)

    for name in FILES:
        assert read(tmp_path / "trial" / "ramp_early" / "run_1" / name) == read(tmp_path / "alone" / name), name


def test_a_name_that_exists_is_refused_and_nothing_is_touched(fast, tmp_path):
    collect("trial", "ramp_early", days=2, runs=1, root=str(tmp_path), joints=TWO)
    before = read(tmp_path / "trial" / "ramp_early" / "run_0" / "sweeps.parquet")

    with pytest.raises(ValueError, match="already exists"):
        collect("trial", "ramp_late", days=5, runs=1, root=str(tmp_path))
    assert read(tmp_path / "trial" / "ramp_early" / "run_0" / "sweeps.parquet") == before
    assert sorted(os.listdir(tmp_path / "trial")) == ["collection.json", "ramp_early"]


@pytest.mark.parametrize("bad, message", [
    (dict(name=""), "name"), (dict(name="two words"), "name"), (dict(name="../outside"), "name"),
    (dict(scenario="ramp_sideways"), "scenario"), (dict(days=0), "days"), (dict(runs=0), "robots"),
    (dict(switches=["MAGIC"]), "MAGIC"),
])
def test_an_impossible_request_is_refused_before_any_work(tmp_path, bad, message):
    request = dict(name="trial", scenario="ramp_early", days=2, runs=1, switches=[])
    request.update(bad)

    with pytest.raises(ValueError, match=message):
        collect(root=str(tmp_path), **request)
    assert os.listdir(tmp_path) == []


def test_switches_are_on_for_the_collection_only(fast, tmp_path):
    # 5 days: joint 3 is past a wear of 0.6 after day 3, so the last day is the one the switch speeds up
    collect("plain", "ramp_early", days=5, runs=1, root=str(tmp_path), joints=TWO)
    collect("faster", "ramp_early", days=5, runs=1, switches=["WEAR_ACCEL"], root=str(tmp_path), joints=TWO)

    wear = [pd.read_csv(tmp_path / name / "ramp_early" / "run_0" / "ground_truth.csv")["wear"].max() for name in ("plain", "faster")]
    assert wear[1] > wear[0] > config.WEAR_ACCEL_FROM                        # the switch did act
    assert json.loads((tmp_path / "faster" / "collection.json").read_text())["switches_on"] == ["WEAR_ACCEL"]
    assert not any(getattr(config, name) for name in SWITCHES)               # and is off again


def test_maintenance_events_happen_in_every_robot_and_are_noted(fast, tmp_path):
    collect("plain", "ramp_early", days=4, runs=1, root=str(tmp_path), joints=TWO)
    collect("greased", "ramp_early", days=4, runs=2, root=str(tmp_path), joints=TWO, events=[(2, 3, "regrease")])

    plain = pd.read_csv(tmp_path / "plain" / "ramp_early" / "run_0" / "ground_truth.csv").query("joint == 3")["wear"].tolist()
    for k in range(2):
        run = tmp_path / "greased" / "ramp_early" / f"run_{k}"
        assert pd.read_csv(run / "events.csv").values.tolist() == [[2, 3, "regrease"]]
    greased = pd.read_csv(tmp_path / "greased" / "ramp_early" / "run_0" / "ground_truth.csv").query("joint == 3")["wear"].tolist()
    assert greased[1] == plain[1] and greased[2] < plain[2]                  # the grease went in on the morning of day 2
    assert json.loads((tmp_path / "greased" / "collection.json").read_text())["events"] == [[2, 3, "regrease"]]


def test_an_event_that_cannot_happen_is_refused_before_any_work(fast, tmp_path):
    with pytest.raises(ValueError, match="day 9"):
        collect("trial", "ramp_early", days=4, runs=1, root=str(tmp_path), events=[(9, 3, "regrease")])
    assert os.listdir(tmp_path) == []


def test_switched_puts_everything_back_even_after_an_error():
    with pytest.raises(RuntimeError):
        with switched(["SENSOR_FAULTS", "WEAR_NOISE"]):
            assert config.SENSOR_FAULTS and config.WEAR_NOISE and not config.WEAR_ACCEL
            raise RuntimeError("something went wrong in the middle")
    assert not any(getattr(config, name) for name in SWITCHES)


def test_a_watcher_sees_every_day_of_every_robot(fast, tmp_path):
    seen = []
    collect("trial", "ramp_early", days=2, runs=2, root=str(tmp_path),
            watch=lambda run, day, rows, world: seen.append((run, day, len(rows))))

    assert seen == [(0, 0, 108), (0, 1, 108), (1, 0, 108), (1, 1, 108)]      # 6 joints x 18 speeds a day


def test_stopping_keeps_the_robots_that_were_finished(fast, tmp_path):
    days_seen = []

    def watch(run, day, rows, world):
        days_seen.append((run, day))

    result = collect("trial", "ramp_early", days=3, runs=3, root=str(tmp_path), watch=watch, joints=TWO,
                     should_stop=lambda: len(days_seen) >= 4)                # stop on the first day of the second robot

    assert result == {"folder": str(tmp_path / "trial"), "runs_written": 1, "stopped": True}
    assert os.listdir(tmp_path / "trial" / "ramp_early") == ["run_0"]        # the half-done robot left nothing
    note = json.loads((tmp_path / "trial" / "collection.json").read_text())
    assert (note["runs_asked"], note["runs_written"], note["stopped"]) == (3, 1, True)


def test_stopping_before_the_first_robot_is_done_leaves_nothing(fast, tmp_path):
    result = collect("trial", "ramp_early", days=3, runs=2, root=str(tmp_path), should_stop=lambda: True)

    assert result == {"folder": str(tmp_path / "trial"), "runs_written": 0, "stopped": True}
    assert os.listdir(tmp_path) == []
