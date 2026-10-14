"""KAIST adapter, on small files written in the real layout: one CSV per hour,
named by its time, no header, columns x, y, bearing temperature, room temperature."""

import math

import pytest

import config
from sources import kaist


def write_file(folder, stamp, rows):
    folder.mkdir(parents=True, exist_ok=True)
    text = "\n".join(",".join(str(v) for v in row) for row in rows) + "\n"
    (folder / f"LogFile_{stamp}.csv").write_text(text)


def numbered_rows(n, start=0):
    """Row i holds x = i, y = -i and two temperatures."""
    return [(float(start + i), float(-(start + i)), 41.6, 24.8) for i in range(n)]


@pytest.fixture
def short_snapshots(monkeypatch):
    """10 Hz and 2 s, so that a snapshot is the first 20 rows of a file."""
    monkeypatch.setattr(config, "KAIST_FS", 10.0)
    monkeypatch.setattr(config, "KAIST_SNAPSHOT_SECONDS", 2.0)


def test_only_the_first_seconds_of_a_file_are_read(tmp_path, short_snapshots):
    write_file(tmp_path, "2022-06-20-17-00-31", numbered_rows(50))

    (rec,) = kaist.load(tmp_path)
    snapshot = rec.snapshot(0)

    assert snapshot.shape == (20, 2)
    assert snapshot[0].tolist() == [0.0, -0.0]
    assert snapshot[19].tolist() == [19.0, -19.0]


def test_the_whole_run_is_one_bearing_timed_by_the_file_names(tmp_path, short_snapshots):
    write_file(tmp_path, "2022-06-21-01-00-31", numbered_rows(20, start=200))
    write_file(tmp_path, "2022-06-20-17-00-31", numbered_rows(20, start=0))
    write_file(tmp_path, "2022-06-20-18-00-31", numbered_rows(20, start=100))

    (rec,) = kaist.load(tmp_path)

    assert list(rec.t_hours) == pytest.approx([0.0, 1.0, 8.0])
    assert rec.failure_hours == pytest.approx(8.0)
    assert [rec.snapshot(i)[0, 0] for i in range(3)] == [0.0, 100.0, 200.0]
    assert (rec.source, rec.unit_id, rec.run_id, rec.fs, rec.fault_class) == ("kaist", "bearing1", "kaist", 10.0, None)
    assert rec.channels == ("x", "y")


def test_a_missing_reading_stays_in_its_place(tmp_path, short_snapshots):
    rows = numbered_rows(20)
    rows[5] = ("NaN", "NaN", 41.6, 24.8)
    write_file(tmp_path, "2022-06-20-17-00-31", rows)

    (rec,) = kaist.load(tmp_path)
    snapshot = rec.snapshot(0)

    assert snapshot.shape == (20, 2)
    assert math.isnan(snapshot[5, 0]) and math.isnan(snapshot[5, 1])
    assert snapshot[6].tolist() == [6.0, -6.0]
