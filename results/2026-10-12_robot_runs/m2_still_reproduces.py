"""With the settings of milestone M2, does today's code still write M2's files, byte for byte?

    python results/2026-10-12_robot_runs/m2_still_reproduces.py     (from the project root, about 2 minutes)

M3 changed two settings: every run now draws its own wear rates, and each
speed is held for 0.1 s + 0.1 s instead of 0.5 s + 0.5 s. This script puts
both back (inside the script only), runs the M2 check command's 60 days, and
compares with the SHA-256 values recorded in
results/2026-10-12_robot_dayloop/output.txt.
"""

import hashlib
import os
import sys
import tempfile

sys.path.insert(0, os.getcwd())

from robot import config
from robot.simulate import simulate

config.RATE_SPREAD, config.SETTLE_S, config.RECORD_S = 0.0, 0.5, 0.5
RECORDED = {"sweeps.parquet": "10992b526792cf6e", "schedule.csv": "293d24c8a740e975", "actual_duty.csv": "56b79c62310fea2d",
            "ground_truth.csv": "18880af3aac63a78", "events.csv": "e6f18ebf2401b93c"}

with tempfile.TemporaryDirectory() as folder:
    simulate("ramp_late", 60, 0, folder)
    for name, old in RECORDED.items():
        with open(os.path.join(folder, name), "rb") as f:
            new = hashlib.sha256(f.read()).hexdigest()[:16]
        print(f"{name:18s} M2: {old}  now: {new}  same: {old == new}")
