"""The production schedule: the duty planned for each day, and the duty that actually happened.

Planned duty = level x day of the week x spell.
  level   0.6, or 1.2 from the scenario's ramp day on
  week    Monday to Friday 1.12, Saturday 0.90, Sunday 0.50   (averages 1)
  spell   28-day blocks: 1.0, 1.3, 0.8, 1.1, 0.7, 1.1          (averages 1)
Day 0 is a Monday.
"""

import numpy as np
import pytest

from robot import config
from robot.schedule import actual_duty, planned_duty


def test_planned_duty_by_hand():
    assert planned_duty("ramp_late", 0) == pytest.approx(0.6 * 1.12 * 1.0)        # Monday, first spell
    assert planned_duty("ramp_late", 5) == pytest.approx(0.6 * 0.90 * 1.0)        # Saturday
    assert planned_duty("ramp_late", 6) == pytest.approx(0.6 * 0.50 * 1.0)        # Sunday
    assert planned_duty("ramp_late", 28) == pytest.approx(0.6 * 1.12 * 1.3)       # Monday, second spell (busy)
    assert planned_duty("ramp_late", 118) == pytest.approx(0.6 * 0.50 * 0.7)      # day 118 = 4 * 28 + 6: Sunday, quiet spell


def test_the_plan_is_the_same_every_time_it_is_asked():
    assert [planned_duty("ramp_early", d) for d in range(50)] == [planned_duty("ramp_early", d) for d in range(50)]


def test_base_duty_averages_to_its_level_over_a_full_cycle():
    cycle = 28 * len(config.SPELL_PATTERN)                       # 168 days: six spells of four whole weeks
    duty = [planned_duty("ramp_late", d) for d in range(cycle)]

    assert np.mean(duty) == pytest.approx(config.BASE_DUTY)


def test_duty_varies_from_day_to_day():
    # if duty were constant, "wear per unit of work" could not be told from "wear per day"
    duty = [planned_duty("ramp_late", d) for d in range(168)]

    assert np.std(duty) > 0.1
    assert min(duty) < 0.25 and max(duty) > 0.85


def test_the_ramp_doubles_the_level_from_the_ramp_day_on():
    ramp = config.RAMP_DAY["ramp_early"]
    assert ramp < config.RAMP_DAY["ramp_late"]

    for day in (0, 50, ramp - 1):
        assert planned_duty("ramp_early", day) == planned_duty("ramp_late", day)
    for day in (ramp, ramp + 1, ramp + 100):
        assert planned_duty("ramp_early", day) == pytest.approx(2.0 * planned_duty("ramp_late", day))
    late = config.RAMP_DAY["ramp_late"]
    assert planned_duty("ramp_late", late) == pytest.approx(2.0 * planned_duty("ramp_late", late - 168))


def test_the_ramp_days_sit_before_and_after_every_joints_service_day_at_base_duty():
    # days to reach FAIL_W at the base duty, for the fastest and the slowest wearing joint
    days = config.FAIL_W / (config.K_WEAR * config.BASE_DUTY * config.RATE)

    assert config.RAMP_DAY["ramp_early"] < days.min()
    assert config.RAMP_DAY["ramp_late"] > days.max()


def test_an_unknown_scenario_is_an_error():
    with pytest.raises(ValueError, match="ramp_sideways"):
        planned_duty("ramp_sideways", 0)


def test_actual_duty_is_the_plan_times_noise_from_the_generator_passed_in():
    first = actual_duty("ramp_late", 3, np.random.default_rng(7))
    again = actual_duty("ramp_late", 3, np.random.default_rng(7))
    other = actual_duty("ramp_late", 3, np.random.default_rng(8))

    assert first == again
    assert first != other
    assert first > 0 and first != planned_duty("ramp_late", 3)


def test_the_noise_is_fair_and_of_the_stated_size():
    rng = np.random.default_rng(0)
    ratio = np.array([actual_duty("ramp_late", 0, rng) for _ in range(20000)]) / planned_duty("ramp_late", 0)

    assert ratio.mean() == pytest.approx(1.0, abs=0.01)          # on average the plan is right
    assert np.log(ratio).std() == pytest.approx(config.DUTY_NOISE_SIGMA, abs=0.01)
    assert (ratio > 0).all()
