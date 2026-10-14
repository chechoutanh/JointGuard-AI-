"""The bearings as the RUL code sees them: the target and the relative features."""

import os
from dataclasses import dataclass

import numpy as np

import config
from features import cache
from features.relative import relative, worst_channel


@dataclass
class Unit:
    unit_id: str
    condition: str
    t_hours: np.ndarray     # time of each snapshot since the start
    life_hours: float       # from the first snapshot to failure
    s: np.ndarray           # the target: share of life left at each snapshot, 1 new, 0 failed
    x: np.ndarray           # (snapshots, features): relative to the unit's own healthy start
    names: list[str]        # name of each feature


def share_of_life_left(t_hours, failure_hours):
    """s = (T_fail - t) / (T_fail - t0)."""
    t = np.asarray(t_hours, dtype=float)
    return (failure_hours - t) / (failure_hours - t[0])


def load_units(source):
    """Every cached unit of a source, with features relative to its own healthy start."""
    folder = os.path.join(config.PROCESSED_DIR, source)
    units = []
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".npz"):
            continue
        feats = cache.load(os.path.join(folder, name), config.BANDS_HZ[source])
        units.append(Unit(
            unit_id=feats.unit_id, condition=feats.condition, t_hours=feats.t_hours,
            life_hours=feats.failure_hours - feats.t_hours[0],
            s=share_of_life_left(feats.t_hours, feats.failure_hours),
            x=worst_channel(relative(feats.raw, config.HEALTHY_SNAPSHOTS)), names=feats.names,
        ))
    return units
