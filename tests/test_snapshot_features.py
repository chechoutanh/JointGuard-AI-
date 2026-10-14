"""Features of one snapshot, on signals small or simple enough to work out by hand."""

import math

import numpy as np
import pytest

from features.snapshot import feature_names, fill_missing, snapshot_features

BANDS = ((10, 500), (500, 1000), (1000, 2000), (2000, 4000), (4000, 8000))


def column(values):
    return np.array(values, dtype=float).reshape(-1, 1)


def tone(fs, n, *parts):
    """Sum of sines; parts are (frequency in Hz, amplitude)."""
    t = np.arange(n) / fs
    return column(sum(a * np.sin(2 * np.pi * f * t) for f, a in parts))


def named(x, fs, bands=BANDS):
    """Features of a one-channel signal as {name: value}."""
    return dict(zip(feature_names(bands), snapshot_features(x, fs, bands)[0]))


def test_time_features_of_a_signal_worked_by_hand():
    # mean 0; squares 1,1,1,1,9,9,9,9 -> mean 5; fourth powers 1 x4, 81 x4 -> mean 41
    f = named(column([1, -1, 1, -1, 3, -3, 3, -3]), fs=25600.0)

    assert f["rms"] == pytest.approx(math.sqrt(5))
    assert f["peak"] == pytest.approx(3.0)
    assert f["kurtosis"] == pytest.approx(41 / 25)
    assert f["crest"] == pytest.approx(3 / math.sqrt(5))


def test_a_constant_sensor_offset_changes_nothing():
    signal = tone(20000.0, 20000, (300, 2.0), (3000, 0.5))

    plain = snapshot_features(signal, 20000.0, BANDS)
    shifted = snapshot_features(signal + 10.0, 20000.0, BANDS)

    assert shifted == pytest.approx(plain, rel=1e-9, abs=1e-9)


def test_a_tone_lands_in_the_band_that_holds_its_frequency():
    # a sine of amplitude 2 has rms 2 / sqrt(2)
    f = named(tone(20000.0, 20000, (300, 2.0)), fs=20000.0)

    assert f["band_10_500"] == pytest.approx(math.sqrt(2), rel=1e-6)
    assert f["band_500_1000"] == pytest.approx(0.0, abs=1e-6)
    assert f["band_4000_8000"] == pytest.approx(0.0, abs=1e-6)


def test_bands_are_in_hz_so_two_sampling_rates_agree():
    # the same vibration as IMS would record it (20 kHz, 20480 samples)
    # and as XJTU-SY would (25.6 kHz, 32768 samples)
    as_ims = named(tone(20000.0, 20480, (300, 1.0), (3000, 0.5)), fs=20000.0)
    as_xjtu = named(tone(25600.0, 32768, (300, 1.0), (3000, 0.5)), fs=25600.0)

    want = {"band_10_500": 1 / math.sqrt(2), "band_500_1000": 0.0, "band_1000_2000": 0.0,
            "band_2000_4000": 0.5 / math.sqrt(2), "band_4000_8000": 0.0}
    for name, value in want.items():
        assert as_ims[name] == pytest.approx(value, abs=1e-3), name
        assert as_xjtu[name] == pytest.approx(value, abs=1e-3), name


def test_a_band_above_what_the_sampling_rate_can_show_is_refused():
    # at 100 Hz nothing above 50 Hz can be measured
    with pytest.raises(ValueError, match="Nyquist"):
        snapshot_features(tone(100.0, 200, (10, 1.0)), 100.0, ((10, 40), (40, 60)))


def test_centroid_is_the_power_weighted_mean_frequency():
    # powers 0.5 at 100 Hz and 1.5 at 300 Hz -> (100 x 0.5 + 300 x 1.5) / 2 = 250 Hz
    f = named(tone(2000.0, 2000, (100, 1.0), (300, math.sqrt(3))), fs=2000.0, bands=((10, 500),))

    assert f["centroid_hz"] == pytest.approx(250.0, abs=0.5)


def test_each_channel_gets_its_own_row():
    two = np.hstack([tone(20000.0, 20000, (300, 1.0)), tone(20000.0, 20000, (300, 2.0))])

    rows = snapshot_features(two, 20000.0, BANDS)
    rms = feature_names(BANDS).index("rms")

    assert rows.shape == (2, len(feature_names(BANDS)))
    assert rows[:, rms] == pytest.approx([1 / math.sqrt(2), 2 / math.sqrt(2)])


def test_a_missing_reading_is_filled_from_its_neighbours():
    filled = fill_missing(np.array([[1.0, 10.0], [np.nan, 20.0], [3.0, np.nan], [4.0, np.nan]]))

    assert filled.tolist() == [[1.0, 10.0], [2.0, 20.0], [3.0, 20.0], [4.0, 20.0]]


def test_a_missing_reading_does_not_spoil_the_features():
    signal = tone(20000.0, 20000, (300, 2.0))
    with_gap = signal.copy()
    with_gap[5000, 0] = np.nan

    assert snapshot_features(with_gap, 20000.0, BANDS) == pytest.approx(
        snapshot_features(signal, 20000.0, BANDS), rel=1e-3, abs=1e-3)
