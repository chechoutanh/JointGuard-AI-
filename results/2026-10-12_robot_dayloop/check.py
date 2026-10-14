"""Milestone M2 of the robot simulation: the day loop and its files. Is the brief's "done when" met?

    python results/2026-10-12_robot_dayloop/check.py     (from the project root, about 4 minutes)

Runs the real command, python -m tools.robot demo --days 60 --seed 0, twice,
and compares the files byte for byte. It overwrites data/simulation/ramp_late/.

Everything here is simulation with illustrative parameters.
"""

import hashlib
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())

from robot import config
from robot.guard import assert_no_leakage
from robot.sweep import run_health_check
from robot.world import connect, disconnect

FILES = ["sweeps.parquet", "schedule.csv", "actual_duty.csv", "ground_truth.csv", "events.csv"]
FOLDER = os.path.join(config.SIMULATION_DIR, "ramp_late")


def demo(seed):
    """Run the command as a user would, and return the SHA-256 and size of each file it wrote."""
    subprocess.run([sys.executable, "-m", "tools.robot", "demo", "--days", "60", "--seed", str(seed)],
                   check=True, capture_output=True)
    out = {}
    for name in FILES:
        with open(os.path.join(FOLDER, name), "rb") as f:
            data = f.read()
        out[name] = (hashlib.sha256(data).hexdigest(), len(data))
    return out


def main():
    print("A. Time of one day (6 joints, 18 speeds each)")
    world = connect()
    rng = np.random.default_rng(0)
    n = config.N_JOINTS
    started = time.time()
    for joint in range(n):
        run_health_check(world, joint, np.zeros(n), np.full(n, config.TEMP_REF_C), rng)
    day = time.time() - started
    disconnect(world)
    print(f"  {day:.2f} s per day")
    for label, days in (("the demo, 60 days", 60), ("one run, 400 days", 400), ("5 runs x 400 days", 2000),
                        ("2 scenarios x 5 runs x 400 days", 4000)):
        print(f"  {label:34s} {days * day / 60:6.1f} minutes")

    print("\nB. python -m tools.robot demo --days 60 --seed 0, run twice, then once with seed 1")
    first, second, other = demo(0), demo(0), demo(1)
    demo(0)                                                       # leave the seed-0 files on disk
    print(f"  {'file':18s} {'bytes':>9s} {'SHA-256 (first 16)':>19s} {'same on 2nd run':>16s} {'same with seed 1':>17s}")
    for name in FILES:
        print(f"  {name:18s} {first[name][1]:9d} {first[name][0][:16]:>19s} {str(first[name] == second[name]):>16s} "
              f"{str(first[name] == other[name]):>17s}")
    print(f"  all five files byte-identical on the second run: {first == second}")

    print("\nC. The leakage guard on the sweeps.parquet just written")
    sweeps = pd.read_parquet(os.path.join(FOLDER, "sweeps.parquet"))
    print(f"  {len(sweeps)} rows, columns: {', '.join(sweeps.columns)}")
    assert_no_leakage(sweeps.columns)
    print("  guard on the file as written: passed")
    try:
        assert_no_leakage(list(sweeps.columns) + ["wear"])
        print("  guard with a wear column added: PASSED, so the guard is broken")
    except AssertionError as error:
        print(f"  guard with a wear column added: refused ({error})")


if __name__ == "__main__":
    main()
