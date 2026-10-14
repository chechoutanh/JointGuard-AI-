"""XJTU-SY bearings: <condition>/<bearing>/<n>.csv, one snapshot per file, one per minute."""

import os
import re

import numpy as np
import pandas as pd

import config
from sources.recording import Recording

CONDITION = re.compile(r"^([\d.]+Hz)(\d+kN)$")   # "37.5Hz11kN"
SNAPSHOT = re.compile(r"^(\d+)\.csv$")


def load(root=None):
    """One Recording per bearing found under root."""
    root = root or config.XJTU_DIR
    recordings = []
    for folder in sorted(os.listdir(root)):
        match = CONDITION.match(folder)
        if not match:
            continue
        condition = "_".join(match.groups())
        for bearing in sorted(os.listdir(os.path.join(root, folder))):
            path = os.path.join(root, folder, bearing)
            if os.path.isdir(path):
                recordings.append(_bearing(path, bearing, condition))
    return recordings


def _bearing(path, unit_id, condition):
    # Sorted as numbers: by name, "10.csv" would come before "2.csv".
    numbers = sorted(int(m.group(1)) for m in map(SNAPSHOT.match, os.listdir(path)) if m)
    t_hours = (np.array(numbers) - numbers[0]) * config.XJTU_STEP_MINUTES / 60.0

    def snapshot(i):
        return pd.read_csv(os.path.join(path, f"{numbers[i]}.csv")).to_numpy(dtype=float)

    return Recording(
        source="xjtu", unit_id=unit_id, run_id=unit_id, condition=condition, fs=config.XJTU_FS,
        t_hours=t_hours, failure_hours=float(t_hours[-1]), fault_class=None,
        channels=("horizontal", "vertical"), snapshot=snapshot,
    )
