"""The summary that `python -m tools.sources` prints, on hand-made recordings."""

import numpy as np

from sources.recording import Recording
from tools import sources as tool


def recording(unit_id, snapshots, fs=10.0):
    return Recording(
        source="xjtu", unit_id=unit_id, run_id=unit_id, condition="35Hz_12kN", fs=fs,
        t_hours=np.arange(len(snapshots)) * 0.5, failure_hours=(len(snapshots) - 1) * 0.5,
        fault_class=None, channels=("horizontal", "vertical"), snapshot=lambda i: snapshots[i],
    )


def test_describe_reports_size_duration_and_missing_readings():
    first, last = np.zeros((20, 2)), np.ones((20, 2))
    last[3, 1] = np.nan

    row = tool.describe(recording("Bearing1_1", [first, np.ones((20, 2)), last]))

    assert (row["unit_id"], row["snapshots"], row["hours"]) == ("Bearing1_1", 3, 1.0)
    assert (row["samples"], row["channels"], row["seconds"]) == (20, 2, 2.0)
    assert row["missing"] == 1


def test_duplicates_lists_recordings_whose_signals_are_identical():
    same = np.arange(40.0).reshape(20, 2)
    rows = [
        tool.describe(recording("a", [same])),
        tool.describe(recording("b", [same + 1.0])),
        tool.describe(recording("c", [same.copy()])),
    ]

    assert tool.duplicates(rows) == [("a", "c")]
