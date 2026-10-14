"""IMS (NASA) bearings: one text file per snapshot, named by its time. Failed bearings only."""

import os
from datetime import datetime

import numpy as np
import pandas as pd

import config
from sources.recording import Recording

# test: (folder inside the archive, {failed bearing: its columns, counted from 0}).
# From the IMS readme. Test 1 has two sensors per bearing, tests 2 and 3 have one.
# The third archive unpacks to a folder called 4th_test. Its readme says the test
# ended after 4,448 files; the archive holds 6,324 and all are used (docs/LIMITS.md).
TESTS = {
    "test1": ("1st_test", {"b3": (4, 5), "b4": (6, 7)}),
    "test2": ("2nd_test", {"b1": (0,)}),
    "test3": (os.path.join("4th_test", "txt"), {"b3": (2,)}),
}
NAME_FORMAT = "%Y.%m.%d.%H.%M.%S"


def load(root=None):
    """One Recording per failed bearing, for every test that is unpacked under root."""
    root = root or config.IMS_DIR
    recordings = []
    for test, (folder, bearings) in TESTS.items():
        path = os.path.join(root, folder)
        if not os.path.isdir(path):
            continue
        names, t_hours = _snapshot_times(path)
        for bearing, columns in bearings.items():
            recordings.append(Recording(
                source="ims", unit_id=f"{test}_{bearing}", run_id=test, condition="2000rpm_6000lb",
                fs=config.IMS_FS, t_hours=t_hours, failure_hours=float(t_hours[-1]), fault_class=None,
                channels=("x", "y")[:len(columns)], snapshot=_reader(path, names, columns),
            ))
    return recordings


def _snapshot_times(path):
    """File names in time order, and the hours each one counts since the first."""
    stamped = []
    for name in os.listdir(path):
        try:
            stamped.append((datetime.strptime(name, NAME_FORMAT), name))
        except ValueError:
            continue
    stamped.sort()
    steps = np.diff([(t - stamped[0][0]).total_seconds() for t, _ in stamped])
    if config.IMS_MAX_STEP_MINUTES is not None:
        steps = np.minimum(steps, config.IMS_MAX_STEP_MINUTES * 60.0)
    t_hours = np.concatenate([[0.0], np.cumsum(steps)]) / 3600.0
    return [name for _, name in stamped], t_hours


def _reader(path, names, columns):
    def snapshot(i):
        data = pd.read_csv(os.path.join(path, names[i]), sep="\t", header=None, usecols=list(columns))
        return data.to_numpy(dtype=float)
    return snapshot
