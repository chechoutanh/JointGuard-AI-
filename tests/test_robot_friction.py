"""The friction law of the simulated joint, at points small enough to work out by hand.

Joint 3 is the reference joint (size 1): Coulomb 1.80 N m, static 2.90 N m,
viscous 0.55 N m s/rad, at 35 C and no wear.
"""

import math

import numpy as np
import pytest

from robot import config
from robot.friction import friction


def test_fast_and_healthy_it_is_coulomb_plus_viscous():
    # at 1 rad/s the static bump is gone (exp(-20^1.5) = 0) and tanh(100) = 1: 1.80 + 0.55 * 1
    assert friction(1.0, 0.0, 35.0, 3) == pytest.approx(2.35)


def test_it_opposes_either_direction_equally():
    assert friction(-1.0, 0.0, 35.0, 3) == pytest.approx(-2.35)
    assert friction(-0.07, 0.3, 28.0, 1) == pytest.approx(-friction(0.07, 0.3, 28.0, 1))


def test_it_is_zero_at_rest_and_has_no_jump_there():
    assert friction(0.0, 0.0, 35.0, 3) == 0.0
    # sign(v) would jump to 1.80 here; tanh gives static 2.90 * (1e-6 / 0.01) = 0.00029
    assert abs(friction(1e-6, 0.0, 35.0, 3)) < 1e-3


def test_at_the_stribeck_speed_part_of_the_static_bump_is_left():
    # v = 0.05: bump = (2.90 - 1.80) * exp(-1) = 0.4047, so 2.2047 * tanh(5) + 0.55 * 0.05
    expected = (1.80 + 1.10 * math.exp(-1.0)) * math.tanh(5.0) + 0.0275
    assert friction(0.05, 0.0, 35.0, 3) == pytest.approx(expected)
    assert expected == pytest.approx(2.2320, abs=1e-4)


def test_wear_raises_coulomb_friction():
    # Coulomb = 1.80 * (1 + 1.5 * 0.8) = 3.96; viscous unchanged while WEAR_AFFECTS_FV is off
    assert not config.WEAR_AFFECTS_FV
    assert friction(1.0, 0.8, 35.0, 3) == pytest.approx(3.96 + 0.55)


def test_wear_can_also_raise_viscous_friction_behind_its_switch(monkeypatch):
    monkeypatch.setattr(config, "WEAR_AFFECTS_FV", True)
    # viscous = 0.55 * (1 + 0.9 * 0.8) = 0.946
    assert friction(1.0, 0.8, 35.0, 3) == pytest.approx(3.96 + 0.946)


def test_a_warm_joint_has_less_friction():
    # 10 C above the reference: scale = 1 - 0.008 * 10 = 0.92
    assert friction(1.0, 0.0, 45.0, 3) == pytest.approx(2.35 * 0.92)
    assert friction(1.0, 0.0, 25.0, 3) == pytest.approx(2.35 * 1.08)


def test_each_joint_has_friction_of_its_own_size():
    for joint in range(config.N_JOINTS):
        assert friction(1.0, 0.0, 35.0, joint) == pytest.approx(2.35 * config.JOINT_SIZE[joint])
    assert config.JOINT_SIZE[3] == 1.0
    assert config.JOINT_SIZE[1] > config.JOINT_SIZE[3] > config.JOINT_SIZE[5]      # bigger at the shoulder


def test_it_takes_a_whole_array_of_speeds():
    v = np.array([-1.0, 0.0, 1.0])
    assert friction(v, 0.0, 35.0, 3) == pytest.approx([-2.35, 0.0, 2.35])
