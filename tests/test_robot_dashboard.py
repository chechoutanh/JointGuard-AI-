"""The dashboard: one self-contained HTML page made from the runs of a simulated scenario.

These tests cover what Python does: the numbers put into the page, and that
the page needs nothing from the internet. What the page draws is checked by
opening it (results/2026-10-12_robot_dashboard).
"""

import json
import os
import shutil

import pandas as pd
import pytest

from robot import config
from robot.health import daily_friction, health_index
from robot.simulate import simulate
from tools import dashboard

DAYS = 9
JOINTS = (0, 3)


@pytest.fixture(scope="module")
def scenario(tmp_path_factory):
    """Two short runs of two joints, laid out as the real dataset: <scenario>/run_<k>/."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(config, "SETTLE_S", 0.1)
        patch.setattr(config, "RECORD_S", 0.05)
        folder = tmp_path_factory.mktemp("data") / "ramp_early"
        for k in range(2):
            simulate("ramp_early", DAYS, seed=k, out_dir=str(folder / f"run_{k}"), joints=JOINTS)
        yield str(folder)


@pytest.fixture()
def every_fourth_day(monkeypatch):
    monkeypatch.setattr(dashboard, "SWEEP_EVERY", 4)


def embedded(html):
    """The data block of a page, parsed back."""
    start = html.index('<script id="data" type="application/json">') + len('<script id="data" type="application/json">')
    return json.loads(html[start:html.index("</script>", start)])


def test_payload_names_the_scenario_and_what_it_needs_to_draw(scenario):
    payload = dashboard.build_payload(scenario, include_truth=False)

    assert payload["scenario"] == "ramp_early"
    assert payload["threshold"] == config.FAIL_W
    assert payload["ramp_day"] == config.RAMP_DAY["ramp_early"]
    assert payload["truth"] is False
    assert [run["run"] for run in payload["runs"]] == [0, 1]


def test_each_run_has_one_value_per_day_for_each_joint(scenario, every_fourth_day):
    run = dashboard.build_payload(scenario, include_truth=False)["runs"][0]

    assert run["days"] == DAYS
    assert len(run["duty_planned"]) == len(run["duty_actual"]) == DAYS
    assert [j["joint"] for j in run["joints"]] == list(JOINTS)
    for joint in run["joints"]:
        for name in ("fc", "fv", "temp", "index", "index_raw"):
            assert len(joint[name]) == DAYS, name
        assert [s["day"] for s in joint["sweeps"]] == [0, 4, 8]              # one whole sweep kept every fourth day
        assert all(len(s["v"]) == len(s["tau"]) == 18 for s in joint["sweeps"])


def test_the_numbers_are_the_ones_in_the_files(scenario):
    run = dashboard.build_payload(scenario, include_truth=False)["runs"][0]
    joint3 = run["joints"][1]
    files = os.path.join(scenario, "run_0")

    assert joint3["fc"][0] == pytest.approx(config.FC0, rel=0.05)            # day 0: the friction that was injected
    assert joint3["index"][0] == 0.0                                         # a joint is its own reference on day 0
    assert max(abs(x) for x in joint3["index"]) < 0.05                       # 9 days of wear are nearly nothing
    assert run["duty_planned"] == pytest.approx(pd.read_csv(os.path.join(files, "schedule.csv"))["duty_planned"].tolist(), abs=1e-4)
    assert run["duty_actual"] == pytest.approx(pd.read_csv(os.path.join(files, "actual_duty.csv"))["duty_actual"].tolist(), abs=1e-4)
    sweeps = pd.read_parquet(os.path.join(files, "sweeps.parquet"))
    day0 = sweeps[(sweeps["joint"] == 3) & (sweeps["day"] == 0)]
    assert joint3["temp"][0] == pytest.approx(day0["temperature_c"].iloc[0], abs=0.01)
    assert joint3["sweeps"][0]["tau"] == pytest.approx(day0["friction_torque"].tolist(), rel=1e-3)


def test_the_index_is_given_with_and_without_the_temperature_taken_out(scenario):
    joint3 = dashboard.build_payload(scenario, include_truth=False)["runs"][0]["joints"][1]
    daily = daily_friction(pd.read_parquet(os.path.join(scenario, "run_0", "sweeps.parquet")), 3)

    assert joint3["index"] == pytest.approx(health_index(daily["fc"], daily["temperature_c"]).tolist(), abs=1e-4)
    assert joint3["index_raw"] == pytest.approx(health_index(daily["fc"]).tolist(), abs=1e-4)
    assert max(abs(a - b) for a, b in zip(joint3["index"], joint3["index_raw"])) > 0.002      # temperature does matter
    assert joint3["fv"] == pytest.approx(daily["fv"].tolist(), rel=1e-3)


def test_without_truth_the_answer_key_is_not_in_the_page_at_all(scenario):
    html = dashboard.render(dashboard.build_payload(scenario, include_truth=False))
    data = json.dumps(embedded(html))

    assert '"wear"' not in data and '"service_day"' not in data


def test_with_truth_the_wear_and_service_day_are_added(scenario):
    payload = dashboard.build_payload(scenario, include_truth=True)

    assert payload["truth"] is True
    for joint in payload["runs"][1]["joints"]:
        assert len(joint["wear"]) == DAYS
        assert joint["wear"][-1] > joint["wear"][0] > 0
        assert joint["service_day"] is None                                  # nothing needs service after 9 days


def test_the_page_is_self_contained_and_says_simulation(scenario):
    html = dashboard.render(dashboard.build_payload(scenario, include_truth=True))

    assert "http://" not in html and "https://" not in html                  # nothing is loaded from the internet
    assert "<script src" not in html and "<link" not in html and "@import" not in html
    assert "simulation" in html.lower()
    assert "__DATA__" not in html                                            # the placeholder was filled


def test_the_data_in_the_page_is_the_payload(scenario):
    payload = dashboard.build_payload(scenario, include_truth=True)

    assert embedded(dashboard.render(payload)) == payload


def test_data_cannot_break_out_of_its_script_block():
    payload = {"scenario": "</script><b>not markup</b>", "runs": []}

    html = dashboard.render(payload)

    assert "</script><b>not markup" not in html
    assert embedded(html) == payload


def test_a_day_without_a_sweep_is_a_gap_not_a_number(scenario, tmp_path):
    gappy = tmp_path / "gappy"
    shutil.copytree(os.path.join(scenario, "run_0"), gappy / "run_0")
    path = gappy / "run_0" / "sweeps.parquet"
    sweeps = pd.read_parquet(path)
    sweeps[~((sweeps["day"] == 2) & (sweeps["joint"] == 3))].to_parquet(path, index=False)      # joint 3 lost its sweep of day 2

    payload = dashboard.build_payload(str(gappy), include_truth=False)
    joint0, joint3 = payload["runs"][0]["joints"]

    assert joint3["fc"][2] is None and joint3["index"][2] is None and joint3["temp"][2] is None
    assert None not in joint3["fc"][:2] + joint3["fc"][3:]
    assert None not in joint0["fc"]
    json.dumps(payload, allow_nan=False)                                     # no NaN: a browser would refuse it


def test_runs_come_in_number_order_not_in_text_order(tmp_path):
    for name in ("run_10", "run_2", "run_0", "notes"):
        os.makedirs(tmp_path / name)

    assert [os.path.basename(f) for f in dashboard.run_folders(str(tmp_path))] == ["run_0", "run_2", "run_10"]


def test_a_folder_without_runs_is_an_error(tmp_path):
    with pytest.raises(ValueError, match="no run_"):
        dashboard.build_payload(str(tmp_path), include_truth=True)


def test_the_command_writes_one_page_per_scenario_and_says_where(scenario, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(config, "SIMULATION_DIR", os.path.dirname(scenario))
    monkeypatch.setattr(dashboard, "OUT_DIR", str(tmp_path))

    dashboard.main(["--scenario", "ramp_early"])

    path = tmp_path / "dashboard_ramp_early.html"
    assert embedded(path.read_text(encoding="utf-8"))["truth"] is True
    assert str(path) in capsys.readouterr().out

    dashboard.main(["--scenario", "ramp_early", "--no-truth"])
    assert embedded(path.read_text(encoding="utf-8"))["truth"] is False
