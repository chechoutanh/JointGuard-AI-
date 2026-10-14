"""The day loop: wear grows with the work done, every joint is swept every day, and five files are written.

To keep this fast the sweeps are shortened (0.15 s per speed instead of 1 s)
and wear is made about 100 times faster, so that a joint goes from new to
past its service threshold in 6 days. Two joints are simulated: joint 3
passes the threshold, joint 0 (the slowest wearing) does not.
"""

import os

import numpy as np
import pandas as pd
import pytest

from robot import config, simulate as simulate_module
from robot.fit import fit_friction
from robot.guard import assert_no_leakage
from robot.schedule import planned_duty
from robot.simulate import simulate, wear_rates
from robot.thermal import next_temperature

DAYS = 6
JOINTS = (0, 3)
SCENARIO = "ramp_early"
FILES = ["actual_duty.csv", "events.csv", "ground_truth.csv", "schedule.csv", "sweeps.parquet"]


@pytest.fixture(scope="module")
def fast():
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(config, "SETTLE_S", 0.1)
        patch.setattr(config, "RECORD_S", 0.05)
        patch.setattr(config, "K_WEAR", 0.22)
        yield


@pytest.fixture(scope="module")
def run(fast, tmp_path_factory):
    """One run of 6 days, seed 0."""
    out = str(tmp_path_factory.mktemp("run"))
    simulate(SCENARIO, DAYS, seed=0, out_dir=out, joints=JOINTS)
    return out


def table(folder, name):
    path = os.path.join(folder, name)
    return pd.read_parquet(path) if name.endswith(".parquet") else pd.read_csv(path)


def file_bytes(folder, name):
    with open(os.path.join(folder, name), "rb") as f:
        return f.read()


def test_it_writes_the_five_files(run):
    assert sorted(os.listdir(run)) == FILES


def test_the_sweeps_file_has_one_row_per_day_joint_and_speed(run):
    sweeps = table(run, "sweeps.parquet")

    assert list(sweeps.columns) == ["day", "joint", "v_target", "v_measured", "friction_torque", "temperature_c",
                                    "posture_q", "payload_kg", "duty_planned"]
    assert len(sweeps) == DAYS * len(JOINTS) * 18
    assert sorted(sweeps["day"].unique()) == list(range(DAYS))
    assert sorted(sweeps["joint"].unique()) == list(JOINTS)
    assert (sweeps.groupby(["day", "joint"]).size() == 18).all()
    assert sweeps["day"].dtype == "int64" and sweeps["joint"].dtype == "int64"
    assert sweeps["friction_torque"].dtype == "float64"
    assert list(sweeps["posture_q"].iloc[0]) == list(config.POSTURE)
    assert (sweeps["payload_kg"] == 0.0).all()


def test_determinism(run, tmp_path):
    again, other = str(tmp_path / "again"), str(tmp_path / "other")
    simulate(SCENARIO, DAYS, seed=0, out_dir=again, joints=JOINTS)
    simulate(SCENARIO, DAYS, seed=1, out_dir=other, joints=JOINTS)

    for name in FILES:
        assert file_bytes(again, name) == file_bytes(run, name), name
    assert file_bytes(other, "sweeps.parquet") != file_bytes(run, "sweeps.parquet")
    assert file_bytes(other, "actual_duty.csv") != file_bytes(run, "actual_duty.csv")
    assert file_bytes(other, "schedule.csv") == file_bytes(run, "schedule.csv")          # the plan does not depend on the seed


def test_no_leakage(run):
    sweeps = table(run, "sweeps.parquet")
    assert_no_leakage(sweeps.columns)

    sweeps["wear"] = 0.5
    with pytest.raises(AssertionError, match="leakage"):
        assert_no_leakage(sweeps.columns)


def test_a_leak_from_the_sweep_stops_the_run_before_the_file_is_written(fast, tmp_path, monkeypatch):
    real = simulate_module.run_health_check

    def leaky(world, joint, wear, temperature_c, rng, **options):
        return [{**row, "wear": float(wear[joint])} for row in real(world, joint, wear, temperature_c, rng, **options)]

    monkeypatch.setattr(simulate_module, "run_health_check", leaky)

    with pytest.raises(AssertionError, match="leakage"):
        simulate(SCENARIO, 1, seed=0, out_dir=str(tmp_path), joints=JOINTS)
    assert not os.path.exists(tmp_path / "sweeps.parquet")


def test_wear_is_rate_times_the_work_actually_done(run):
    truth = table(run, "ground_truth.csv")
    work = table(run, "actual_duty.csv")["duty_actual"].cumsum().to_numpy()

    assert list(truth.columns) == ["day", "joint", "wear", "service_day"]
    assert len(truth) == DAYS * len(JOINTS)
    rates = wear_rates(0)                                                    # this run's own rate for each joint
    for joint in JOINTS:
        wear = truth[truth["joint"] == joint].sort_values("day")["wear"].to_numpy()
        assert wear == pytest.approx(config.K_WEAR * rates[joint] * work, rel=1e-12)


def test_service_day(run):
    truth = table(run, "ground_truth.csv")

    for joint in JOINTS:
        rows = truth[truth["joint"] == joint].sort_values("day")
        passed = rows[rows["wear"] >= config.FAIL_W]
        assert rows["service_day"].nunique(dropna=False) == 1                # one value per joint, on every row
        if len(passed):
            assert rows["service_day"].iloc[0] == passed["day"].iloc[0]      # the FIRST day at or past the threshold
        else:
            assert rows["service_day"].isna().all()                          # never reached: left empty

    # this run must hold both cases, or one branch above is never checked
    final = truth[truth["day"] == DAYS - 1].set_index("joint")["wear"]
    assert final[3] >= config.FAIL_W > final[0]
    assert 0 < truth[truth["joint"] == 3]["service_day"].iloc[0] < DAYS - 1


def test_the_schedule_file_is_the_plan_and_the_actual_file_is_not(run):
    schedule = table(run, "schedule.csv")
    actual = table(run, "actual_duty.csv")

    assert list(schedule.columns) == ["day", "duty_planned"]
    assert list(actual.columns) == ["day", "duty_actual"]
    assert schedule["day"].tolist() == actual["day"].tolist() == list(range(DAYS))
    assert schedule["duty_planned"].tolist() == [planned_duty(SCENARIO, d) for d in range(DAYS)]
    assert (actual["duty_actual"] > 0).all()
    assert (actual["duty_actual"] != schedule["duty_planned"]).all()


def test_sweeps_carry_the_planned_duty_never_the_actual(run):
    sweeps = table(run, "sweeps.parquet")
    planned = table(run, "schedule.csv").set_index("day")["duty_planned"]
    actual = table(run, "actual_duty.csv").set_index("day")["duty_actual"]

    assert (sweeps["duty_planned"] == sweeps["day"].map(planned)).all()
    assert (sweeps["duty_planned"] != sweeps["day"].map(actual)).all()


def test_temperature_follows_the_work_actually_done(run):
    sweeps = table(run, "sweeps.parquet")
    actual = table(run, "actual_duty.csv")["duty_actual"].to_numpy()

    for joint in JOINTS:
        recorded = sweeps[sweeps["joint"] == joint].groupby("day")["temperature_c"].first().to_numpy()
        temp, expected = config.AMBIENT_C, []
        for duty in actual:
            temp = next_temperature(temp, duty, config.WORK_SPEED[joint])
            expected.append(temp)
        assert recorded == pytest.approx(expected, rel=1e-12)
    assert sweeps.groupby(["day", "joint"])["temperature_c"].nunique().max() == 1    # one temperature per sweep


def test_fit_sanity_over_the_run(run):
    """Coulomb friction, read off the saved sweeps, has grown in proportion to the true wear."""
    sweeps = table(run, "sweeps.parquet")
    truth = table(run, "ground_truth.csv")
    wear = truth[truth["joint"] == 3].sort_values("day")["wear"].to_numpy()

    fc = []
    for day in (0, DAYS - 1):
        rows = sweeps[(sweeps["joint"] == 3) & (sweeps["day"] == day)]
        fitted, _ = fit_friction(rows["v_measured"], rows["friction_torque"], config.RATED_RAD_S[3])
        warmth = 1 - config.TEMP_COEF * (rows["temperature_c"].iloc[0] - config.TEMP_REF_C)
        fc.append(fitted / warmth)                                           # take the temperature effect out

    expected = (1 + config.WEAR_GAIN_FC * wear[-1]) / (1 + config.WEAR_GAIN_FC * wear[0])
    assert expected > 1.8                                                    # the wear did grow in this run
    assert fc[1] / fc[0] == pytest.approx(expected, rel=0.03)


def test_a_shorter_run_is_the_start_of_a_longer_one(run, tmp_path):
    simulate(SCENARIO, 2, seed=0, out_dir=str(tmp_path), joints=JOINTS)

    long_run = table(run, "sweeps.parquet")
    pd.testing.assert_frame_equal(table(str(tmp_path), "sweeps.parquet"), long_run[long_run["day"] < 2].reset_index(drop=True))
    assert table(str(tmp_path), "actual_duty.csv")["duty_actual"].tolist() == table(run, "actual_duty.csv")["duty_actual"].tolist()[:2]


def test_the_work_done_does_not_depend_on_which_joints_are_measured(run, tmp_path):
    simulate(SCENARIO, DAYS, seed=0, out_dir=str(tmp_path), joints=(3,))

    assert file_bytes(str(tmp_path), "actual_duty.csv") == file_bytes(run, "actual_duty.csv")
    both = table(run, "ground_truth.csv")
    alone = table(str(tmp_path), "ground_truth.csv")
    assert alone["wear"].tolist() == both[both["joint"] == 3]["wear"].tolist()


def test_every_run_has_wear_rates_of_its_own():
    first, again, other = wear_rates(0), wear_rates(0), wear_rates(1)

    assert first.shape == (config.N_JOINTS,)
    assert first.tolist() == again.tolist()                                  # the seed decides them
    assert (first != other).all()
    assert (first != config.RATE).all()                                      # no joint keeps exactly its nominal rate
    assert len(set((first / config.RATE).round(9))) == config.N_JOINTS       # each joint has a factor of its own
    assert (first > 0).all()


def test_the_wear_rates_scatter_around_the_nominal_rate_by_the_stated_spread():
    ratio = np.array([wear_rates(seed) for seed in range(3000)]) / config.RATE

    assert ratio.mean() == pytest.approx(1.0, abs=0.005)                     # on average a joint has its nominal rate
    assert ratio.mean(axis=0) == pytest.approx(1.0, abs=0.02)                # and that holds for each joint
    assert np.log(ratio).std() == pytest.approx(config.RATE_SPREAD, abs=0.01)


def test_with_no_spread_every_run_has_the_nominal_rates(monkeypatch):
    monkeypatch.setattr(config, "RATE_SPREAD", 0.0)

    assert wear_rates(7).tolist() == config.RATE.tolist()


def test_the_wear_rates_do_not_disturb_the_work_or_the_sensor(run, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RATE_SPREAD", 0.0)
    simulate(SCENARIO, 2, seed=0, out_dir=str(tmp_path), joints=JOINTS)

    # same seed, different wear rates: the work done is the same, the wear is not
    assert table(str(tmp_path), "actual_duty.csv")["duty_actual"].tolist() == table(run, "actual_duty.csv")["duty_actual"].tolist()[:2]
    assert table(str(tmp_path), "ground_truth.csv")["wear"].tolist() != table(run, "ground_truth.csv")["wear"].tolist()[:4]


def test_isolation_in_the_saved_dataset(fast, tmp_path, monkeypatch):
    """Only joint 3 wears. Read from the saved file, only joint 3's friction rises."""
    only_joint_3 = np.zeros(config.N_JOINTS)
    only_joint_3[3] = config.RATE[3]
    monkeypatch.setattr(config, "RATE", only_joint_3)
    simulate(SCENARIO, DAYS, seed=0, out_dir=str(tmp_path))

    sweeps = table(str(tmp_path), "sweeps.parquet")
    truth = table(str(tmp_path), "ground_truth.csv")
    assert truth[truth["joint"] == 3]["wear"].max() > 0.6
    assert truth[truth["joint"] != 3]["wear"].max() == 0.0

    for joint in range(config.N_JOINTS):
        fc = []
        for day in (0, DAYS - 1):
            rows = sweeps[(sweeps["joint"] == joint) & (sweeps["day"] == day)]
            fitted, _ = fit_friction(rows["v_measured"], rows["friction_torque"], config.RATED_RAD_S[joint])
            fc.append(fitted / (1 - config.TEMP_COEF * (rows["temperature_c"].iloc[0] - config.TEMP_REF_C)))
        change = fc[1] / fc[0] - 1
        if joint == 3:
            assert change > 0.5
        else:
            assert abs(change) < 0.03


def test_a_watcher_is_told_each_day_what_was_measured_and_changes_nothing(run, tmp_path):
    days = []

    def on_day(day, rows, world):
        days.append((day, len(rows), {r["joint"] for r in rows}, {r["day"] for r in rows}, "wear" in rows[0]))

    simulate(SCENARIO, DAYS, seed=0, out_dir=str(tmp_path), joints=JOINTS, on_day=on_day)

    assert days == [(d, 18 * len(JOINTS), set(JOINTS), {d}, False) for d in range(DAYS)]      # the day's sweeps, never the wear
    for name in FILES:
        assert file_bytes(str(tmp_path), name) == file_bytes(run, name), name


def test_a_watcher_can_stop_the_run_and_then_nothing_is_written(fast, tmp_path):
    class Stop(Exception):
        pass

    def on_day(day, rows, world):
        if day == 2:
            raise Stop

    with pytest.raises(Stop):
        simulate(SCENARIO, DAYS, seed=0, out_dir=str(tmp_path / "out"), joints=JOINTS, on_day=on_day)
    assert not os.path.exists(tmp_path / "out")


def test_a_watcher_of_the_steps_changes_nothing(run, tmp_path):
    steps = []
    simulate(SCENARIO, 2, seed=0, out_dir=str(tmp_path), joints=JOINTS, on_step=lambda world: steps.append(1))

    # 2 days x 2 joints x 18 speeds x 150 time steps (0.1 s + 0.05 s in these tests)
    assert len(steps) == 2 * len(JOINTS) * 18 * 150
    long_run = table(run, "sweeps.parquet")
    pd.testing.assert_frame_equal(table(str(tmp_path), "sweeps.parquet"), long_run[long_run["day"] < 2].reset_index(drop=True))


def test_without_events_the_log_has_only_its_header(run):
    events = table(run, "events.csv")

    assert list(events.columns) == ["day", "joint", "event"]
    assert len(events) == 0


def test_a_regrease_cuts_the_wear_and_is_logged(run, tmp_path):
    simulate(SCENARIO, 4, seed=0, out_dir=str(tmp_path), joints=JOINTS, events=[(2, 3, "regrease")])

    plain = table(run, "ground_truth.csv").pivot(index="day", columns="joint", values="wear")
    greased = table(str(tmp_path), "ground_truth.csv").pivot(index="day", columns="joint", values="wear")
    growth = plain[3].diff()                                                 # what each day's work adds to joint 3

    # the grease goes in on the morning of day 2: 0.3 of the wear so far stays, then the day's work is added
    assert greased[3][1] == pytest.approx(plain[3][1])
    assert greased[3][2] == pytest.approx(config.REGREASE_KEEP * plain[3][1] + growth[2])
    assert greased[3][3] == pytest.approx(greased[3][2] + growth[3])
    assert greased[0].tolist() == pytest.approx(plain[0].tolist()[:4])       # the other joint is untouched
    assert table(str(tmp_path), "events.csv").values.tolist() == [[2, 3, "regrease"]]


@pytest.mark.parametrize("event, message", [
    ((2, 3, "polish"), "polish"),          # not a known event
    ((9, 3, "regrease"), "day 9"),         # after the last day: it would silently do nothing
    ((2, 5, "regrease"), "joint 5"),       # a joint that is not simulated
])
def test_an_event_that_cannot_happen_is_an_error(fast, tmp_path, event, message):
    with pytest.raises(ValueError, match=message):
        simulate(SCENARIO, 4, seed=0, out_dir=str(tmp_path), joints=JOINTS, events=[event])
    assert os.listdir(tmp_path) == []


def test_a_run_needs_at_least_one_day(fast, tmp_path):
    with pytest.raises(ValueError, match="at least 1 day"):
        simulate(SCENARIO, 0, seed=0, out_dir=str(tmp_path))


def test_by_default_all_six_joints_are_simulated(fast, tmp_path):
    simulate("ramp_late", 1, seed=0, out_dir=str(tmp_path))

    assert sorted(table(str(tmp_path), "sweeps.parquet")["joint"].unique()) == list(range(config.N_JOINTS))
    assert sorted(table(str(tmp_path), "ground_truth.csv")["joint"]) == list(range(config.N_JOINTS))
