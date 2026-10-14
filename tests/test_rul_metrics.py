"""The RUL metrics, on one made-up bearing small enough to work out by hand.

The bearing: snapshots at 0, 1, 2, 3, 4 hours, failure at 4 hours.
True share of life left:  1.00  0.75  0.50  0.25  0.00
Predicted:                0.90  0.80  0.50  0.10  0.10
"""

import math

import numpy as np
import pytest

from rul import metrics
from rul.data import share_of_life_left

T = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
LIFE = 4.0
TRUE = np.array([1.0, 0.75, 0.5, 0.25, 0.0])
PRED = np.array([0.9, 0.8, 0.5, 0.1, 0.1])


def test_target_is_the_share_of_life_left():
    assert share_of_life_left(T, LIFE).tolist() == TRUE.tolist()


def test_mae_is_the_mean_absolute_error():
    # errors 0.10, 0.05, 0, 0.15, 0.10 -> sum 0.40 over 5
    assert metrics.mae(TRUE, PRED) == pytest.approx(0.08)


def test_near_failure_recall_is_the_share_of_the_last_fifth_predicted_low():
    true = np.array([0.9, 0.5, 0.19, 0.10, 0.05, 0.0])
    pred = np.array([0.9, 0.1, 0.25, 0.15, 0.30, 0.0])
    # last fifth of life: the four snapshots with true below 0.2; predicted below 0.2 in two of them.
    # The early false alarm (0.1 predicted at 0.5) does not count either way.
    assert metrics.near_failure_recall(true, pred, 0.2) == pytest.approx(0.5)


def test_a_perfect_prediction_has_full_near_failure_recall():
    true = np.array([1.0, 0.8, 0.6, 0.4, 0.2, 0.0])   # one snapshot sits exactly on the 0.2 line

    assert metrics.near_failure_recall(true, true, 0.2) == 1.0


def test_remaining_hours_follow_from_elapsed_time_and_share_left():
    # if 80% is left after 1 hour, the whole life is 5 hours, so 4 remain
    hours = metrics.remaining_hours(np.array([1.0, 2.0, 3.0]), np.array([0.8, 0.5, 0.1]), cap_hours=100.0)

    assert hours == pytest.approx([4.0, 2.0, 1 / 3])


def test_remaining_hours_are_capped():
    # 99 hours, a division by zero, and zero elapsed time with "everything left"
    hours = metrics.remaining_hours(np.array([1.0, 1.0, 0.0]), np.array([0.99, 1.0, 1.0]), cap_hours=10.0)

    assert hours.tolist() == [10.0, 10.0, 10.0]


def test_remaining_time_error_is_a_median_in_hours_and_in_percent():
    # predicted hours 0, 4, 2, 0.333, 0.444 against true 4, 3, 2, 1, 0
    # absolute errors 4, 1, 0, 0.667, 0.444 -> median 0.667
    # as % of the true remaining time (last snapshot left out, nothing remains): 100, 33.3, 0, 66.7 -> median 50
    hours, percent = metrics.remaining_time_error(T, LIFE, PRED, cap_hours=100.0)

    assert hours == pytest.approx(2 / 3)
    assert percent == pytest.approx(50.0)


def test_rank_within_a_bearing_is_the_spearman_correlation():
    # ranks of true: 5 4 3 2 1; ranks of predicted: 5 4 3 1.5 1.5 -> 9.5 / sqrt(10 x 9.5)
    assert metrics.rank_within(TRUE, PRED) == pytest.approx(9.5 / math.sqrt(95))


def test_a_constant_prediction_has_no_rank():
    assert metrics.rank_within(TRUE, np.full(5, 0.5)) == 0.0


def test_interval_coverage_and_width():
    low = np.array([0.7, 0.6, 0.6, 0.0, 0.1])
    high = np.array([0.9, 0.9, 0.8, 0.5, 0.3])
    # the truth 1, 0.75, 0.5, 0.25, 0 is inside in 2 of 5; widths 0.2, 0.3, 0.2, 0.5, 0.2
    coverage, width = metrics.interval_coverage_and_width(TRUE, low, high)

    assert coverage == pytest.approx(0.4)
    assert width == pytest.approx(0.28)


def test_triage_compares_snapshots_of_different_bearings_only():
    # Read at the start, middle and end of life. Both bearings are ordered perfectly inside
    # themselves, but every prediction for the second is 10 too high. Of the 6 pairs made of one
    # snapshot from each bearing at different shares of life, 3 are ordered correctly.
    predictions = [np.array([1.0, 0.5, 0.0]), np.array([11.0, 10.5, 10.0])]

    assert metrics.triage_concordance(predictions, life_shares=(0.0, 0.5, 1.0)) == pytest.approx(0.5)


def test_triage_is_one_when_every_cross_bearing_pair_is_ordered_right():
    predictions = [np.array([0.9, 0.2]), np.array([0.6, 0.4])]

    assert metrics.triage_concordance(predictions, life_shares=(0.0, 1.0)) == 1.0


def test_triage_of_a_constant_prediction_is_a_coin_flip():
    predictions = [np.full(3, 0.5), np.full(3, 0.5)]

    assert metrics.triage_concordance(predictions, life_shares=(0.0, 0.5, 1.0)) == 0.5


def test_triage_reads_a_long_and_a_short_bearing_at_the_same_shares_of_life():
    # at 0%, 50% and 100% of life the long bearing is read at snapshots 0, 50 and 100
    long = np.full(101, 99.0)
    long[[0, 50, 100]] = [1.0, 0.5, 0.0]          # right where it is read, nonsense elsewhere
    short = np.array([1.0, 0.5, 0.0])

    assert metrics.triage_concordance([long, short], life_shares=(0.0, 0.5, 1.0)) == 1.0
