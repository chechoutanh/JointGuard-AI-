"""Features of one snapshot: an array of shape (samples, channels) at a known sampling rate."""

import numpy as np
from scipy.signal import get_window

TIME_FEATURES = ("rms", "peak", "kurtosis", "crest")


def feature_names(bands):
    """Names of the columns snapshot_features returns, for bands given as (low Hz, high Hz)."""
    return list(TIME_FEATURES) + [f"band_{lo}_{hi}" for lo, hi in bands] + ["centroid_hz"]


def fill_missing(x):
    """Missing readings (NaN) replaced by a straight line between their neighbours, per channel."""
    filled = np.array(x, dtype=float)
    index = np.arange(len(filled))
    for c in range(filled.shape[1]):
        present = np.isfinite(filled[:, c])
        if not present.all():
            filled[:, c] = np.interp(index, index[present], filled[present, c])
    return filled


def snapshot_features(x, fs, bands):
    """One row of features per channel, in the order of feature_names(bands)."""
    low, top = min(lo for lo, _ in bands), max(hi for _, hi in bands)
    if top > fs / 2:
        raise ValueError(f"band edge {top} Hz is above the Nyquist frequency ({fs / 2:g} Hz) of this signal")

    x = fill_missing(x)
    x = x - x.mean(axis=0)          # a sensor's constant offset says nothing about the machine
    n = len(x)

    mean_square = (x ** 2).mean(axis=0)
    rms = np.sqrt(mean_square)
    peak = np.abs(x).max(axis=0)
    kurtosis = (x ** 4).mean(axis=0) / mean_square ** 2      # 1.5 for a sine, 3 for random noise

    # Power at each frequency in Hz. The Hann window stops a strong low tone from leaking
    # into the quiet high bands. With this scaling the powers add up to the mean square,
    # so the square root of a band's sum is the rms of the signal inside that band.
    window = get_window("hann", n)
    power = 2 * np.abs(np.fft.rfft(x * window[:, None], axis=0)) ** 2 / (n * (window ** 2).sum())
    freq = np.fft.rfftfreq(n, d=1 / fs)
    band_rms = [np.sqrt(power[(freq >= lo) & (freq < hi)].sum(axis=0)) for lo, hi in bands]
    inside = (freq >= low) & (freq < top)
    centroid = (freq[inside, None] * power[inside]).sum(axis=0) / power[inside].sum(axis=0)

    return np.column_stack([rms, peak, kurtosis, peak / rms, *band_rms, centroid])
