"""The health-check sweep, run in PyBullet without a window.

One joint moves at 18 constant speeds while the others are held. The torque
left after gravity is taken out is the friction. These tests inject a known
friction and check that the sweep reads it back.
"""

import numpy as np
import pytest

from robot import config, sweep
from robot.fit import fit_friction
from robot.sweep import run_health_check, start_angle
from robot.world import connect, disconnect, joint_states

JOINTS = range(config.N_JOINTS)
HEALTHY = np.zeros(config.N_JOINTS)
WARM = np.full(config.N_JOINTS, config.TEMP_REF_C)


@pytest.fixture(scope="module")
def world():
    world = connect()
    yield world
    disconnect(world)


def columns(rows):
    return np.array([r["v_measured"] for r in rows]), np.array([r["friction_torque"] for r in rows])


def fitted_coulomb(rows):
    v, tau = columns(rows)
    return fit_friction(v, tau, config.RATED_RAD_S[rows[0]["joint"]])[0]


@pytest.fixture(scope="module")
def day0(world):
    """A sweep of every joint with no wear."""
    return {j: run_health_check(world, j, HEALTHY, WARM, np.random.default_rng(j)) for j in JOINTS}


@pytest.fixture(scope="module")
def joint3_worn(world):
    """A sweep of every joint when only joint 3 is worn, up to the service threshold."""
    wear = HEALTHY.copy()
    wear[3] = config.FAIL_W
    return {j: run_health_check(world, j, wear, WARM, np.random.default_rng(100 + j)) for j in JOINTS}


def test_sweep_shape(day0):
    v, tau = columns(day0[3])

    assert len(v) == 18
    assert (np.sign(tau) == np.sign(v)).all()                    # friction opposes the motion
    assert tau + tau[::-1] == pytest.approx(0.0, abs=0.15)       # antisymmetric: the curve passes through zero
    assert abs(tau.mean()) < 0.05
    assert abs(tau[-1]) > abs(tau[9]) + 0.3                      # faster costs more: the viscous part


def test_with_no_friction_the_sweep_reads_zero(world, monkeypatch):
    # gravity on joint 1 is 33 N m at this posture. If it were not taken out exactly, it would show here.
    monkeypatch.setattr(sweep, "friction", lambda v, wear, temp, joint: 0.0 * v)
    monkeypatch.setattr(config, "NOISE_NM", 0.0)

    for joint in (1, 3, 5):
        _, tau = columns(run_health_check(world, joint, HEALTHY, WARM, np.random.default_rng(0)))
        assert np.abs(tau).max() < 1e-3 * config.JOINT_SIZE[joint]


def test_fit_sanity(day0, joint3_worn):
    for joint in JOINTS:
        expected = config.FC0 * config.JOINT_SIZE[joint]
        assert fitted_coulomb(day0[joint]) == pytest.approx(expected, rel=0.05)

    # at the service threshold Coulomb friction has grown by WEAR_GAIN_FC * FAIL_W
    index = (fitted_coulomb(joint3_worn[3]) / fitted_coulomb(day0[3]) - 1) / config.WEAR_GAIN_FC
    assert index == pytest.approx(config.FAIL_W, abs=0.05)


def test_a_worn_joint_sits_clearly_higher(day0, joint3_worn):
    _, healthy = columns(day0[3])
    _, worn = columns(joint3_worn[3])

    assert (np.abs(worn) > 1.5 * np.abs(healthy)).all()


def test_isolation(day0, joint3_worn):
    for joint in JOINTS:
        change = fitted_coulomb(joint3_worn[joint]) / fitted_coulomb(day0[joint]) - 1
        if joint == 3:
            assert change > 1.0
        else:
            assert abs(change) < 0.05


def test_only_the_joints_own_temperature_changes_its_friction(world, day0):
    temperature = WARM.copy()
    temperature[2] = 15.0                                        # 20 C colder: friction x (1 + 0.008 * 20) = 1.16

    cold = run_health_check(world, 2, HEALTHY, temperature, np.random.default_rng(0))
    neighbour = run_health_check(world, 3, HEALTHY, temperature, np.random.default_rng(0))

    assert fitted_coulomb(cold) / fitted_coulomb(day0[2]) == pytest.approx(1.16, abs=0.03)
    assert fitted_coulomb(neighbour) / fitted_coulomb(day0[3]) == pytest.approx(1.0, abs=0.03)


def test_the_same_seed_gives_the_same_rows(world, day0):
    again = run_health_check(world, 3, HEALTHY, WARM, np.random.default_rng(3))
    other = run_health_check(world, 3, HEALTHY, WARM, np.random.default_rng(4))

    assert again == day0[3]
    assert columns(other)[1].tolist() != columns(day0[3])[1].tolist()
    assert columns(other)[0].tolist() == columns(day0[3])[0].tolist()     # the noise is on the torque only


def test_watching_the_sweep_changes_no_reading(world, monkeypatch):
    monkeypatch.setattr(config, "SETTLE_S", 0.01)                # 20 time steps at each of 18 speeds: 360 steps
    monkeypatch.setattr(config, "RECORD_S", 0.01)
    plain = run_health_check(world, 3, HEALTHY, WARM, np.random.default_rng(0))

    seen = []
    watched = run_health_check(world, 3, HEALTHY, WARM, np.random.default_rng(0), on_step=lambda w: seen.append(joint_states(w)[0][3]))

    assert watched == plain
    assert len(seen) == 360                                      # called once after every time step
    assert seen[0] != seen[-1]                                   # and it sees the joint where it is at that moment


def test_the_other_joints_are_held_still(world):
    run_health_check(world, 3, HEALTHY, WARM, np.random.default_rng(0))
    q, v = joint_states(world)
    others = [j for j in world.joints if j != 3]

    assert q[others] == pytest.approx(np.array(config.POSTURE)[others], abs=1e-4)
    assert np.abs(v[others]).max() < 1e-3


def test_measured_speed_is_a_little_below_the_target(day0):
    for joint in JOINTS:
        ratio = np.array([r["v_measured"] / r["v_target"] for r in day0[joint]])
        assert (ratio < 1.0).all()                               # a proportional loop always lags
        assert (ratio > 0.9).all()


def test_every_speed_point_stays_usable_by_the_fit(world, day0):
    for joint in JOINTS:
        v, _ = columns(day0[joint])
        assert (np.abs(v) >= config.FIT_MIN_FRAC * config.RATED_RAD_S[joint]).all()

    # worst case: more wear than the service threshold, and a cold joint (both raise friction, so the lag)
    worst = run_health_check(world, 3, np.full(config.N_JOINTS, 1.0), np.full(config.N_JOINTS, 15.0), np.random.default_rng(0))
    v, _ = columns(worst)
    assert (np.abs(v) >= config.FIT_MIN_FRAC * config.RATED_RAD_S[3]).all()


def test_the_swept_joint_stays_inside_its_limits(world):
    seconds = config.SETTLE_S + config.RECORD_S
    for joint in JOINTS:
        for frac in config.SPEED_FRACS:
            v_target = frac * config.RATED_RAD_S[joint]
            start = start_angle(joint, v_target)
            end = start + v_target * seconds
            assert world.lower[joint] + 0.1 < min(start, end)
            assert max(start, end) < world.upper[joint] - 0.1
            assert (start + end) / 2 == pytest.approx(config.POSTURE[joint])   # the travel is centred on the posture


def test_rows_hold_the_measurement_and_never_the_wear(world):
    temperature = np.linspace(30.0, 40.0, config.N_JOINTS)
    rows = run_health_check(world, 2, HEALTHY, temperature, np.random.default_rng(0))

    assert set(rows[0]) == {"joint", "v_target", "v_measured", "friction_torque", "temperature_c", "posture_q"}
    assert [r["joint"] for r in rows] == [2] * 18
    assert [r["v_target"] for r in rows] == pytest.approx(np.array(config.SPEED_FRACS) * config.RATED_RAD_S[2])
    assert rows[0]["temperature_c"] == temperature[2]
    assert rows[0]["posture_q"] == list(config.POSTURE)


def test_the_speed_grid_has_nine_points_each_way_and_none_below_the_fit_limit():
    fracs = np.array(config.SPEED_FRACS)

    assert len(fracs) == 18
    assert fracs.tolist() == pytest.approx((-fracs[::-1]).tolist())
    assert np.abs(fracs).min() > config.FIT_MIN_FRAC
    assert np.abs(fracs).max() == pytest.approx(0.8)
