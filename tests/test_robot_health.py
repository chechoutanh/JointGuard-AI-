"""From saved sweeps to a health index. Made-up sweeps, no physics: every number can be worked out by hand.

A made-up sweep of joint 3 (rated speed 1.3 rad/s): torque = Fc * sign(v) + 0.5 * v at eight speeds.
"""

import numpy as np
import pandas as pd
import pytest

from robot import config
from robot.health import daily_friction, health_index

SPEEDS = np.array([-1.0, -0.6, -0.3, -0.15, 0.15, 0.3, 0.6, 1.0])


def sweep_rows(day, joint, fc, temperature=35.0, fv=0.5):
    return [{"day": day, "joint": joint, "v_target": v, "v_measured": v, "friction_torque": fc * np.sign(v) + fv * v,
             "temperature_c": temperature} for v in SPEEDS]


def table(*sweeps):
    return pd.DataFrame([row for sweep in sweeps for row in sweep])


def test_one_row_per_day_with_the_fitted_friction_and_the_temperature():
    sweeps = table(sweep_rows(0, 3, 2.0, 31.0), sweep_rows(1, 3, 2.5, 33.0), sweep_rows(0, 1, 9.0, 30.0))

    daily = daily_friction(sweeps, 3)

    assert list(daily.columns) == ["day", "fc", "fv", "temperature_c"]
    assert daily["day"].tolist() == [0, 1]
    assert daily["fc"].tolist() == pytest.approx([2.0, 2.5])
    assert daily["fv"].tolist() == pytest.approx([0.5, 0.5])
    assert daily["temperature_c"].tolist() == [31.0, 33.0]


def test_a_day_without_a_sweep_has_no_row():
    sweeps = table(sweep_rows(0, 3, 2.0), sweep_rows(2, 3, 2.2))

    assert daily_friction(sweeps, 3)["day"].tolist() == [0, 2]


def test_a_joint_that_is_not_in_the_file_gives_an_empty_table():
    assert len(daily_friction(table(sweep_rows(0, 3, 2.0)), 5)) == 0


def test_health_index_by_hand():
    # the first 7 days are the joint's own reference: Fc 2.0. Then Fc 2.3 and 3.0.
    fc = np.array([2.0] * 7 + [2.3, 3.0])

    index = health_index(fc)

    assert config.BASELINE_DAYS == 7
    assert index[:7] == pytest.approx(0.0)
    # (2.3 / 2.0 - 1) / 1.5 = 0.1 and (3.0 / 2.0 - 1) / 1.5 = 0.3333
    assert index[7:] == pytest.approx([0.1, 1 / 3])


def test_the_reference_is_the_mean_of_the_first_days():
    fc = np.array([1.9, 2.1] + [2.0] * 5 + [3.0])                # mean of the first 7: 2.0

    assert health_index(fc)[-1] == pytest.approx(1 / 3)


def test_temperature_is_taken_out_before_the_index():
    # a joint at 45 C has 8% less friction than at 35 C. The same wear must give the same index.
    fc_true = np.array([2.0] * 7 + [3.0])
    temperature = np.array([35.0] * 7 + [45.0])
    fc_read = fc_true * (1 - 0.008 * (temperature - 35.0))

    assert health_index(fc_read)[-1] == pytest.approx((3.0 * 0.92 / 2.0 - 1) / 1.5)     # raw: reads low
    assert health_index(fc_read, temperature)[-1] == pytest.approx(1 / 3)                # taken out: right


def test_no_hindsight_a_later_day_changes_no_earlier_value():
    rng = np.random.default_rng(0)
    fc = 2.0 + np.cumsum(rng.random(40)) * 0.02
    temperature = 30 + 10 * rng.random(40)
    whole = health_index(fc, temperature)

    for today in range(1, 41):                                   # also inside the first week
        assert health_index(fc[:today], temperature[:today]).tolist() == whole[:today].tolist()


def test_inside_the_first_week_the_reference_is_the_mean_of_the_days_so_far():
    # references: 2.0, then (2.0 + 2.2) / 2 = 2.1, then 2.2
    index = health_index(np.array([2.0, 2.2, 2.4]))

    assert index.tolist() == pytest.approx([0.0, (2.2 / 2.1 - 1) / 1.5, (2.4 / 2.2 - 1) / 1.5])


def test_no_days_give_no_index():
    assert len(health_index(np.array([]))) == 0
