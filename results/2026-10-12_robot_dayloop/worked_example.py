"""Three days of one joint, to check the day loop's bookkeeping by hand.

    python results/2026-10-12_robot_dayloop/worked_example.py     (from the project root, 2 s)

Joint 3: wear rate 1.24, work speed 0.7. Scenario ramp_late, seed 0. The
files go to a temporary folder that is removed at the end.
"""

import os
import sys
import tempfile

import pandas as pd

sys.path.insert(0, os.getcwd())

from robot import config
from robot.simulate import simulate

JOINT = 3

with tempfile.TemporaryDirectory() as folder:
    simulate("ramp_late", 3, seed=0, out_dir=folder, joints=(JOINT,))
    schedule = pd.read_csv(os.path.join(folder, "schedule.csv"))
    actual = pd.read_csv(os.path.join(folder, "actual_duty.csv"))
    truth = pd.read_csv(os.path.join(folder, "ground_truth.csv"))
    sweeps = pd.read_parquet(os.path.join(folder, "sweeps.parquet"))

rate, speed = config.RATE[JOINT], config.WORK_SPEED[JOINT]
print("1. Planned duty = level 0.6 x day of the week x spell. Days 0 to 2 are Monday to Wednesday of a normal spell:")
print(f"   0.6 x 1.12 x 1.0 = {0.6 * 1.12 * 1.0:.4f}        schedule.csv: {schedule['duty_planned'].round(4).tolist()}")

print(f"\n2. Wear of joint {JOINT} grows by K_WEAR x rate x actual duty = (1/480) x {rate:.2f} x actual duty")
print(f"   {'day':>3s} {'planned':>8s} {'actual':>8s} {'added by hand':>14s} {'wear by hand':>13s} {'ground_truth.csv':>17s}")
wear = 0.0
for day in range(3):
    worked = actual["duty_actual"][day]
    added = rate * worked / 480
    wear += added
    print(f"   {day:3d} {schedule['duty_planned'][day]:8.4f} {worked:8.4f} {added:14.6f} {wear:13.6f} {truth['wear'][day]:17.6f}")

print(f"\n3. Temperature: settles at 26 + 15 x actual duty x {speed}; each day covers 0.7 of the way. Starts at 26.")
print(f"   {'day':>3s} {'settles at':>11s} {'by hand':>9s} {'sweeps.parquet':>15s}")
temp = 26.0
recorded = sweeps.groupby("day")["temperature_c"].first()
for day in range(3):
    settled = 26 + 15 * actual["duty_actual"][day] * speed
    temp = temp + 0.7 * (settled - temp)
    print(f"   {day:3d} {settled:11.4f} {temp:9.4f} {recorded[day]:15.4f}")

print("\n4. What the model may see: one row of sweeps.parquet (day 0, fastest speed)")
row = sweeps[sweeps["day"] == 0].iloc[-1]
for name in sweeps.columns:
    print(f"   {name:16s} {row[name]}")
print(f"   no wear column: {'wear' not in sweeps.columns}")
