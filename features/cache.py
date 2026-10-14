"""The cached raw features of one unit: one .npz file in data/processed/<source>/."""

import os
from dataclasses import dataclass

import numpy as np

import config
from features.snapshot import feature_names


@dataclass
class Features:
    source: str
    unit_id: str
    run_id: str
    condition: str
    fs: float
    t_hours: np.ndarray          # time of each snapshot since the start
    failure_hours: float | None
    channels: tuple[str, ...]
    names: list[str]             # name of each feature
    raw: np.ndarray              # (snapshots, channels, features), not yet relative
    missing: np.ndarray          # missing readings in each snapshot, before they were filled


def path(source, unit_id):
    return os.path.join(config.PROCESSED_DIR, source, unit_id + ".npz")


def save(path, rec, raw, missing, bands):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    np.savez(
        path, raw=raw, missing=missing, t_hours=rec.t_hours, bands=np.array(bands, dtype=float),
        names=np.array(feature_names(bands)), channels=np.array(rec.channels), fs=rec.fs,
        failure_hours=np.nan if rec.failure_hours is None else rec.failure_hours,
        source=rec.source, unit_id=rec.unit_id, run_id=rec.run_id, condition=rec.condition,
    )


def load(path, bands):
    """The cached features, refused if they were computed with other frequency bands."""
    with np.load(path) as stored:
        if stored["bands"].tolist() != np.array(bands, dtype=float).tolist():
            raise ValueError(f"{path} was cached with other frequency bands: "
                             "run python -m tools.features <source> --force")
        failure_hours = float(stored["failure_hours"])
        return Features(
            source=str(stored["source"]), unit_id=str(stored["unit_id"]), run_id=str(stored["run_id"]),
            condition=str(stored["condition"]), fs=float(stored["fs"]), t_hours=stored["t_hours"],
            failure_hours=None if np.isnan(failure_hours) else failure_hours,
            channels=tuple(stored["channels"].tolist()), names=stored["names"].tolist(),
            raw=stored["raw"], missing=stored["missing"],
        )
