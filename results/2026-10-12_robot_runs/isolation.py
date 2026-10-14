"""Isolation, in the saved dataset: when only joint 3 wears, does only joint 3's friction rise?

    python results/2026-10-12_robot_runs/isolation.py     (from the project root, about 15 s)

A special run made for this check only: the wear rate of every joint but
joint 3 is set to 0, and wear is made 20 times faster, so that joint 3 goes
from new to past its service threshold in 30 days. The settings are changed
inside this script; the files go to a temporary folder.

Everything here is simulation with illustrative parameters.
"""

import os
import sys
import tempfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())

from robot import config
from robot.fit import fit_friction
from robot.simulate import simulate

DAYS = 30
only_joint_3 = np.zeros(config.N_JOINTS)
only_joint_3[3] = config.RATE[3]
config.RATE = only_joint_3
config.K_WEAR = 20 / 480

with tempfile.TemporaryDirectory() as folder:
    simulate("ramp_late", DAYS, seed=0, out_dir=folder)
    sweeps = pd.read_parquet(os.path.join(folder, "sweeps.parquet"))
    truth = pd.read_csv(os.path.join(folder, "ground_truth.csv"))


def coulomb(joint, days):
    """Mean fitted Coulomb friction over some days, with the temperature effect taken out."""
    values = []
    for day in days:
        rows = sweeps[(sweeps["joint"] == joint) & (sweeps["day"] == day)]
        fc, _ = fit_friction(rows["v_measured"], rows["friction_torque"], config.RATED_RAD_S[joint])
        values.append(fc / (1 - config.TEMP_COEF * (rows["temperature_c"].iloc[0] - config.TEMP_REF_C)))
    return np.mean(values)


print(f"{'joint':>5s} {'true wear, day 0':>16s} {'true wear, last day':>19s} {'Fc first 3 days':>15s} {'Fc last 3 days':>14s} {'change':>8s}")
for joint in range(config.N_JOINTS):
    wear = truth[truth["joint"] == joint].sort_values("day")["wear"].to_numpy()
    first, last = coulomb(joint, range(3)), coulomb(joint, range(DAYS - 3, DAYS))
    print(f"{joint:5d} {wear[0]:16.3f} {wear[-1]:19.3f} {first:15.4f} {last:14.4f} {last / first - 1:+8.2%}")
