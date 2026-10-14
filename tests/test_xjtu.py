"""XJTU-SY adapter, on small files written in the real layout:
<condition>/<bearing>/<n>.csv, one header line, two columns."""

import pytest

from sources import xjtu


def write_bearing(root, condition, bearing, n_files, rows=4):
    """Snapshot n holds n in the horizontal column and -n in the vertical one."""
    folder = root / condition / bearing
    folder.mkdir(parents=True)
    for n in range(1, n_files + 1):
        lines = ["Horizontal_vibration_signals,Vertical_vibration_signals"]
        lines += [f"{float(n)},{float(-n)}"] * rows
        (folder / f"{n}.csv").write_text("\n".join(lines) + "\n")
    return folder


def test_snapshots_follow_the_file_number_not_the_alphabet(tmp_path):
    write_bearing(tmp_path, "35Hz12kN", "Bearing1_1", n_files=12)

    (rec,) = xjtu.load(tmp_path)

    assert [rec.snapshot(i)[0, 0] for i in range(12)] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]


def test_one_snapshot_per_minute_and_failure_at_the_last_one(tmp_path):
    write_bearing(tmp_path, "35Hz12kN", "Bearing1_1", n_files=4)

    (rec,) = xjtu.load(tmp_path)

    assert list(rec.t_hours) == pytest.approx([0.0, 1 / 60, 2 / 60, 3 / 60])
    assert rec.failure_hours == pytest.approx(3 / 60)
    assert len(rec) == 4


def test_one_recording_per_bearing_named_by_folder(tmp_path):
    write_bearing(tmp_path, "35Hz12kN", "Bearing1_2", n_files=2)
    write_bearing(tmp_path, "35Hz12kN", "Bearing1_1", n_files=2)
    write_bearing(tmp_path, "37.5Hz11kN", "Bearing2_1", n_files=2)

    recs = xjtu.load(tmp_path)

    assert [(r.unit_id, r.run_id, r.condition) for r in recs] == [
        ("Bearing1_1", "Bearing1_1", "35Hz_12kN"),
        ("Bearing1_2", "Bearing1_2", "35Hz_12kN"),
        ("Bearing2_1", "Bearing2_1", "37.5Hz_11kN"),
    ]
    assert {(r.source, r.fs, r.fault_class) for r in recs} == {("xjtu", 25600.0, None)}


def test_snapshot_is_samples_by_two_channels_without_the_header(tmp_path):
    write_bearing(tmp_path, "40Hz10kN", "Bearing3_1", n_files=3, rows=5)

    (rec,) = xjtu.load(tmp_path)
    snapshot = rec.snapshot(2)

    assert rec.channels == ("horizontal", "vertical")
    assert snapshot.shape == (5, 2)
    assert snapshot.tolist() == [[3.0, -3.0]] * 5


def test_loading_reads_no_signal_until_a_snapshot_is_asked_for(tmp_path):
    folder = write_bearing(tmp_path, "35Hz12kN", "Bearing1_1", n_files=3)
    (folder / "2.csv").write_text("Horizontal_vibration_signals,Vertical_vibration_signals\nbroken,file\n")

    (rec,) = xjtu.load(tmp_path)

    assert rec.snapshot(0)[0, 0] == 1.0
    with pytest.raises(ValueError):
        rec.snapshot(1)


def test_files_that_are_not_snapshots_are_ignored(tmp_path):
    folder = write_bearing(tmp_path, "35Hz12kN", "Bearing1_1", n_files=2)
    (tmp_path / ".DS_Store").write_bytes(b"\x00")
    (tmp_path / "Introduction_to_XJTU-SY_Bearing_Dataset.pdf").write_bytes(b"%PDF")
    (tmp_path / "35Hz12kN" / ".DS_Store").write_bytes(b"\x00")
    (folder / "notes.txt").write_text("not a snapshot")

    (rec,) = xjtu.load(tmp_path)

    assert len(rec) == 2
