"""The leakage guard: the file a model reads must never hold the hidden wear."""

import pandas as pd
import pytest

from robot.guard import FORBIDDEN, assert_no_leakage

ALLOWED = ["day", "joint", "v_target", "v_measured", "friction_torque", "temperature_c", "posture_q", "payload_kg", "duty_planned"]


def test_the_columns_of_the_sweeps_file_pass():
    assert_no_leakage(ALLOWED)


@pytest.mark.parametrize("name", ["wear", "wear_true", "health_true", "service_day", "W"])
def test_each_forbidden_column_is_refused_by_name(name):
    assert name in FORBIDDEN
    with pytest.raises(AssertionError, match=f"leakage.*{name}"):
        assert_no_leakage(ALLOWED + [name])


def test_it_reads_the_columns_of_a_table():
    table = pd.DataFrame({"day": [0], "friction_torque": [1.9]})
    assert_no_leakage(table.columns)

    table["wear"] = 0.1
    with pytest.raises(AssertionError):
        assert_no_leakage(table.columns)
