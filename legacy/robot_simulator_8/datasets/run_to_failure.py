"""
Shared logic for run-to-failure bearing datasets (XJTU-SY, PHM 2012).

Each run is a sequence of short vibration snapshots. Time comes from the file
number and the snapshot interval, so a partially downloaded run still has
correct timing. Labels:

    life_fraction = t / t_failure       (0 at the start, 1 at the last snapshot)
    RUL_fraction  = 1 - life_fraction
"""

import contextlib

import numpy as np

import config
from datasets.base_adapter import DatasetAdapter, file_number
from datasets.harmonize import harmonize, split_windows
from datasets.signal_features import vibration_feature_names, vibration_features


@contextlib.contextmanager
def feature_settings(window_samples=0, sample_rate_hz=0.0):
    """Temporarily set the common windowing / sample rate (the two settings that change features)."""
    before = config.RUL_COMMON_WINDOW_SAMPLES, config.RUL_COMMON_SAMPLE_RATE_HZ
    config.RUL_COMMON_WINDOW_SAMPLES, config.RUL_COMMON_SAMPLE_RATE_HZ = window_samples, sample_rate_hz
    try:
        yield
    finally:
        config.RUL_COMMON_WINDOW_SAMPLES, config.RUL_COMMON_SAMPLE_RATE_HZ = before


# The two ways the test labs are processed: as recorded, and with the full transfer pipeline of
# CODE_GUIDE section 16 (0.1 s windows at 25.6 kHz, the settings of PHM 2012).
FEATURE_VARIANTS = {"native": (0, 0.0), "common": (2560, 25600.0)}


class RunToFailureAdapter(DatasetAdapter):

    snapshot_channels = ("horizontal", "vertical")

    def read_snapshot(self, path):
        """(samples, 2) horizontal and vertical acceleration."""
        raise NotImplementedError

    def feature_names(self):
        names = []
        for channel in self.snapshot_channels:
            names.extend(vibration_feature_names(channel))
        return tuple(names)

    # A dataset whose snapshots are not best measured as one block gives the window here
    # (in samples). config.RUL_COMMON_WINDOW_SAMPLES, when set, takes precedence.
    native_window_samples = 0

    def read_recording_snapshot(self, recording, path):
        """Hook for datasets that need to know which recording a file belongs to (channel choice)."""
        return self.read_snapshot(path)

    def cache_kind(self):
        window = int(config.RUL_COMMON_WINDOW_SAMPLES)
        rate = float(config.RUL_COMMON_SAMPLE_RATE_HZ)
        return "run" if window <= 0 and rate <= 0 else "run_w%d_r%d" % (window, round(rate))

    def is_cached(self, recording):
        cached = self.load_cache(self.cache_path(recording, self.cache_kind()), recording.signature())
        return cached is not None and tuple(cached["names"]) == self.feature_names()

    def snapshot_times(self, recording):
        first = file_number(recording.files[0])
        return np.array([(file_number(f) - first) * recording.snapshot_interval
                         for f in recording.files], dtype=np.float64)

    def extract_run(self, recording, progress=None, cancel=None):
        """
        Returns dict(times, features, names, life_fraction, rul_fraction).
        Cached in data/processed/<dataset>/.
        """
        names = self.feature_names()
        window = int(config.RUL_COMMON_WINDOW_SAMPLES) or int(self.native_window_samples)
        target_rate = float(config.RUL_COMMON_SAMPLE_RATE_HZ)
        scale = float(recording.meta.get("scale_to_g", 1.0))
        # The two settings change the features, so each combination has its own cache.
        cache = self.cache_path(recording, self.cache_kind())
        signature = recording.signature()
        cached = self.load_cache(cache, signature)
        if cached is None or tuple(cached["names"]) != names:
            rows = []
            for index, path in enumerate(recording.files):
                snapshot = self.read_recording_snapshot(recording, path)
                row = []
                for c in range(len(self.snapshot_channels)):
                    signal, rate = harmonize(snapshot[:, c], recording.sample_rate, scale, target_rate)
                    parts = [vibration_features(part, rate) for part in split_windows(signal, window)]
                    row.extend(parts[0] if len(parts) == 1 else np.mean(parts, axis=0))
                rows.append(row)
                if progress is not None and index % 50 == 0:
                    progress(index, len(recording.files))
                if cancel is not None and cancel():
                    raise KeyboardInterrupt("cancelled")
            features = np.array(rows, dtype=np.float64)
            self.save_cache(cache, signature, features=features, names=np.array(names))
        else:
            features = cached["features"]
        times = self.snapshot_times(recording)
        life = times / times[-1] if times[-1] > 0 else np.zeros_like(times)
        return {
            "run_id": recording.run_id, "dataset": self.name, "condition": recording.condition,
            "times": times, "features": features, "names": names,
            "life_fraction": life, "rul_fraction": 1.0 - life,
            "total_life_s": float(times[-1]),
            "shaft_hz": recording.meta.get("shaft_hz"), "load_n": recording.meta.get("load_n"),
        }
