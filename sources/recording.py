"""The one record type every dataset adapter returns."""

from dataclasses import dataclass, field
from typing import Callable

import numpy as np


@dataclass
class Recording:
    source: str                  # "xjtu", "ims", "kaist", "seu", "cwru"
    unit_id: str                 # one bearing, or one gearbox recording
    run_id: str                  # independent run (IMS test-1 bearings 3 and 4 share one)
    condition: str               # e.g. "35Hz_12kN"
    fs: float                    # Hz; from the file where it is stored, else from config.py
    t_hours: np.ndarray          # time of each snapshot since the start
    failure_hours: float | None  # run-to-failure sources only
    fault_class: str | None      # SEU / CWRU only
    channels: tuple[str, ...]    # name of each column of a snapshot
    # snapshot(i) reads snapshot i from disk: an array of shape (samples, channels).
    # Nothing is kept in memory between calls.
    snapshot: Callable[[int], np.ndarray] = field(repr=False, compare=False)

    def __len__(self):
        return len(self.t_hours)
