"""KAIST ball bearing: one CSV per hour, named by its time. One bearing, one run."""

import os
import re
from datetime import datetime

import numpy as np
import pandas as pd

import config
from sources.recording import Recording

NAME = re.compile(r"^LogFile_(\d{4}-\d\d-\d\d-\d\d-\d\d-\d\d)\.csv$")
NAME_FORMAT = "%Y-%m-%d-%H-%M-%S"


def load(root=None):
    """The single KAIST run as a list of one Recording."""
    root = root or config.KAIST_DIR
    stamped = sorted((datetime.strptime(m.group(1), NAME_FORMAT), m.group(0))
                     for m in map(NAME.match, os.listdir(root)) if m)
    t_hours = np.array([(t - stamped[0][0]).total_seconds() / 3600.0 for t, _ in stamped])
    fs = config.KAIST_FS
    rows = int(round(config.KAIST_SNAPSHOT_SECONDS * fs))

    def snapshot(i):
        # Columns 0 and 1 are vibration x and y; 2 and 3 are temperatures.
        # Missing readings are stored as NaN and are returned as NaN.
        data = pd.read_csv(os.path.join(root, stamped[i][1]), header=None, usecols=[0, 1], nrows=rows)
        return data.to_numpy(dtype=float)

    return [Recording(
        source="kaist", unit_id="bearing1", run_id="kaist", condition="1775rpm", fs=fs,
        t_hours=t_hours, failure_hours=float(t_hours[-1]), fault_class=None,
        channels=("x", "y"), snapshot=snapshot,
    )]
