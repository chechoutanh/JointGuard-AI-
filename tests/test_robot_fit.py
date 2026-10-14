"""Fitting Coulomb and viscous friction to a sweep: torque = Fc * sign(v) + Fv * v."""

import numpy as np
import pytest

from robot import config
from robot.fit import fit_friction


def test_it_recovers_the_two_numbers_from_four_points():
    # Fc = 2, Fv = 0.5: torque at 0.5 rad/s is 2 + 0.25, at 1 rad/s it is 2 + 0.5
    v = np.array([-1.0, -0.5, 0.5, 1.0])
    tau = np.array([-2.5, -2.25, 2.25, 2.5])

    fc, fv = fit_friction(v, tau, rated=1.0)

    assert fc == pytest.approx(2.0)
    assert fv == pytest.approx(0.5)


def test_points_slower_than_the_limit_are_left_out():
    # the limit is 0.08 of rated speed: with rated 2.0, anything slower than 0.16 rad/s
    assert config.FIT_MIN_FRAC == 0.08
    v = np.array([-1.0, -0.5, -0.15, 0.15, 0.5, 1.0])
    tau = np.array([-2.5, -2.25, 99.0, -99.0, 2.25, 2.5])       # the two slow points are nonsense

    fc, fv = fit_friction(v, tau, rated=2.0)

    assert fc == pytest.approx(2.0)
    assert fv == pytest.approx(0.5)


def test_a_point_exactly_on_the_limit_is_kept():
    v = np.array([-0.5, -0.08, 0.08, 0.5])
    tau = 2.0 * np.sign(v) + 0.5 * v
    tau[1], tau[2] = -3.0, 3.0                                  # if these were dropped, Fc would be 2.0

    fc, _ = fit_friction(v, tau, rated=1.0)

    assert fc > 2.0


def test_noise_averages_out_over_a_sweep():
    rng = np.random.default_rng(0)
    v = np.concatenate([-np.geomspace(0.1, 1.0, 9)[::-1], np.geomspace(0.1, 1.0, 9)])
    tau = 1.8 * np.sign(v) + 0.55 * v + rng.normal(0.0, 0.02, v.size)

    fc, fv = fit_friction(v, tau, rated=1.0)

    assert fc == pytest.approx(1.8, abs=0.03)
    assert fv == pytest.approx(0.55, abs=0.06)


def test_too_few_usable_points_is_an_error_not_a_number():
    with pytest.raises(ValueError, match="at least 2"):
        fit_friction(np.array([0.01, 0.02, 0.5]), np.array([1.0, 1.0, 2.0]), rated=1.0)
