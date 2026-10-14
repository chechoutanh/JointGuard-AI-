"""Extract the features of every snapshot of a source and cache them in data/processed/.

    python -m tools.features xjtu [--force]

One file per unit. A unit that is already cached is skipped unless --force is given.
"""

import argparse
import os
import time

import numpy as np

import config
from features import cache
from features.snapshot import snapshot_features
from sources import ims, kaist, xjtu

LOADERS = {"xjtu": xjtu.load, "ims": ims.load, "kaist": kaist.load}


def extract(rec, bands):
    """Raw features of every snapshot, (snapshots, channels, features), and the missing readings in each."""
    rows, missing = [], []
    for i in range(len(rec)):
        x = rec.snapshot(i)
        missing.append(int(np.isnan(x).sum()))
        rows.append(snapshot_features(x, rec.fs, bands))
    return np.stack(rows), np.array(missing)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Extract and cache snapshot features.")
    parser.add_argument("source", choices=sorted(LOADERS))
    parser.add_argument("--force", action="store_true", help="recompute units that are already cached")
    args = parser.parse_args(argv)

    bands = config.BANDS_HZ[args.source]
    for rec in LOADERS[args.source]():
        path = cache.path(rec.source, rec.unit_id)
        if os.path.exists(path) and not args.force:
            print(f"{rec.unit_id}: already cached")
            continue
        started = time.time()
        raw, missing = extract(rec, bands)
        cache.save(path, rec, raw, missing, bands)
        print(f"{rec.unit_id}: {len(rec)} snapshots, {int(missing.sum())} missing readings, "
              f"{time.time() - started:.0f} s")


if __name__ == "__main__":
    main()
