"""The command line: python -m tools.robot demo"""

import os

import pandas as pd
import pytest

from robot import config
from tools import robot as tool


FILES = ["actual_duty.csv", "events.csv", "ground_truth.csv", "schedule.csv", "sweeps.parquet"]


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    """Write under a temporary folder, with short sweeps so that a day takes a fraction of a second."""
    monkeypatch.setattr(config, "SIMULATION_DIR", str(tmp_path))
    monkeypatch.setattr(config, "SETTLE_S", 0.1)
    monkeypatch.setattr(config, "RECORD_S", 0.05)
    return tmp_path


def test_demo_writes_the_dataset_of_the_scenario_and_says_where(sandbox, capsys):
    tool.main(["demo", "--scenario", "ramp_early", "--days", "2", "--seed", "3"])

    folder = sandbox / "ramp_early"
    assert sorted(os.listdir(folder)) == ["actual_duty.csv", "events.csv", "ground_truth.csv", "schedule.csv", "sweeps.parquet"]
    assert len(pd.read_parquet(folder / "sweeps.parquet")) == 2 * config.N_JOINTS * 18
    printed = capsys.readouterr().out
    assert str(folder) in printed
    assert "216 rows" in printed
    assert "simulation" in printed.lower()                       # every output says it is not a real robot


def test_demo_defaults_to_the_late_ramp_400_days_seed_0_one_run():
    args = tool.parse(["demo"])

    assert (args.scenario, args.days, args.seed, args.runs) == ("ramp_late", 400, 0, None)
    assert (args.gui, args.joint, args.wear) == (False, 3, 0.5)


# ---------------------------------------------------------------------------
# The live demo: one sweep in a window. The tests run it without the window.
# ---------------------------------------------------------------------------

def test_the_live_sweep_reads_back_the_wear_it_was_given(sandbox, capsys):
    result = tool.live_sweep(joint=3, wear=0.5, seed=0, gui=False)

    assert result["fc_new"] == pytest.approx(config.FC0, rel=0.05)
    assert result["health_index"] == pytest.approx(0.5, abs=0.03)
    printed = capsys.readouterr().out
    assert "joint 3" in printed
    assert f"{result['health_index']:.2f}" in printed
    assert "simulation" in printed.lower()
    assert str(config.FAIL_W) in printed                         # the reader sees the threshold next to the index


def test_the_live_sweep_of_a_new_joint_reads_about_zero(sandbox):
    assert tool.live_sweep(joint=1, wear=0.0, seed=0, gui=False)["health_index"] == pytest.approx(0.0, abs=0.03)


def test_gui_runs_the_live_sweep_and_writes_no_dataset(sandbox, monkeypatch):
    calls = []
    monkeypatch.setattr(tool, "live_sweep", lambda joint, wear, seed, gui: calls.append((joint, wear, seed, gui)))

    tool.main(["demo", "--gui", "--joint", "2", "--wear", "0.3", "--seed", "4"])

    assert calls == [(2, 0.3, 4, True)]
    assert os.listdir(sandbox) == []


@pytest.mark.parametrize("extra", [["--joint", "6"], ["--joint", "-1"], ["--wear", "-0.1"]])
def test_gui_refuses_a_joint_or_wear_that_does_not_exist(sandbox, monkeypatch, extra):
    monkeypatch.setattr(tool, "live_sweep", lambda *args, **kwargs: pytest.fail("the window must not open"))

    with pytest.raises(SystemExit):
        tool.main(["demo", "--gui"] + extra)


def read(path):
    with open(path, "rb") as f:
        return f.read()


def test_runs_go_into_one_folder_each(sandbox, capsys):
    tool.main(["demo", "--scenario", "ramp_early", "--days", "2", "--seed", "5", "--runs", "3"])

    scenario = sandbox / "ramp_early"
    assert sorted(os.listdir(scenario)) == ["run_0", "run_1", "run_2"]
    for k in range(3):
        assert sorted(os.listdir(scenario / f"run_{k}")) == FILES
    printed = capsys.readouterr().out
    assert all(f"run_{k}" in printed for k in range(3))


def test_each_run_is_a_different_robot(sandbox):
    tool.main(["demo", "--scenario", "ramp_early", "--days", "2", "--seed", "5", "--runs", "2"])

    first, second = sandbox / "ramp_early" / "run_0", sandbox / "ramp_early" / "run_1"
    assert read(first / "sweeps.parquet") != read(second / "sweeps.parquet")
    assert read(first / "actual_duty.csv") != read(second / "actual_duty.csv")
    assert read(first / "schedule.csv") == read(second / "schedule.csv")          # one plan for every run
    wear = [pd.read_csv(run / "ground_truth.csv").query("day == 1")["wear"] / pd.read_csv(run / "actual_duty.csv")["duty_actual"].sum()
            for run in (first, second)]
    assert (wear[0] != wear[1]).all()                                             # each joint wears at its own rate in each run


def test_run_k_is_the_single_run_of_seed_plus_k(sandbox):
    tool.main(["demo", "--scenario", "ramp_early", "--days", "2", "--seed", "5", "--runs", "2"])
    tool.main(["demo", "--scenario", "ramp_late", "--days", "2", "--seed", "6"])

    # before the ramp the two scenarios have the same plan, so the same seed gives the same files
    for name in FILES:
        assert read(sandbox / "ramp_early" / "run_1" / name) == read(sandbox / "ramp_late" / name), name


def test_zero_runs_is_refused(sandbox):
    with pytest.raises(SystemExit):
        tool.main(["demo", "--days", "1", "--runs", "0"])
    assert os.listdir(sandbox) == []


def test_demo_refuses_an_unknown_scenario(sandbox):
    with pytest.raises(SystemExit):
        tool.main(["demo", "--scenario", "ramp_sideways", "--days", "1"])
    assert os.listdir(sandbox) == []
