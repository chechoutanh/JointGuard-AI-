"""One made-up bearing through every metric, to check by hand.

    python results/2026-10-08_baselines/worked_example.py     (from the project root)

Snapshots at 0, 1, 2, 3, 4 hours; the bearing fails at 4 hours.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.getcwd())

from rul import metrics
from rul.data import share_of_life_left

t = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
life = 4.0
true = share_of_life_left(t, life)
pred = np.array([0.9, 0.8, 0.5, 0.1, 0.1])
low, high = pred - 0.12, pred + 0.12
cap = 100.0

hours_pred = metrics.remaining_hours(t, pred, cap)
hours_true = life - t

print(f"{'hour':>4s} {'true s':>7s} {'pred s':>7s} {'|error|':>8s} {'true h left':>12s} {'pred h left':>12s} "
      f"{'|error| h':>10s} {'% of left':>10s} {'interval':>14s} {'inside':>7s}")
for i in range(len(t)):
    error_h = abs(hours_pred[i] - hours_true[i])
    percent = f"{100 * error_h / hours_true[i]:9.1f}%" if hours_true[i] > 0 else "         -"
    inside = low[i] <= true[i] <= high[i]
    print(f"{t[i]:4.0f} {true[i]:7.2f} {pred[i]:7.2f} {abs(pred[i] - true[i]):8.2f} {hours_true[i]:12.2f} "
          f"{hours_pred[i]:12.3f} {error_h:10.3f} {percent} {f'{low[i]:.2f} to {high[i]:.2f}':>14s} {str(inside):>7s}")

hours_error, percent_error = metrics.remaining_time_error(t, life, pred, cap)
coverage, width = metrics.interval_coverage_and_width(true, low, high)
print(f"\nMAE                          {metrics.mae(true, pred):.4f}")
print(f"near-failure recall          {metrics.near_failure_recall(true, pred, 0.2):.2f}")
print(f"hours error (median)         {hours_error:.4f}")
print(f"% of the hours left (median) {percent_error:.1f}")
print(f"rank within the bearing      {metrics.rank_within(true, pred):.4f}")
print(f"interval coverage, width     {coverage:.2f}, {width:.2f}")
print(f"MAE of always saying 0.5     {metrics.mae(true, np.full(5, 0.5)):.4f}")
