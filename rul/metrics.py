"""The RUL metrics. s is the share of life left: 1 new, 0 failed. All arrays are one bearing's snapshots."""

import numpy as np
from scipy.stats import spearmanr


def mae(s_true, s_pred):
    return float(np.mean(np.abs(s_pred - s_true)))


def near_failure_recall(s_true, s_pred, share):
    """Of the snapshots in the last `share` of life, the part predicted to be in it."""
    near = s_true < share
    return float(np.mean(s_pred[near] < share))


def remaining_hours(elapsed_hours, s_pred, cap_hours):
    """Hours left, from the share left: if s of the life is left after t hours, t s / (1 - s) remain.

    Never more than cap_hours, which also stands in when s is 1 and the formula has no answer.
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        hours = elapsed_hours * s_pred / (1 - s_pred)
    return np.where(np.isfinite(hours), np.minimum(hours, cap_hours), cap_hours)


def remaining_time_error(t_hours, life_hours, s_pred, cap_hours):
    """Median absolute error of the hours left, in hours and as a % of the true hours left."""
    elapsed = t_hours - t_hours[0]
    true = life_hours - elapsed
    error = np.abs(remaining_hours(elapsed, s_pred, cap_hours) - true)
    left = true > 0                  # at the failure itself nothing is left to take a % of
    return float(np.median(error)), float(np.median(100 * error[left] / true[left]))


def rank_within(s_true, s_pred):
    """Spearman correlation inside one bearing. 0 when the prediction never moves."""
    if np.ptp(s_pred) == 0:
        return 0.0
    return float(spearmanr(s_true, s_pred).statistic)


def interval_coverage_and_width(s_true, low, high):
    """Share of snapshots whose truth lies inside the interval, and the mean width of the interval."""
    return float(np.mean((low <= s_true) & (s_true <= high))), float(np.mean(high - low))


def triage_concordance(predictions, life_shares):
    """Given two snapshots of different bearings, how often is the one nearer failure predicted lower?

    predictions holds one array of predicted s per bearing. Each bearing is read at the same
    shares of its life, and every pair of readings from two different bearings at two different
    shares is checked. 1 is always right, 0.5 a coin flip; an equal prediction counts as half.
    """
    shares = np.asarray(life_shares, dtype=float)
    pred, share, owner = [], [], []
    for number, s_pred in enumerate(predictions):
        pred.append(s_pred[np.round(shares * (len(s_pred) - 1)).astype(int)])
        share.append(shares)
        owner.append(np.full(len(shares), number))
    pred, share, owner = np.concatenate(pred), np.concatenate(share), np.concatenate(owner)

    a, b = np.triu_indices(len(pred), k=1)
    use = (owner[a] != owner[b]) & (share[a] != share[b])
    # later in life means less left: right when the later snapshot has the lower prediction
    agree = np.sign(pred[a] - pred[b]) * np.sign(share[b] - share[a])       # 1 right, -1 wrong, 0 equal
    return float(np.mean((agree[use] + 1) / 2))
