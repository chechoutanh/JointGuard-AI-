"""Features: one worked example to check by hand, and a sanity check on the cached XJTU-SY features.

    python results/2026-10-07_features/check.py            (from the project root)

Part 1, worked example. Six made-up snapshots of 8 samples each, run through the
same functions the real data goes through. Every number can be redone on paper.

Part 2, sanity check on the development set (needs python -m tools.features xjtu
first). Expectation, written before the run: a bearing shakes harder before it
fails, so the relative rms of the last snapshot should be above 1 for all 15
bearings, and close to 1 on average over the healthy start. This checks the
pipeline. It is not a result about predicting anything.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.getcwd())

import config
from features import cache
from features.relative import relative, worst_channel
from features.snapshot import feature_names, snapshot_features
from sources import xjtu


def worked_example():
    bands = ((1, 4),)             # one band, 1 to 4 Hz: everything this sampling rate can show
    fs = 8.0                      # 8 samples per second, so each snapshot is 1 second
    base = np.array([0.0, 1.0, 0.0, -1.0, 0.0, 1.0, 0.0, -1.0])     # a 2 Hz sine, amplitude 1
    amplitudes = [2, 3, 2, 4, 8, 16]
    names = feature_names(bands)

    print("PART 1: worked example")
    print(f"each snapshot is {base.tolist()} times an amplitude, at {fs:g} samples per second")
    print(f"amplitudes of the six snapshots: {amplitudes}\n")
    raw = np.stack([snapshot_features((a * base).reshape(-1, 1), fs, bands) for a in amplitudes])
    print("raw features, one row per snapshot")
    print("  amplitude " + " ".join(f"{name:>11s}" for name in names))
    for a, row in zip(amplitudes, raw[:, 0, :]):
        print(f"  {a:9d} " + " ".join(f"{v:11.4f}" for v in row))

    n_healthy = 3
    rel = worst_channel(relative(raw, n_healthy))
    rms = names.index("rms")
    print(f"\nrelative rms, healthy reference = median of the first {n_healthy} snapshots seen so far")
    print(f"  {'snapshot':>8s} {'rms':>8s} {'reference':>10s} {'relative':>9s}")
    for i in range(len(raw)):
        reference = np.median(raw[:min(i + 1, n_healthy), 0, rms])
        print(f"  {i:8d} {raw[i, 0, rms]:8.4f} {reference:10.4f} {rel[i, rms]:9.4f}")


def sanity_check():
    bands = config.BANDS_HZ["xjtu"]
    n = config.HEALTHY_SNAPSHOTS
    print(f"\nPART 2: XJTU-SY, relative rms (largest of the two sensors), healthy snapshots = {n}")
    print(f"  {'bearing':12s} {'condition':12s} {'snapshots':>9s} {'healthy start: mean':>20s} {'last snapshot':>14s} "
          f"{'largest':>9s} {'missing':>8s}")
    last_values, start_values = [], []
    for rec in xjtu.load():
        feats = cache.load(cache.path(rec.source, rec.unit_id), bands)
        rel = worst_channel(relative(feats.raw, n))[:, feats.names.index("rms")]
        last_values.append(rel[-1])
        start_values.append(rel[:n].mean())
        print(f"  {feats.unit_id:12s} {feats.condition:12s} {len(rel):9d} {rel[:n].mean():20.3f} {rel[-1]:14.2f} "
              f"{rel.max():9.2f} {int(feats.missing.sum()):8d}")
    above = sum(v > 1 for v in last_values)
    print(f"\n  last snapshot above 1: {above} of {len(last_values)} bearings "
          f"(smallest {min(last_values):.2f}, median {np.median(last_values):.2f}, largest {max(last_values):.2f})")
    print(f"  healthy start, mean relative rms over the bearings: {np.mean(start_values):.3f}")
    print(f"  expectation met: {above == len(last_values)}")


if __name__ == "__main__":
    worked_example()
    if os.path.isdir(os.path.join(config.PROCESSED_DIR, "xjtu")):
        sanity_check()
