"""From saved sweeps to a health index: the reading side of the simulation.

This is what a model may do with sweeps.parquet. Nothing here touches the
hidden wear. The index is in wear units only because it divides by the wear
gain the simulation was built with, and the temperature is taken out with the
simulation's own coefficient: a real system would have to estimate both.
"""

import numpy as np
import pandas as pd

from robot import config
from robot.fit import fit_friction


def daily_friction(sweeps, joint):
    """Fitted friction of one joint on each day that has a sweep: columns day, fc, fv, temperature_c."""
    rows = sweeps[sweeps["joint"] == joint].sort_values("day", kind="stable")
    day = rows["day"].to_numpy()
    v, tau, temperature = (rows[name].to_numpy() for name in ("v_measured", "friction_torque", "temperature_c"))
    days, start = np.unique(day, return_index=True)
    out = []
    for d, a, b in zip(days, start, list(start[1:]) + [len(day)]):
        fc, fv = fit_friction(v[a:b], tau[a:b], config.RATED_RAD_S[joint])
        out.append((int(d), fc, fv, float(temperature[a])))
    return pd.DataFrame(out, columns=["day", "fc", "fv", "temperature_c"])


def health_index(fc, temperature_c=None):
    """(Fc / the joint's own reference - 1) / wear gain, for each day. 0 is new; the service threshold is FAIL_W.

    The reference is the mean Fc of the first BASELINE_DAYS days, and inside
    those days the mean of the days so far, so no value ever uses a later day.
    With temperature_c given, the temperature effect is taken out first.
    """
    fc = np.asarray(fc, dtype=float)
    if temperature_c is not None:
        fc = fc / (1 - config.TEMP_COEF * (np.asarray(temperature_c, dtype=float) - config.TEMP_REF_C))
    if len(fc) == 0:
        return fc
    first = fc[:config.BASELINE_DAYS]
    reference = np.full(len(fc), first.mean())
    reference[:len(first)] = np.cumsum(first) / np.arange(1, len(first) + 1)
    return (fc / reference - 1) / config.WEAR_GAIN_FC
