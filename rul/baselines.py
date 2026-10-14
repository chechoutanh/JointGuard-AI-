"""The three baselines that every results table carries.

Each has fit(train) -> model and predict(model, t_hours, x) -> Prediction. predict is given
the times and the features of a bearing's snapshots and nothing else: it cannot know when
the bearing fails.
"""

from dataclasses import dataclass

import numpy as np

import config


@dataclass
class Prediction:
    s: np.ndarray        # predicted share of life left at each snapshot
    low: np.ndarray      # the 90% interval
    high: np.ndarray


def weighted_quantile(values, weights, shares):
    """For each share, the smallest value at which the running weight reaches that share of the total."""
    values = np.asarray(values, dtype=float)
    order = np.argsort(values, kind="stable")
    running = np.cumsum(np.asarray(weights, dtype=float)[order])
    index = np.searchsorted(running / running[-1], shares, side="left")
    return values[order][np.minimum(index, len(values) - 1)]


def _pooled(train):
    """Targets, features and weights of all training snapshots. Each bearing weighs 1 in total,
    so one that ran for 2538 snapshots counts no more than one that ran for 42."""
    s = np.concatenate([u.s for u in train])
    x = np.concatenate([u.x for u in train])
    weights = np.concatenate([np.full(len(u.s), 1 / len(u.s)) for u in train])
    return s, x, weights


def fit_constant(train):
    """Always 0.5. Its interval is the range that holds 90% of the training targets."""
    s, _, weights = _pooled(train)
    return weighted_quantile(s, weights, config.INTERVAL_SHARES)


def predict_constant(model, t_hours, x):
    low, high = model
    n = len(t_hours)
    return Prediction(np.full(n, 0.5), np.full(n, low), np.full(n, high))


def fit_elapsed(train):
    """The clock alone: assume this bearing lives as long as the median training bearing."""
    lives = np.array([u.life_hours for u in train])
    short, long = weighted_quantile(lives, np.ones(len(lives)), config.INTERVAL_SHARES)
    return np.median(lives), short, long


def predict_elapsed(model, t_hours, x):
    median, short, long = model
    elapsed = t_hours - t_hours[0]

    def share_left(life):
        return np.clip(1 - elapsed / life, 0.0, 1.0)

    return Prediction(share_left(median), share_left(short), share_left(long))


def fit_rms(train, bins=None):
    """Vibration level alone. Training snapshots are sorted into groups of equal weight by relative
    rms; a group answers with the middle of its shares of life left, and the range holding 90%."""
    bins = bins or config.RMS_MODEL_BINS
    column = train[0].names.index("rms")
    s, x, weights = _pooled(train)
    rms = x[:, column]

    edges = np.unique(weighted_quantile(rms, weights, np.arange(1, bins) / bins))
    edges = edges[edges < rms.max()]           # so that no group is empty
    group = np.searchsorted(edges, rms, side="left")
    low, high = config.INTERVAL_SHARES
    table = np.array([weighted_quantile(s[group == g], weights[group == g], (low, 0.5, high))
                      for g in range(len(edges) + 1)])
    return column, edges, table


def predict_rms(model, t_hours, x):
    column, edges, table = model
    low, middle, high = table[np.searchsorted(edges, x[:, column], side="left")].T
    return Prediction(middle, low, high)


BASELINES = {
    "constant 0.5": (fit_constant, predict_constant),
    "elapsed time": (fit_elapsed, predict_elapsed),
    "rms only": (fit_rms, predict_rms),
}
