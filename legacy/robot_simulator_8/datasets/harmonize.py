"""
Make recordings from different labs comparable before any feature is computed.

    calibration      raw numbers -> acceleration in g (a per dataset scale)
    harmonization    one sample rate for every dataset
    common windowing features on windows of the same length, whatever the
                     snapshot length (XJTU-SY: 1.28 s, PHM 2012: 0.1 s)
    metadata         shaft speed and load, read from the condition name

Pure numpy / scipy, no dataset specific code.
"""

import re
from fractions import Fraction

import numpy as np


def operating_condition(text):
    """'35Hz12kN' or '1800rpm_4000N' -> {'shaft_hz': ..., 'load_n': ...} (missing parts are left out)."""
    out = {}
    text = str(text)
    hz = re.search(r"([\d.]+)\s*Hz", text, re.IGNORECASE)
    rpm = re.search(r"([\d.]+)\s*rpm", text, re.IGNORECASE)
    kn = re.search(r"([\d.]+)\s*kN", text, re.IGNORECASE)
    newton = re.search(r"([\d.]+)\s*N(?![a-zA-Z])", text)
    if hz:
        out["shaft_hz"] = float(hz.group(1))
    elif rpm:
        out["shaft_hz"] = float(rpm.group(1)) / 60.0
    if kn:
        out["load_n"] = 1000.0 * float(kn.group(1))
    elif newton:
        out["load_n"] = float(newton.group(1))
    return out


def harmonize(signal, sample_rate, scale_to_g=1.0, target_rate=0.0):
    """
    Returns (signal in g at the target rate, that rate). target_rate 0 keeps
    the recording's own rate. Resampling is band limited (polyphase filter), so
    a slower target rate also removes what it cannot represent.
    """
    x = np.asarray(signal, dtype=np.float64) * float(scale_to_g)
    if not target_rate or abs(target_rate - sample_rate) < 1e-6:
        return x, float(sample_rate)
    from scipy.signal import resample_poly
    ratio = Fraction(float(target_rate) / float(sample_rate)).limit_denominator(1000)
    return resample_poly(x, ratio.numerator, ratio.denominator), float(target_rate)


def split_windows(signal, samples):
    """
    Whole windows of `samples` values, in order, without overlap. A signal
    shorter than one window, or samples <= 0, gives the signal itself: the
    snapshot is then one window, as before common windowing existed.
    """
    x = np.asarray(signal)
    if samples <= 0 or x.shape[0] < samples:
        return [x]
    return [x[i:i + samples] for i in range(0, x.shape[0] - samples + 1, samples)]
