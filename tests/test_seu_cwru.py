"""SEU and CWRU adapters, on small files written in the real formats.

SEU: 16 header lines, then 8 values per line with a trailing separator; most
files use tabs, one uses commas. CWRU: MATLAB files with one variable per sensor."""

import numpy as np
from scipy.io import savemat

from sources import seu_cwru


def write_seu(path, sep, frequency_limit, rows):
    header = [
        ["Title:", "c_20_0_1-10"], ["Parameters:"], [], ["DAQ", "Settings:"],
        ["Frequency", "Limit", str(frequency_limit)], ["Spectral", "Lines", "1600"],
        ["Number", "of", "Blocks", "1024"], ["Total", "Data", "Rows", "4194304"], ["Channels:"],
        ["Legend"] + [f"Channel{i}" for i in range(1, 9)], [], ["On/Off"] + ["ON"] * 8, [],
        ["Volts/Unit"] + ["1"] * 8, [], ["Data"],
    ]
    lines = [sep.join(cells + [""] * (9 - len(cells))) for cells in header]
    lines += [sep.join(str(v) for v in row) + sep for row in rows]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


ROWS = [[r + c / 10 for c in range(8)] for r in range(3)]  # row r, channel c holds r + c/10


def test_seu_sampling_rate_is_read_from_each_file_header(tmp_path):
    write_seu(tmp_path / "gearset" / "Health_20_0.csv", "\t", 2000, ROWS)
    write_seu(tmp_path / "gearset" / "Miss_20_0.csv", "\t", 1000, ROWS)

    fs = {r.unit_id: r.fs for r in seu_cwru.load_seu(tmp_path)}

    assert fs == {"gearset/Health_20_0": 5120.0, "gearset/Miss_20_0": 2560.0}


def test_seu_reads_tab_files_and_comma_files(tmp_path):
    write_seu(tmp_path / "bearingset" / "ball_20_0.csv", ",", 2000, ROWS)
    write_seu(tmp_path / "bearingset" / "ball_30_2.csv", "\t", 2000, ROWS)

    recs = seu_cwru.load_seu(tmp_path)

    for rec in recs:
        snapshot = rec.snapshot(0)
        assert snapshot.shape == (3, 8)
        assert snapshot.tolist() == ROWS
    assert len(recs) == 2


def test_seu_class_and_condition_come_from_the_file_name(tmp_path):
    write_seu(tmp_path / "gearset" / "Health_20_0.csv", "\t", 2000, ROWS)
    write_seu(tmp_path / "gearset" / "Chipped_30_2.csv", "\t", 2000, ROWS)
    write_seu(tmp_path / "bearingset" / "health_30_2.csv", "\t", 2000, ROWS)
    write_seu(tmp_path / "bearingset" / "comb_20_0.csv", "\t", 2000, ROWS)
    (tmp_path / "dds").write_text("These data are acquired on Drivetrain Dynamics Simulator")
    (tmp_path / "gearset" / "4 kinds of gear faults").write_text("Chipped tooth")

    recs = seu_cwru.load_seu(tmp_path)

    assert [(r.unit_id, r.fault_class, r.condition) for r in recs] == [
        ("bearingset/comb_20_0", "comb", "20_0"),
        ("bearingset/health_30_2", "normal", "30_2"),
        ("gearset/Chipped_30_2", "chipped", "30_2"),
        ("gearset/Health_20_0", "normal", "20_0"),
    ]


def test_seu_file_is_one_snapshot_with_eight_named_channels(tmp_path):
    write_seu(tmp_path / "gearset" / "Root_20_0.csv", "\t", 2000, ROWS)

    (rec,) = seu_cwru.load_seu(tmp_path)

    assert (rec.source, rec.run_id, len(rec), list(rec.t_hours), rec.failure_hours) == (
        "seu", "gearset/Root_20_0", 1, [0.0], None)
    assert rec.channels == ("motor_vibration", "planetary_x", "planetary_y", "planetary_z",
                            "motor_torque", "parallel_x", "parallel_y", "parallel_z")


def write_cwru(path, records, rpm=None):
    """records: {number: first value}. Sensor arrays are columns of 4 samples, as in the real files."""
    path.parent.mkdir(parents=True, exist_ok=True)
    mat = {}
    for number, value in records.items():
        mat[f"X{number:03d}_DE_time"] = np.full((4, 1), float(value))
        mat[f"X{number:03d}_FE_time"] = np.full((4, 1), float(value) + 0.5)
        mat[f"X{number:03d}_BA_time"] = np.full((4, 1), -1.0)
        if rpm:
            mat[f"X{number:03d}RPM"] = np.array([[rpm]])
    savemat(path, mat)


def test_cwru_class_and_load_come_from_the_file_name(tmp_path):
    write_cwru(tmp_path / "B007_0.mat", {118: 1}, rpm=1796)
    write_cwru(tmp_path / "IR014_2.mat", {171: 2}, rpm=1752)
    write_cwru(tmp_path / "OR021@6_3.mat", {237: 3}, rpm=1721)
    write_cwru(tmp_path / "normal_1.mat", {98: 4})
    (tmp_path / "Bearing-dataset").write_text("Bearing dataset from Case Western Reserve University")

    recs = seu_cwru.load_cwru(tmp_path)

    assert [(r.unit_id, r.fault_class, r.condition) for r in recs] == [
        ("B007_0", "ball", "0hp"),
        ("IR014_2", "inner", "2hp"),
        ("OR021@6_3", "outer", "3hp"),
        ("normal_1", "normal", "1hp"),
    ]
    assert {(r.source, len(r), r.failure_hours) for r in recs} == {("cwru", 1, None)}


def test_cwru_normal_files_have_a_different_sampling_rate(tmp_path):
    write_cwru(tmp_path / "B007_0.mat", {118: 1}, rpm=1796)
    write_cwru(tmp_path / "normal_0.mat", {97: 2}, rpm=1796)

    fs = {r.unit_id: r.fs for r in seu_cwru.load_cwru(tmp_path)}

    assert fs == {"B007_0": 12000.0, "normal_0": 48000.0}


def test_cwru_snapshot_is_drive_end_then_fan_end(tmp_path):
    write_cwru(tmp_path / "IR007_0.mat", {105: 7}, rpm=1797)

    (rec,) = seu_cwru.load_cwru(tmp_path)

    assert rec.channels == ("drive_end", "fan_end")
    assert rec.snapshot(0).tolist() == [[7.0, 7.5]] * 4


def test_cwru_file_holding_two_records_uses_the_later_one(tmp_path):
    # The real normal_2.mat holds record 99 and also a copy of record 98, which is normal_1's data.
    write_cwru(tmp_path / "normal_1.mat", {98: 10})
    write_cwru(tmp_path / "normal_2.mat", {98: 10, 99: 20})

    recs = {r.unit_id: r for r in seu_cwru.load_cwru(tmp_path)}

    assert recs["normal_1"].snapshot(0)[0, 0] == 10.0
    assert recs["normal_2"].snapshot(0)[0, 0] == 20.0
