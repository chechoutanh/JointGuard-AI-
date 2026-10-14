"""One joint of one run, to check by hand: its wear rate and its service day.

    python results/2026-10-12_robot_runs/worked_example.py     (from the project root)

Reads data/simulation/ramp_late/run_0 (seed 0). Joint 3, nominal wear rate 1.24.
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())

from robot import config
from robot.simulate import wear_rates

JOINT = 3
folder = os.path.join(config.SIMULATION_DIR, "ramp_late", "run_0")
work = pd.read_csv(os.path.join(folder, "actual_duty.csv"))["duty_actual"].to_numpy()
truth = pd.read_csv(os.path.join(folder, "ground_truth.csv"))
truth = truth[truth["joint"] == JOINT].sort_values("day")
wear = truth["wear"].to_numpy()

rate = wear_rates(0)[JOINT]
print(f"1. This run's wear rate of joint {JOINT}")
print(f"   nominal rate {config.RATE[JOINT]:.2f} x this run's factor {rate / config.RATE[JOINT]:.4f} = {rate:.4f}")

print("\n2. Wear on day 9 = rate x (work done on days 0 to 9) / 480")
print(f"   work done, day by day: {' + '.join(f'{x:.4f}' for x in work[:10])} = {work[:10].sum():.4f}")
print(f"   by hand: {rate:.4f} x {work[:10].sum():.4f} / 480 = {rate * work[:10].sum() / 480:.6f}        ground_truth.csv: {wear[9]:.6f}")

needed = config.FAIL_W * 480 / rate
total = np.cumsum(work)
day = int(np.argmax(total >= needed))
print(f"\n3. Service day = the first day the wear is at or past {config.FAIL_W}")
print(f"   work needed: {config.FAIL_W} x 480 / {rate:.4f} = {needed:.2f}")
print(f"   work done by the end of day {day - 1}: {total[day - 1]:.2f} (not yet); by the end of day {day}: {total[day]:.2f} (reached)")
print(f"   by hand: day {day}        ground_truth.csv: day {int(truth['service_day'].iloc[0])}")
print(f"   with the nominal rate {config.RATE[JOINT]:.2f} it would have been day {int(np.argmax(total >= config.FAIL_W * 480 / config.RATE[JOINT]))}")
