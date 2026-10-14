"""Features relative to a unit's own healthy start.

Arrays are (snapshots, channels, features). Nothing here looks ahead: the value
at snapshot i depends only on snapshots 0 to i.
"""

import numpy as np


def relative(raw, n_healthy):
    """Each value divided by its healthy reference.

    The reference is the median of that feature over the unit's first n_healthy
    snapshots. Before that many exist, it is the median of those seen so far.
    """
    raw = np.asarray(raw, dtype=float)
    out = np.empty_like(raw)
    for i in range(min(n_healthy, len(raw))):
        out[i] = raw[i] / np.median(raw[:i + 1], axis=0)
    if len(raw) > n_healthy:
        out[n_healthy:] = raw[n_healthy:] / np.median(raw[:n_healthy], axis=0)
    return out


def worst_channel(rel):
    """One row per snapshot: for each feature, the sensor that changed the most."""
    return rel.max(axis=1)
