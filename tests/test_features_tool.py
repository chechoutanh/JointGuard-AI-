"""`python -m tools.features`: extraction over a recording, the cache file, and the command."""

import math

import numpy as np
import pytest

import config
from features import cache
from features.snapshot import feature_names
from sources.recording import Recording
from tools import features as tool

BANDS = config.RUL_BANDS_HZ
FS = 25600.0


def wave(rms, samples=64):
    """Four whole cycles of a 1600 Hz sine whose rms is the given value."""
    t = np.arange(samples) / FS
    return rms * math.sqrt(2) * np.sin(2 * np.pi * 1600 * t)


def recording(snapshots):
    return Recording(
        source="xjtu", unit_id="Bearing1_1", run_id="Bearing1_1", condition="35Hz_12kN", fs=FS,
        t_hours=np.arange(len(snapshots)) / 60, failure_hours=(len(snapshots) - 1) / 60,
        fault_class=None, channels=("horizontal", "vertical"), snapshot=lambda i: snapshots[i],
    )


def two_channels(rms):
    """Channel 0 has the given rms, channel 1 twice as much."""
    return np.column_stack([wave(rms), wave(2 * rms)])


def test_extract_gives_one_row_per_snapshot_and_channel():
    snapshots = [two_channels(a) for a in (2.0, 3.0, 5.0)]
    snapshots[1][7, 0] = np.nan

    raw, missing = tool.extract(recording(snapshots), BANDS)
    rms = feature_names(BANDS).index("rms")

    assert raw.shape == (3, 2, len(feature_names(BANDS)))
    assert raw[:, 1, rms] == pytest.approx([4.0, 6.0, 10.0])
    assert missing.tolist() == [0, 1, 0]


def test_saved_features_load_back_the_same(tmp_path):
    rec = recording([two_channels(a) for a in (2.0, 3.0)])
    raw, missing = tool.extract(rec, BANDS)
    path = tmp_path / "xjtu" / "Bearing1_1.npz"

    cache.save(path, rec, raw, missing, BANDS)
    got = cache.load(path, BANDS)

    assert np.array_equal(got.raw, raw)
    assert got.t_hours.tolist() == rec.t_hours.tolist()
    assert got.missing.tolist() == [0, 0]
    assert got.names == feature_names(BANDS)
    assert (got.source, got.unit_id, got.run_id, got.condition, got.fs, got.failure_hours, got.channels) == (
        "xjtu", "Bearing1_1", "Bearing1_1", "35Hz_12kN", FS, 1 / 60, ("horizontal", "vertical"))


def test_features_cached_with_other_bands_are_refused(tmp_path):
    rec = recording([two_channels(2.0)])
    raw, missing = tool.extract(rec, BANDS)
    path = tmp_path / "Bearing1_1.npz"
    cache.save(path, rec, raw, missing, BANDS)

    with pytest.raises(ValueError, match="--force"):
        cache.load(path, ((10, 500), (500, 9000)))


def write_xjtu_snapshot(folder, number, rms):
    """A snapshot file in the real XJTU-SY format: horizontal has the given rms, vertical twice as much."""
    folder.mkdir(parents=True, exist_ok=True)
    lines = ["Horizontal_vibration_signals,Vertical_vibration_signals"]
    lines += [f"{h!r},{v!r}" for h, v in two_channels(rms).tolist()]
    (folder / f"{number}.csv").write_text("\n".join(lines) + "\n")


@pytest.fixture
def project(tmp_path, monkeypatch):
    """A tiny XJTU-SY folder and an empty cache folder, in place of the real ones."""
    monkeypatch.setattr(config, "XJTU_DIR", str(tmp_path / "raw"))
    monkeypatch.setattr(config, "PROCESSED_DIR", str(tmp_path / "processed"))
    return tmp_path


def test_the_command_writes_one_cache_file_per_bearing(project):
    for number, rms in enumerate([2.0, 3.0, 5.0], start=1):
        write_xjtu_snapshot(project / "raw" / "35Hz12kN" / "Bearing1_1", number, rms)
    for number in (1, 2):
        write_xjtu_snapshot(project / "raw" / "35Hz12kN" / "Bearing1_2", number, 1.0)

    tool.main(["xjtu"])

    got = cache.load(cache.path("xjtu", "Bearing1_1"), BANDS)
    assert got.raw[:, :, got.names.index("rms")] == pytest.approx(np.array([[2.0, 4.0], [3.0, 6.0], [5.0, 10.0]]))
    assert cache.load(cache.path("xjtu", "Bearing1_2"), BANDS).raw.shape[0] == 2


def test_the_command_leaves_an_existing_cache_file_alone_unless_forced(project):
    folder = project / "raw" / "35Hz12kN" / "Bearing1_1"
    write_xjtu_snapshot(folder, 1, 2.0)
    tool.main(["xjtu"])
    write_xjtu_snapshot(folder, 1, 9.0)          # the raw file changes after it was cached

    def cached_rms():
        got = cache.load(cache.path("xjtu", "Bearing1_1"), BANDS)
        return got.raw[0, 0, got.names.index("rms")]

    tool.main(["xjtu"])
    kept = cached_rms()
    tool.main(["xjtu", "--force"])
    redone = cached_rms()

    assert kept == pytest.approx(2.0)
    assert redone == pytest.approx(9.0)
