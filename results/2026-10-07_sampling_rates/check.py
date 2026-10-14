"""Which sampling rate do the KAIST files and the CWRU normal files really have?

    python results/2026-10-07_sampling_rates/check.py     (from the project root)

Question. Neither dataset stores its rate. The earlier project used 6666.7 Hz
for KAIST (2,000,000 rows read as 5 minutes); the Mendeley page says 25.6 kHz.
For CWRU the fault files are the documented "12k drive end" set; the normal
files are usually reported as 48 kHz, with no rate in the files.

Method. A wrong rate moves every spectral line by the same factor, so lines
whose true position is known show which rate is right.
  KAIST: the shaft speed is documented (1770 to 1780 rpm). Its line must sit
         at 1x, not at a fraction.
  CWRU:  the fault files are known to be 12 kHz. They show which multiples of
         shaft speed, and which multiples of 60 Hz, this rig produces. The
         normal files come from the same rig, so read at the right rate they
         must show the same lines.

This script was written after a first look at the spectra, so it is a record
of the checks that settle the question, not a blind test. Only raw signals are
read; no feature, label or model is involved.
"""

import os
import sys

import numpy as np
from scipy.io import loadmat

sys.path.insert(0, os.getcwd())

import config
from sources import kaist, seu_cwru

KAIST_SHAFT_HZ = 1775 / 60
SHAFT_MULTIPLES = (0.25, 0.5, 1.0, 1.235, 1.35, 1.6, 2.0, 4.0, 4.94, 5.4, 6.4)
MAINS_HZ = (60, 120, 180, 240, 300, 360, 720)
# normal_1 and normal_2 store no speed: the speed of the fault files at the same load is used
NOMINAL_RPM = {"normal_1": 1772.0, "normal_2": 1750.0}


def spectrum(x):
    """Amplitude spectrum against frequency in cycles per sample."""
    x = x[np.isfinite(x)]
    x = x - x.mean()
    return np.fft.rfftfreq(len(x)), np.abs(np.fft.rfft(x * np.hanning(len(x))))


def strongest_lines(x, count, f_max):
    """The strongest separate spectral lines below f_max (cycles per sample)."""
    freq, amp = spectrum(x)
    keep = (freq > 2e-4) & (freq < f_max)
    freq, amp = freq[keep], amp[keep]
    guard = max(3, int(2e-4 * len(x)))
    picked = []
    for i in np.argsort(amp)[::-1]:
        if all(abs(i - j) > guard for j in picked):
            picked.append(i)
        if len(picked) == count:
            break
    return freq[picked]


def line_height(freq, amp, f_norm):
    """Peak within 0.4% of f_norm, over the median level within 20% of it. 1 means no line."""
    half_width = max(0.004 * f_norm, 1.5 * freq[1])
    near = np.abs(freq - f_norm) < half_width
    around = (np.abs(freq - f_norm) < 0.2 * f_norm) & ~near
    return amp[near].max() / np.median(amp[around])


def kaist_check():
    (rec,) = kaist.load()
    print(f"KAIST: two strongest low-frequency lines, in Hz and as a multiple of the shaft speed ({KAIST_SHAFT_HZ:.2f} Hz)")
    print(f"  {'snapshot':>8s} {'axis':4s} | {'if 6666.7 Hz':^34s} | {'if 25600 Hz':^34s}")
    for i in (0, 40, 80, 120):
        snapshot = rec.snapshot(i)
        for column, axis in enumerate(rec.channels):
            lines = np.sort(strongest_lines(snapshot[:, column], 2, 0.006))
            cells = [", ".join(f"{f * fs:5.1f} Hz = {f * fs / KAIST_SHAFT_HZ:4.2f}x" for f in lines)
                     for fs in (2_000_000 / 300, 25600.0)]
            print(f"  {i:8d} {axis:4s} | {cells[0]:34s} | {cells[1]:34s}")


def cwru_rpm(unit):
    mat = loadmat(os.path.join(config.CWRU_DIR, unit + ".mat"))
    keys = [key for key in mat if key.endswith("RPM")]
    return float(np.ravel(mat[max(keys)])[0]) if keys else NOMINAL_RPM[unit]


def cwru_check():
    recs = seu_cwru.load_cwru()
    spectra = {rec.unit_id: spectrum(rec.snapshot(0)[:, 0]) for rec in recs}      # drive-end sensor
    samples = {rec.unit_id: len(rec.snapshot(0)) for rec in recs}
    shaft = {unit: cwru_rpm(unit) / 60 for unit in spectra}
    faults = [unit for unit in spectra if not unit.startswith("normal")]
    normals = [unit for unit in spectra if unit.startswith("normal")]

    print("\nCWRU check 1: length of a recording in seconds")
    lengths = np.array([samples[u] for u in faults]) / 12000
    print(f"  {len(faults)} fault files at 12 kHz: {lengths.min():.1f} to {lengths.max():.1f} s")
    for unit in normals:
        print(f"  {unit}: {samples[unit] / 12000:5.1f} s if 12 kHz, {samples[unit] / 48000:5.1f} s if 48 kHz")

    def heights(unit, fs, hz_of):
        freq, amp = spectra[unit]
        return [line_height(freq, amp, hz_of(unit, value) / fs) for value in hz_of.values]

    def table(title, units_fault, units_normal, hz_of, labels):
        print(f"\n{title}")
        print(f"  {'':26s}" + "".join(f"{label:>8s}" for label in labels))
        fault = np.array([heights(u, 12000, hz_of) for u in units_fault])
        print(f"  {f'{len(units_fault)} fault files: median':26s}" + "".join(f"{v:8.1f}" for v in np.median(fault, axis=0)))
        print(f"  {'  share with a line (>5)':26s}" + "".join(f"{v:8.0%}" for v in (fault > 5).mean(axis=0)))
        for fs in (12000, 48000):
            for unit in units_normal:
                print(f"  {f'{unit} if {fs // 1000} kHz':26s}" + "".join(f"{v:8.1f}" for v in heights(unit, fs, hz_of)))

    def shaft_hz(unit, multiple):
        return multiple * shaft[unit]
    shaft_hz.values = SHAFT_MULTIPLES

    def mains_hz(unit, hz):
        return hz
    mains_hz.values = MAINS_HZ

    table("CWRU check 2: height of the line at each multiple of shaft speed (1 = no line)",
          faults, normals, shaft_hz, [f"{m:g}x" for m in SHAFT_MULTIPLES])
    # loads 2 and 3 hp only: at 0 and 1 hp the shaft multiples sit almost on the 60 Hz multiples
    high_load = {rec.unit_id for rec in recs if rec.condition in ("2hp", "3hp")}
    table("CWRU check 3: height of the line at each multiple of 60 Hz, loads 2 and 3 hp (1 = no line)",
          [u for u in faults if u in high_load], [u for u in normals if u in high_load],
          mains_hz, [f"{h} Hz" for h in MAINS_HZ])


if __name__ == "__main__":
    kaist_check()
    cwru_check()
