"""The realism switches of milestone M4. Every one is off by default; each test turns one on.

  WEAR_NOISE        the wear a day adds varies from day to day
  WEAR_ACCEL        wear speeds up late in life
  WEAR_AFFECTS_FV   wear also raises viscous friction
  MODEL_MISMATCH    the real arm's link masses differ from the model that takes gravity out
  SENSOR_FAULTS     a sweep is sometimes missing, a reading is sometimes wild, every reading is rounded
"""

import os

import numpy as np
import pandas as pd
import pytest

from robot import config, sweep
from robot.fit import fit_friction
from robot.guard import assert_no_leakage
from robot.simulate import link_mass_factors, simulate, wear_growth
from robot.sweep import run_health_check, sensor_faults
from robot.world import connect, disconnect, gravity_torque

DAYS = 5
JOINTS = (0, 3)
SCENARIO = "ramp_early"
N = config.N_JOINTS
WARM = np.full(N, config.TEMP_REF_C)


def test_every_switch_is_off_until_it_is_approved():
    assert not any([config.WEAR_NOISE, config.WEAR_ACCEL, config.WEAR_AFFECTS_FV, config.MODEL_MISMATCH, config.SENSOR_FAULTS])


# ---------------------------------------------------------------------------
# How much wear one day adds
# ---------------------------------------------------------------------------

def test_with_the_switches_off_a_day_adds_rate_times_work():
    # rates 1 and 2, work 0.6: 1 * 0.6 / 480 and 2 * 0.6 / 480, whatever the wear so far
    growth = wear_growth(np.array([0.0, 0.9]), np.array([1.0, 2.0]), 0.6, np.random.default_rng(0))

    assert growth == pytest.approx([0.00125, 0.0025])


def test_with_the_switches_off_no_random_number_is_used():
    rng = np.random.default_rng(0)
    wear_growth(np.zeros(N), np.ones(N), 0.6, rng)

    assert rng.random() == np.random.default_rng(0).random()


def test_wear_accel_leaves_a_young_joint_alone_and_speeds_up_an_old_one(monkeypatch):
    monkeypatch.setattr(config, "WEAR_ACCEL", True)
    growth = wear_growth(np.array([0.5, 0.6, 0.8]), np.ones(3), 0.6, np.random.default_rng(0))

    # nothing up to a wear of 0.6; at 0.8 the factor is 1 + 1.5 * (0.8 - 0.6) = 1.3
    assert growth == pytest.approx([0.00125, 0.00125, 0.00125 * 1.3])


def test_wear_noise_is_fair_of_the_stated_size_and_different_for_each_joint_and_day(monkeypatch):
    monkeypatch.setattr(config, "WEAR_NOISE", True)
    rng = np.random.default_rng(0)
    ratio = np.array([wear_growth(np.zeros(N), np.ones(N), 0.6, rng) for _ in range(3000)]) / 0.00125

    assert ratio.mean() == pytest.approx(1.0, abs=0.005)                     # on average a day adds what it should
    assert np.log(ratio).std() == pytest.approx(config.WEAR_NOISE_SIGMA, abs=0.01)
    assert len(set(ratio[0].round(12))) == N                                 # each joint has its own luck
    assert not np.allclose(ratio[0], ratio[1])                               # and so has each day


# ---------------------------------------------------------------------------
# The switches inside a run
# ---------------------------------------------------------------------------

@pytest.fixture()
def fast(monkeypatch):
    """Short sweeps and wear about 100 times faster: joint 3 passes its threshold in 5 days."""
    monkeypatch.setattr(config, "SETTLE_S", 0.1)
    monkeypatch.setattr(config, "RECORD_S", 0.05)
    monkeypatch.setattr(config, "K_WEAR", 0.22)


@pytest.fixture()
def plain(fast, tmp_path):
    """A run with every switch off, to compare with."""
    return simulate(SCENARIO, DAYS, seed=0, out_dir=str(tmp_path / "plain"), joints=JOINTS)


def file_bytes(folder, name):
    with open(os.path.join(folder, name), "rb") as f:
        return f.read()


def wear_table(folder):
    return pd.read_csv(os.path.join(folder, "ground_truth.csv")).pivot(index="day", columns="joint", values="wear")


def test_wear_noise_changes_the_wear_and_not_the_work(plain, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "WEAR_NOISE", True)
    noisy = simulate(SCENARIO, DAYS, seed=0, out_dir=str(tmp_path / "noisy"), joints=JOINTS)

    assert file_bytes(noisy, "actual_duty.csv") == file_bytes(plain, "actual_duty.csv")
    ratio = wear_table(noisy).diff().iloc[1:] / wear_table(plain).diff().iloc[1:]      # a day's wear, with and without
    assert (ratio > 0.5).all().all() and (ratio < 2.0).all().all()
    assert ratio.to_numpy().std() > 0.05


def test_wear_accel_changes_nothing_until_a_joint_is_past_the_starting_wear(plain, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "WEAR_ACCEL", True)
    fast_end = wear_table(simulate(SCENARIO, DAYS, seed=0, out_dir=str(tmp_path / "accel"), joints=JOINTS))
    before = wear_table(plain)

    assert before[0].max() < config.WEAR_ACCEL_FROM                          # joint 0 never gets there in this run
    assert fast_end[0].tolist() == before[0].tolist()
    young = before[3].shift(1, fill_value=0.0) <= config.WEAR_ACCEL_FROM     # days that start at or below 0.6
    assert young.sum() >= 2 and (~young).sum() >= 1
    first_old = int((~young).idxmax())
    assert fast_end[3][:first_old].tolist() == before[3][:first_old].tolist()
    assert fast_end[3][DAYS - 1] > before[3][DAYS - 1] * 1.02


def test_model_mismatch_changes_the_readings_and_not_the_wear(plain, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "MODEL_MISMATCH", True)
    other = simulate(SCENARIO, DAYS, seed=0, out_dir=str(tmp_path / "mismatch"), joints=JOINTS)

    assert file_bytes(other, "ground_truth.csv") == file_bytes(plain, "ground_truth.csv")
    assert file_bytes(other, "sweeps.parquet") != file_bytes(plain, "sweeps.parquet")


def test_sensor_faults_drop_whole_sweeps_and_leave_the_wear_alone(plain, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SENSOR_FAULTS", True)
    monkeypatch.setattr(config, "MISSED_SWEEP_SHARE", 0.4)                   # far more than the real setting, to see it in 10 sweeps
    faulty = simulate(SCENARIO, DAYS, seed=0, out_dir=str(tmp_path / "faulty"), joints=JOINTS)

    sweeps = pd.read_parquet(os.path.join(faulty, "sweeps.parquet"))
    per_sweep = sweeps.groupby(["day", "joint"]).size()
    assert 0 < len(per_sweep) < DAYS * len(JOINTS)                           # some sweeps are missing
    assert (per_sweep == 18).all()                                           # a sweep is there whole or not at all
    assert file_bytes(faulty, "ground_truth.csv") == file_bytes(plain, "ground_truth.csv")
    assert len(pd.read_csv(os.path.join(faulty, "schedule.csv"))) == DAYS    # the days themselves are all there
    assert_no_leakage(sweeps.columns)

    # a reading that is still there is the plain run's reading, rounded, or a wild one. Nothing else moved.
    both = sweeps.merge(pd.read_parquet(os.path.join(plain, "sweeps.parquet")), on=["day", "joint", "v_target"], suffixes=("", "_plain"))
    size = config.JOINT_SIZE[both["joint"].to_numpy()]
    off = np.abs(both["friction_torque"] - both["friction_torque_plain"]).to_numpy() / size
    rounded = off <= config.QUANT_NM / 2 + 1e-9
    wild = np.abs(off - config.OUTLIER_NM) <= config.QUANT_NM / 2 + 1e-9
    assert (rounded | wild).all()
    assert (both["v_measured"] == both["v_measured_plain"]).all()


def test_with_every_switch_on_the_same_seed_still_gives_the_same_files(fast, tmp_path, monkeypatch):
    for name in ("WEAR_NOISE", "WEAR_ACCEL", "WEAR_AFFECTS_FV", "MODEL_MISMATCH", "SENSOR_FAULTS"):
        monkeypatch.setattr(config, name, True)
    first = simulate(SCENARIO, DAYS, seed=0, out_dir=str(tmp_path / "a"), joints=JOINTS)
    again = simulate(SCENARIO, DAYS, seed=0, out_dir=str(tmp_path / "b"), joints=JOINTS)
    other = simulate(SCENARIO, DAYS, seed=1, out_dir=str(tmp_path / "c"), joints=JOINTS)

    for name in ("sweeps.parquet", "schedule.csv", "actual_duty.csv", "ground_truth.csv", "events.csv"):
        assert file_bytes(first, name) == file_bytes(again, name), name
    assert file_bytes(first, "sweeps.parquet") != file_bytes(other, "sweeps.parquet")
    assert_no_leakage(pd.read_parquet(os.path.join(first, "sweeps.parquet")).columns)


# ---------------------------------------------------------------------------
# Model mismatch, on one sweep
# ---------------------------------------------------------------------------

def columns(rows):
    return np.array([r["v_measured"] for r in rows]), np.array([r["friction_torque"] for r in rows])


def test_link_mass_factors_are_within_three_percent_and_belong_to_the_seed():
    first, again, other = link_mass_factors(0), link_mass_factors(0), link_mass_factors(1)

    assert first.shape == (7,)                                               # one per link of the arm
    assert first.tolist() == again.tolist()
    assert first.tolist() != other.tolist()
    assert (np.abs(first - 1) <= config.MASS_ERROR).all()
    assert np.abs(first - 1).max() > 0.005


def test_with_heavier_links_the_model_keeps_its_gravity_and_the_sweep_reads_the_difference(monkeypatch):
    monkeypatch.setattr(sweep, "friction", lambda v, wear, temp, joint: 0.0 * v)
    monkeypatch.setattr(config, "NOISE_NM", 0.0)
    nominal = connect()
    heavier = connect(mass_factors=np.full(7, 1.03))                         # every link 3% heavier than the model thinks
    try:
        model_gravity = gravity_torque(heavier, config.POSTURE)
        assert model_gravity == pytest.approx(gravity_torque(nominal, config.POSTURE), abs=1e-9)

        # no friction at all: what the sweep of joint 1 reads is the gravity the model does not know about,
        # 3% of the 33 N m on that joint, the same for both directions
        _, tau = columns(run_health_check(heavier, 1, np.zeros(N), WARM, np.random.default_rng(0)))
        assert tau.mean() == pytest.approx(0.03 * model_gravity[1], rel=0.1)
        assert abs(tau.mean()) > 0.8
    finally:
        disconnect(nominal)
        disconnect(heavier)


def test_the_fit_does_not_take_a_gravity_error_for_coulomb_friction():
    heavier = connect(mass_factors=np.full(7, 1.03))
    try:
        for joint in (1, 3):
            v, tau = columns(run_health_check(heavier, joint, np.zeros(N), WARM, np.random.default_rng(joint)))
            fc, _ = fit_friction(v, tau, config.RATED_RAD_S[joint])
            # the offset is the same for both directions, and Coulomb friction is the part that changes sign
            assert fc == pytest.approx(config.FC0 * config.JOINT_SIZE[joint], rel=0.05)
            assert abs(tau.mean()) > 0.2 * config.JOINT_SIZE[joint]              # the offset is really there
    finally:
        disconnect(heavier)


# ---------------------------------------------------------------------------
# Wear that also raises viscous friction, on one sweep
# ---------------------------------------------------------------------------

def test_when_wear_raises_viscous_friction_the_fit_shows_it_and_coulomb_still_gives_the_wear(monkeypatch):
    monkeypatch.setattr(config, "WEAR_AFFECTS_FV", True)
    world = connect()
    try:
        new = columns(run_health_check(world, 3, np.zeros(N), WARM, np.random.default_rng(0)))
        worn = columns(run_health_check(world, 3, np.full(N, 0.8), WARM, np.random.default_rng(1)))
    finally:
        disconnect(world)
    fc_new, fv_new = fit_friction(*new, config.RATED_RAD_S[3])
    fc_worn, fv_worn = fit_friction(*worn, config.RATED_RAD_S[3])

    assert fv_worn / fv_new == pytest.approx(1 + 0.9 * 0.8, rel=0.10)        # viscous: 0.55 * (1 + 0.9 * 0.8) = 0.946
    assert (fc_worn / fc_new - 1) / config.WEAR_GAIN_FC == pytest.approx(0.8, abs=0.05)


# ---------------------------------------------------------------------------
# Sensor faults, on one sweep
# ---------------------------------------------------------------------------

def made_up_sweep(joint, torques):
    return [{"joint": joint, "v_target": 0.1 * (i + 1), "v_measured": 0.095 * (i + 1), "friction_torque": t,
             "temperature_c": 35.0, "posture_q": list(config.POSTURE)} for i, t in enumerate(torques)]


TORQUES = [1.8734, 1.9021, 1.9577, 2.0143, 2.1099, 2.2468]


def test_every_reading_is_rounded_to_the_sensors_step(monkeypatch):
    monkeypatch.setattr(config, "MISSED_SWEEP_SHARE", 0.0)
    monkeypatch.setattr(config, "OUTLIER_SHARE", 0.0)
    rows = made_up_sweep(3, TORQUES)

    out = sensor_faults(rows, np.random.default_rng(0))

    # joint 3 has size 1, so its step is 0.01 N m: 1.8734 -> 1.87, 1.9577 -> 1.96
    assert [r["friction_torque"] for r in out] == pytest.approx([1.87, 1.90, 1.96, 2.01, 2.11, 2.25], abs=1e-9)
    assert [r["friction_torque"] for r in rows] == TORQUES                  # the rows passed in are not changed
    for before, after in zip(rows, out):
        assert {k: v for k, v in after.items() if k != "friction_torque"} == {k: v for k, v in before.items() if k != "friction_torque"}


def test_the_step_is_sized_to_the_joint(monkeypatch):
    monkeypatch.setattr(config, "MISSED_SWEEP_SHARE", 0.0)
    monkeypatch.setattr(config, "OUTLIER_SHARE", 0.0)
    step = config.QUANT_NM * config.JOINT_SIZE[5]                            # 0.01 * 0.021 = 0.00021 N m

    out = sensor_faults(made_up_sweep(5, [0.03781, 0.04012]), np.random.default_rng(0))

    for row, original in zip(out, [0.03781, 0.04012]):
        assert row["friction_torque"] / step == pytest.approx(round(row["friction_torque"] / step), abs=1e-6)
        assert abs(row["friction_torque"] - original) <= step / 2 + 1e-12


def test_a_missed_sweep_leaves_no_rows(monkeypatch):
    monkeypatch.setattr(config, "MISSED_SWEEP_SHARE", 1.0)

    assert sensor_faults(made_up_sweep(3, TORQUES), np.random.default_rng(0)) == []


def test_a_wild_reading_is_off_by_the_stated_amount_either_way(monkeypatch):
    monkeypatch.setattr(config, "MISSED_SWEEP_SHARE", 0.0)
    monkeypatch.setattr(config, "OUTLIER_SHARE", 1.0)
    rows = made_up_sweep(3, [2.0] * 40)

    shift = np.array([r["friction_torque"] for r in sensor_faults(rows, np.random.default_rng(0))]) - 2.0

    assert np.abs(shift) == pytest.approx(config.OUTLIER_NM, abs=1e-9)       # 0.2 N m on joint 3
    assert (shift > 0).any() and (shift < 0).any()

    # on the small joint 5 it is 0.2 * 0.021 = 0.0042 N m
    small = np.array([r["friction_torque"] for r in sensor_faults(made_up_sweep(5, [0.042] * 10), np.random.default_rng(0))]) - 0.042
    assert np.abs(small) == pytest.approx(config.OUTLIER_NM * config.JOINT_SIZE[5], abs=1e-9)


def test_faults_are_as_rare_as_the_settings_say():
    rng = np.random.default_rng(0)
    missed = wild = kept = 0
    for _ in range(20000):
        out = sensor_faults(made_up_sweep(3, [2.0]), rng)
        missed += not out
        kept += len(out)
        wild += sum(abs(r["friction_torque"] - 2.0) > 0.1 for r in out)

    assert missed / 20000 == pytest.approx(config.MISSED_SWEEP_SHARE, abs=0.004)       # 2 sweeps in 100
    assert wild / kept == pytest.approx(config.OUTLIER_SHARE, abs=0.002)               # 1 reading in 200
