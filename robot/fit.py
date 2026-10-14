"""Read Coulomb and viscous friction off one sweep. Used by the simulation's tests and by the model side."""

import numpy as np

from robot import config


def fit_friction(v, tau, rated):
    """Least-squares fit of tau = Fc * sign(v) + Fv * v. Returns (Fc, Fv).

    v is the measured speed of each point (rad/s), tau its friction torque
    (N m), rated the joint's rated speed. Points slower than FIT_MIN_FRAC of
    rated speed are left out.
    """
    v, tau = np.asarray(v, dtype=float), np.asarray(tau, dtype=float)
    keep = np.abs(v) >= config.FIT_MIN_FRAC * rated
    if keep.sum() < 2:
        raise ValueError(f"the fit needs at least 2 points at or above {config.FIT_MIN_FRAC} of rated speed, got {keep.sum()}")
    design = np.column_stack([np.sign(v[keep]), v[keep]])
    (fc, fv), *_ = np.linalg.lstsq(design, tau[keep], rcond=None)
    return float(fc), float(fv)
