"""Joint temperature from one day to the next.

A joint settles at ambient 26 C plus 15 C per unit of duty (times how fast the
joint moves in the work cycle), and each day it covers 0.7 of the distance
from yesterday's temperature to that level.
"""

import numpy as np
import pytest

from robot.thermal import next_temperature


def test_one_day_by_hand():
    # settles at 26 + 15 * 0.6 * 1.0 = 35; from 30 it covers 0.7 of the 5 degrees
    assert next_temperature(30.0, 0.6, 1.0) == pytest.approx(33.5)


def test_at_its_settling_temperature_it_stays():
    assert next_temperature(35.0, 0.6, 1.0) == pytest.approx(35.0)


def test_a_day_without_work_cools_toward_ambient():
    # 40 + 0.7 * (26 - 40)
    assert next_temperature(40.0, 0.0, 1.0) == pytest.approx(30.2)


def test_a_slower_moving_joint_runs_cooler():
    # settles at 26 + 15 * 0.6 * 0.6 = 31.4
    assert next_temperature(31.4, 0.6, 0.6) == pytest.approx(31.4)
    assert next_temperature(31.4, 0.6, 0.6) < next_temperature(31.4, 0.6, 1.0)


def test_many_equal_days_reach_the_settling_temperature():
    temp = 26.0
    for _ in range(20):
        temp = next_temperature(temp, 1.2, 1.0)

    assert temp == pytest.approx(26 + 15 * 1.2)


def test_it_takes_one_value_per_joint():
    temp = next_temperature(np.array([30.0, 30.0]), 0.6, np.array([1.0, 0.6]))

    assert temp == pytest.approx([33.5, 30.0 + 0.7 * (31.4 - 30.0)])
