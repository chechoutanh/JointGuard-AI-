"""Does a shorter time at each speed change what the sweep reads? An option if long runs are wanted.

    python results/2026-10-12_robot_dayloop/sweep_length.py     (from the project root, about 10 s)

Noise off, six joints, new and at wear 0.8. The settings are changed inside
this script only; robot/config.py keeps 0.5 s + 0.5 s.

Everything here is simulation with illustrative parameters.
"""

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.getcwd())

from robot import config
from robot.fit import fit_friction
from robot.sweep import run_health_check
from robot.world import connect, disconnect

config.NOISE_NM = 0.0
world = connect()
n = config.N_JOINTS


def coulomb(joint, wear):
    rows = run_health_check(world, joint, np.full(n, wear), np.full(n, config.TEMP_REF_C), np.random.default_rng(0))
    return fit_friction([r["v_measured"] for r in rows], [r["friction_torque"] for r in rows], config.RATED_RAD_S[joint])[0]


print(f"{'settle s':>8s} {'record s':>8s} {'s per day':>9s} {'largest change of Fc':>21s} {'largest change of the health index at wear 0.8':>47s}")
reference = None
for settle, record in ((0.5, 0.5), (0.2, 0.2), (0.1, 0.1), (0.05, 0.05)):
    config.SETTLE_S, config.RECORD_S = settle, record
    started = time.time()
    new = np.array([coulomb(j, 0.0) for j in range(n)])
    worn = np.array([coulomb(j, config.FAIL_W) for j in range(n)])
    day = (time.time() - started) / 2
    index = (worn / new - 1) / config.WEAR_GAIN_FC
    if reference is None:
        reference = (new, worn, index)
    change = np.abs(np.r_[new / reference[0], worn / reference[1]] - 1).max()
    print(f"{settle:8.2f} {record:8.2f} {day:9.2f} {change:21.1e} {np.abs(index - reference[2]).max():47.1e}")
disconnect(world)
