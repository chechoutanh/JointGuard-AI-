"""The three baselines, on made-up bearings small enough to work out by hand."""

import numpy as np
import pytest

from features.relative import relative, worst_channel
from rul import baselines
from rul.data import Unit, share_of_life_left


def unit(unit_id, t_hours, rms, condition="a"):
    """A bearing that fails at its last snapshot, with relative rms as its only feature."""
    t = np.array(t_hours, dtype=float)
    return Unit(unit_id=unit_id, condition=condition, t_hours=t, life_hours=float(t[-1]),
                s=share_of_life_left(t, t[-1]), x=np.array(rms, dtype=float).reshape(-1, 1), names=["rms"])


def test_weighted_quantile_is_the_smallest_value_that_reaches_the_share():
    values = np.array([30.0, 10.0, 40.0, 20.0])

    # equal weights: 10 holds 25%, up to 20 holds 50%, up to 30 holds 75%
    assert baselines.weighted_quantile(values, np.ones(4), [0.5, 0.51, 0.05]).tolist() == [20.0, 30.0, 10.0]
    # weights 1, 3, 1, 1: the value 10 alone already holds half
    assert baselines.weighted_quantile(values, np.array([1.0, 3.0, 1.0, 1.0]), [0.5]).tolist() == [10.0]


def test_constant_baseline_says_half_with_the_training_range_as_its_interval():
    train = [unit("A", [0, 1, 2, 3, 4], [1, 1, 1, 1, 1]), unit("B", [0, 1, 2], [1, 1, 1])]
    # training shares of life: A has 1, .75, .5, .25, 0 and B has 1, .5, 0. The value 0 already holds
    # more than 5% of the weight, and 95% is only reached at 1.
    got = baselines.predict_constant(baselines.fit_constant(train), np.array([0.0, 5.0, 9.0]), np.ones((3, 1)))

    assert got.s.tolist() == [0.5, 0.5, 0.5]
    assert got.low.tolist() == [0.0, 0.0, 0.0]
    assert got.high.tolist() == [1.0, 1.0, 1.0]


def test_elapsed_time_prior_uses_the_median_training_life():
    train = [unit("A", [0, 2], [1, 1]), unit("B", [0, 4], [1, 1]), unit("C", [0, 10], [1, 1])]
    # median life 4 h; shortest 2 h and longest 10 h bound the interval
    got = baselines.predict_elapsed(baselines.fit_elapsed(train), np.array([0.0, 1.0, 2.0, 6.0]), np.ones((4, 1)))

    assert got.s == pytest.approx([1.0, 0.75, 0.5, 0.0])
    assert got.low == pytest.approx([1.0, 0.5, 0.0, 0.0])
    assert got.high == pytest.approx([1.0, 0.9, 0.8, 0.4])


def test_rms_model_says_the_middle_share_of_life_of_training_snapshots_that_shook_alike():
    train = [unit("A", [0, 1, 2, 3], [1.0, 1.1, 5.0, 6.0])]       # shares of life 1, 2/3, 1/3, 0
    # two groups of equal weight: rms up to 1.1 (shares 1 and 2/3) and above it (shares 1/3 and 0)
    model = baselines.fit_rms(train, bins=2)
    got = baselines.predict_rms(model, np.zeros(4), np.array([[1.0], [1.1], [1.2], [100.0]]))

    assert got.s == pytest.approx([2 / 3, 2 / 3, 0.0, 0.0])
    assert got.low == pytest.approx([2 / 3, 2 / 3, 0.0, 0.0])
    assert got.high == pytest.approx([1.0, 1.0, 1 / 3, 1 / 3])


def test_every_training_bearing_counts_the_same_however_many_snapshots_it_has():
    long = unit("long", range(8), [1.0] * 8)            # 8 snapshots, never shakes harder
    short = unit("short", [0, 1], [1.0, 9.0])           # 2 snapshots, shakes hard at the end
    model = baselines.fit_rms([long, short], bins=2)
    got = baselines.predict_rms(model, np.zeros(2), np.array([[1.0], [9.0]]))

    # at rms 1: the long bearing's shares 0, 1/7 ... 1 weigh 1/8 each, the short one's share 1 weighs 1/2.
    # Half of that weight (0.75 of 1.5) is reached at 5/7. Counting snapshots instead would give 4/7.
    assert got.s == pytest.approx([5 / 7, 0.0])


def test_streaming_predictions_equal_batch_predictions():
    # Streaming: at each snapshot, redo everything from the raw features that exist so far.
    rng = np.random.default_rng(3)
    train = [unit(f"T{i}", np.arange(n) * 0.5, np.sort(rng.uniform(1.0, 8.0, n)))
             for i, n in enumerate([12, 20, 35])]
    raw = np.sort(rng.uniform(1.0, 3.0, size=(25, 2, 1)), axis=0) * rng.uniform(0.9, 1.1, size=(25, 2, 1))
    t = np.arange(25) * 0.5

    def features(upto):
        return worst_channel(relative(raw[:upto], 5))

    for fit, predict in baselines.BASELINES.values():
        model = fit(train)
        batch = predict(model, t, features(25))
        for k in range(1, 26):
            now = predict(model, t[:k], features(k))
            assert (now.s[-1], now.low[-1], now.high[-1]) == (batch.s[k - 1], batch.low[k - 1], batch.high[k - 1])
