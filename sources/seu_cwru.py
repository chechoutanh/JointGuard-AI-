"""SEU gearbox and CWRU bearing files. Each file is one long recording: one snapshot."""

import os
import re

import numpy as np
import pandas as pd
from scipy.io import loadmat

import config
from sources.recording import Recording

SEU_NAME = re.compile(r"^([A-Za-z]+)_(\d+_\d+)\.csv$")            # "Chipped_30_2.csv"
SEU_CHANNELS = ("motor_vibration", "planetary_x", "planetary_y", "planetary_z",
                "motor_torque", "parallel_x", "parallel_y", "parallel_z")

CWRU_NAME = re.compile(r"^(B|IR|OR|normal)[\d@]*_(\d)\.mat$")     # "OR021@6_3.mat"
CWRU_CLASSES = {"B": "ball", "IR": "inner", "OR": "outer", "normal": "normal"}


def load_seu(root=None):
    """One Recording per CSV in root/bearingset and root/gearset."""
    root = root or config.SEU_DIR
    recordings = []
    for subset in ("bearingset", "gearset"):
        folder = os.path.join(root, subset)
        if not os.path.isdir(folder):
            continue
        for name in sorted(os.listdir(folder)):
            match = SEU_NAME.match(name)
            if match:
                recordings.append(_seu_file(os.path.join(folder, name), f"{subset}/{name[:-4]}", *match.groups()))
    return recordings


def _seu_file(path, unit_id, class_name, condition):
    frequency_limit, sep, header_lines = _seu_header(path)

    def snapshot(i):
        # Every line ends with a separator, which pandas sees as an empty ninth column.
        data = pd.read_csv(path, sep=sep, header=None, skiprows=header_lines, usecols=range(8))
        return data.to_numpy(dtype=float)

    fault_class = class_name.lower()
    return Recording(
        source="seu", unit_id=unit_id, run_id=unit_id, condition=condition,
        fs=frequency_limit * config.SEU_FS_PER_FREQUENCY_LIMIT, t_hours=np.zeros(1), failure_hours=None,
        fault_class="normal" if fault_class == "health" else fault_class,
        channels=SEU_CHANNELS, snapshot=snapshot,
    )


def _seu_header(path):
    """Frequency limit in Hz, separator, and number of lines before the samples."""
    with open(path) as handle:
        for count, line in enumerate(handle, start=1):
            if count == 1:
                sep = "," if "," in line else "\t"   # one real file uses commas, the rest tabs
            cells = line.rstrip("\n").split(sep)
            if cells[:2] == ["Frequency", "Limit"]:
                frequency_limit = float(cells[2])
            if cells[0] == "Data":
                return frequency_limit, sep, count


def load_cwru(root=None):
    """One Recording per .mat file in root."""
    root = root or config.CWRU_DIR
    recordings = []
    for name in sorted(os.listdir(root)):
        match = CWRU_NAME.match(name)
        if not match:
            continue
        prefix, load_hp = match.groups()
        fault_class = CWRU_CLASSES[prefix]
        recordings.append(Recording(
            source="cwru", unit_id=name[:-4], run_id=name[:-4], condition=f"{load_hp}hp",
            fs=config.CWRU_FS_NORMAL if fault_class == "normal" else config.CWRU_FS_FAULT,
            t_hours=np.zeros(1), failure_hours=None, fault_class=fault_class,
            channels=("drive_end", "fan_end"), snapshot=_cwru_reader(os.path.join(root, name)),
        ))
    return recordings


def _cwru_reader(path):
    def snapshot(i):
        mat = loadmat(path)
        # A file can hold more than one record: the real normal_2.mat holds record 99 and
        # a copy of record 98, which is normal_1's data. The file's own record is the later one.
        number = max(int(key[1:4]) for key in mat if key.endswith("_DE_time"))
        return np.column_stack([mat[f"X{number:03d}_{end}_time"].ravel() for end in ("DE", "FE")]).astype(float)
    return snapshot
