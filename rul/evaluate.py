"""Evaluation on whole bearings: the two splits, the score of each bearing, and the summary."""

import numpy as np

import config
from rul import metrics
from rul.baselines import BASELINES

# Always saying 0.5 is wrong by 0.25 on average when s runs evenly from 1 to 0.
GUESSING_MAE = 0.25


def leave_one_bearing_out(units):
    """One fold per bearing: train on all the others, test on it."""
    return [([u for u in units if u is not held], [held]) for held in units]


def leave_one_condition_out(units):
    """One fold per operating condition: train on the other conditions, test on all its bearings."""
    conditions = sorted({u.condition for u in units})
    return [([u for u in units if u.condition != c], [u for u in units if u.condition == c]) for c in conditions]


def score(unit, prediction, cap_hours):
    """Every metric for one bearing."""
    hours_error, percent_error = metrics.remaining_time_error(unit.t_hours, unit.life_hours, prediction.s, cap_hours)
    coverage, width = metrics.interval_coverage_and_width(unit.s, prediction.low, prediction.high)
    return {
        "unit_id": unit.unit_id, "condition": unit.condition, "snapshots": len(unit.s),
        "life_hours": unit.life_hours,
        "mae": metrics.mae(unit.s, prediction.s),
        "recall": metrics.near_failure_recall(unit.s, prediction.s, config.NEAR_FAILURE_SHARE),
        "hours_error": hours_error, "percent_error": percent_error,
        "rank": metrics.rank_within(unit.s, prediction.s),
        "coverage": coverage, "width": width,
    }


def evaluate(units, folds, predictors=BASELINES):
    """{predictor name: {"bearings": one score per test bearing, "triage": across-bearing score}}.

    Each bearing is predicted by a model fitted on its fold's training bearings only.
    """
    result = {}
    for name, (fit, predict) in predictors.items():
        rows, predictions = [], []
        for train, test in folds:
            model = fit(train)
            cap_hours = max(u.life_hours for u in train)     # no claim beyond the longest life seen
            for unit in test:
                prediction = predict(model, unit.t_hours, unit.x)
                rows.append(score(unit, prediction, cap_hours))
                predictions.append(prediction.s)
        result[name] = {"bearings": rows,
                        "triage": metrics.triage_concordance(predictions, config.TRIAGE_LIFE_SHARES)}
    return result


def summarise(result):
    """One line of the results table. Every bearing counts once, however many snapshots it has."""
    rows = result["bearings"]

    def column(key):
        return np.array([row[key] for row in rows])

    return {
        "bearings": len(rows),
        "mae": float(column("mae").mean()),
        "beat_guessing": int((column("mae") < GUESSING_MAE).sum()),
        "recall": float(column("recall").mean()),
        "hours_error": float(np.median(column("hours_error"))),
        "percent_error": float(np.median(column("percent_error"))),
        "rank": float(column("rank").mean()),
        "triage": result["triage"],
        "coverage": float(column("coverage").mean()),
        "width": float(column("width").mean()),
    }
