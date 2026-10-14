"""IMS adapter, on small files written in the real layout: one text file per
snapshot, named by its time, tab separated, CRLF line ends, no header."""

import pytest

import config
from sources import ims


def write_snapshot(folder, name, n_columns, base, rows=3):
    """Column j (from 0) of the file holds base + j."""
    folder.mkdir(parents=True, exist_ok=True)
    line = "\t".join(f"{base + j:.3f}" for j in range(n_columns))
    (folder / name).write_bytes(("\r\n".join([line] * rows) + "\r\n").encode())


def write_all_three_tests(root):
    write_snapshot(root / "1st_test", "2003.10.22.12.06.24", 8, base=100)
    write_snapshot(root / "1st_test", "2003.10.22.12.16.24", 8, base=200)
    write_snapshot(root / "2nd_test", "2004.02.12.10.32.39", 4, base=300)
    write_snapshot(root / "4th_test" / "txt", "2004.03.04.09.27.46", 4, base=400)


def test_each_failed_bearing_reads_its_own_columns(tmp_path):
    write_all_three_tests(tmp_path)

    recs = {r.unit_id: r for r in ims.load(tmp_path)}

    assert sorted(recs) == ["test1_b3", "test1_b4", "test2_b1", "test3_b3"]
    assert recs["test1_b3"].snapshot(0).tolist() == [[104.0, 105.0]] * 3
    assert recs["test1_b4"].snapshot(1).tolist() == [[206.0, 207.0]] * 3
    assert recs["test2_b1"].snapshot(0).tolist() == [[300.0]] * 3
    assert recs["test3_b3"].snapshot(0).tolist() == [[402.0]] * 3


def test_two_bearings_of_one_test_share_a_run(tmp_path):
    write_all_three_tests(tmp_path)

    runs = {r.unit_id: r.run_id for r in ims.load(tmp_path)}

    assert runs == {"test1_b3": "test1", "test1_b4": "test1", "test2_b1": "test2", "test3_b3": "test3"}


def test_time_comes_from_the_file_names(tmp_path):
    for name in ("2004.02.12.10.32.39", "2004.02.12.10.35.28", "2004.02.12.10.45.28"):
        write_snapshot(tmp_path / "2nd_test", name, 4, base=0)

    (rec,) = ims.load(tmp_path)

    assert list(rec.t_hours) == pytest.approx([0.0, 169 / 3600, 769 / 3600])
    assert rec.failure_hours == pytest.approx(769 / 3600)
    assert (rec.source, rec.fs, rec.fault_class, rec.condition) == ("ims", 20000.0, None, "2000rpm_6000lb")


def test_a_stop_of_the_rig_adds_one_normal_step_not_the_whole_stop(tmp_path):
    for name in ("2003.10.22.12.06.24", "2003.10.22.12.16.24", "2003.10.23.08.16.24"):  # 10 min, then 20 h
        write_snapshot(tmp_path / "2nd_test", name, 4, base=0)

    (rec,) = ims.load(tmp_path)

    assert list(rec.t_hours) == pytest.approx([0.0, 10 / 60, 20 / 60])


def test_without_a_step_limit_time_is_calendar_time(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "IMS_MAX_STEP_MINUTES", None)
    for name in ("2003.10.22.12.06.24", "2003.10.22.12.16.24", "2003.10.23.08.16.24"):
        write_snapshot(tmp_path / "2nd_test", name, 4, base=0)

    (rec,) = ims.load(tmp_path)

    assert list(rec.t_hours) == pytest.approx([0.0, 10 / 60, 10 / 60 + 20.0])


def test_a_test_that_is_not_unpacked_is_left_out(tmp_path):
    write_snapshot(tmp_path / "2nd_test", "2004.02.12.10.32.39", 4, base=0)
    (tmp_path / "2nd_test" / ".DS_Store").write_bytes(b"\x00")

    recs = ims.load(tmp_path)

    assert [(r.unit_id, len(r)) for r in recs] == [("test2_b1", 1)]
