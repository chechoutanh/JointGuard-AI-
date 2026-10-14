"""List what each dataset adapter finds on disk.

    python -m tools.sources

Reads the first and the last snapshot of every recording, nothing more.
"""

import hashlib
import os

import numpy as np

import config
from sources import ims, kaist, seu_cwru, xjtu

SOURCES = [
    ("xjtu", config.XJTU_DIR, xjtu.load),
    ("ims", config.IMS_DIR, ims.load),
    ("kaist", config.KAIST_DIR, kaist.load),
    ("seu", config.SEU_DIR, seu_cwru.load_seu),
    ("cwru", config.CWRU_DIR, seu_cwru.load_cwru),
]


def describe(rec):
    """One table row for a recording."""
    first = rec.snapshot(0)
    missing = int(np.isnan(first).sum())
    if len(rec) > 1:
        missing += int(np.isnan(rec.snapshot(len(rec) - 1)).sum())
    return {
        "unit_id": rec.unit_id, "condition": rec.condition, "fault_class": rec.fault_class,
        "fs": rec.fs, "snapshots": len(rec), "hours": rec.failure_hours,
        "samples": first.shape[0], "channels": first.shape[1], "seconds": first.shape[0] / rec.fs,
        "missing": missing, "digest": hashlib.sha1(first.tobytes()).hexdigest(),
    }


def duplicates(rows):
    """Groups of unit ids whose first snapshot holds exactly the same numbers."""
    groups = {}
    for row in rows:
        groups.setdefault(row["digest"], []).append(row["unit_id"])
    return sorted(tuple(units) for units in groups.values() if len(units) > 1)


def main():
    for source, root, load in SOURCES:
        if not os.path.isdir(root):
            print(f"\n{source}: not found at {root}")
            continue
        rows = [describe(rec) for rec in load()]
        print(f"\n{source}: {len(rows)} recordings, {sum(r['snapshots'] for r in rows)} snapshots")
        print(f"  {'unit':24s} {'condition':15s} {'class':8s} {'fs Hz':>7s} {'snapshots':>9s} {'hours':>8s} "
              f"{'samples':>8s} {'chan':>4s} {'seconds':>8s} {'missing':>7s}")
        for r in rows:
            hours = "-" if r["hours"] is None else f"{r['hours']:.2f}"
            print(f"  {r['unit_id']:24s} {r['condition']:15s} {r['fault_class'] or '-':8s} {r['fs']:7.0f} "
                  f"{r['snapshots']:9d} {hours:>8s} {r['samples']:8d} {r['channels']:4d} "
                  f"{r['seconds']:8.2f} {r['missing']:7d}")
        print(f"  identical signals: {duplicates(rows) or 'none'}")


if __name__ == "__main__":
    main()
