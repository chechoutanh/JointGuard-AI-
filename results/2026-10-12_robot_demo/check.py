"""Milestone M5: does the live demo read back the wear it is given, on every joint? Run without the window.

    python results/2026-10-12_robot_demo/check.py     (from the project root, about 10 s)

The demo itself is: python -m tools.robot demo --gui [--joint 3] [--wear 0.5]

Everything here is simulation with illustrative parameters.
"""

import contextlib
import io
import os
import sys

sys.path.insert(0, os.getcwd())

from robot import config
from tools.robot import live_sweep

WEARS = (0.0, 0.2, 0.5, 0.8, 1.0)

print("health index printed by the demo, for the wear it was given (rows: joint)")
print(f"  {'joint':>5s} " + " ".join(f"{'wear ' + str(w):>9s}" for w in WEARS))
worst = 0.0
for joint in range(config.N_JOINTS):
    cells = []
    for wear in WEARS:
        with contextlib.redirect_stdout(io.StringIO()):
            index = live_sweep(joint, wear, seed=joint, gui=False)["health_index"]
        worst = max(worst, abs(index - wear))
        cells.append(f"{index:9.3f}")
    print(f"  {joint:5d} " + " ".join(cells))
print(f"largest difference between the index and the wear: {worst:.3f}")

print("\nwhat the command prints (joint 3, wear 0.5, seed 0), without the window:")
live_sweep(3, 0.5, seed=0, gui=False)
