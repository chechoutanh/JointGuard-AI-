"""Features relative to a unit's own healthy start. Arrays are (snapshots, channels, features)."""

import numpy as np
import pytest

from features.relative import relative, worst_channel


def one_feature(values):
    return np.array(values, dtype=float).reshape(-1, 1, 1)


def test_relative_is_the_ratio_to_the_median_of_the_first_snapshots():
    # reference after 1, 2, 3 snapshots: median(2)=2, median(2,3)=2.5, median(2,3,2)=2, then fixed at 2
    got = relative(one_feature([2, 3, 2, 4, 8, 16]), n_healthy=3)

    assert got.ravel() == pytest.approx([1.0, 1.2, 1.0, 2.0, 4.0, 8.0])


def test_the_reference_stops_learning_after_the_healthy_snapshots():
    # the 100 comes after the first 3, so the last value is still 4 / 2
    got = relative(one_feature([2, 2, 2, 100, 4]), n_healthy=3)

    assert got.ravel() == pytest.approx([1.0, 1.0, 1.0, 50.0, 2.0])


def test_the_past_does_not_change_when_the_future_does():
    rng = np.random.default_rng(0)
    raw = rng.uniform(1.0, 2.0, size=(30, 2, 4))
    other_future = raw.copy()
    other_future[12:] *= 7.0

    assert np.array_equal(relative(raw, 5)[:12], relative(other_future, 5)[:12])


def test_streaming_equals_batch():
    # streaming: at each moment, compute with only the snapshots that exist so far
    rng = np.random.default_rng(1)
    raw = rng.uniform(1.0, 2.0, size=(25, 2, 3))

    batch = relative(raw, 5)
    streamed = np.stack([relative(raw[:k + 1], 5)[-1] for k in range(len(raw))])

    assert np.array_equal(streamed, batch)


def test_each_channel_is_compared_with_its_own_reference():
    # channel 0 rests at 1, channel 1 rests at 10; both double at the end
    raw = np.array([[[1.0], [10.0]], [[1.0], [10.0]], [[2.0], [20.0]]])

    got = relative(raw, n_healthy=2)

    assert got[-1].ravel() == pytest.approx([2.0, 2.0])


def test_a_run_shorter_than_the_healthy_count_still_gets_values():
    got = relative(one_feature([4, 8]), n_healthy=10)

    assert got.ravel() == pytest.approx([1.0, 8 / 6])


def test_channels_are_combined_by_the_one_that_changed_most():
    # snapshot 0: channel 0 is [1, 3], channel 1 is [2, 1] -> [2, 3]
    rel = np.array([[[1.0, 3.0], [2.0, 1.0]], [[5.0, 0.5], [4.0, 0.9]]])

    assert worst_channel(rel).tolist() == [[2.0, 3.0], [5.0, 0.9]]
