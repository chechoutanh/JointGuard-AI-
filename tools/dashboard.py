"""One self-contained HTML page for the runs of a simulated scenario.

    python -m tools.dashboard [--scenario ramp_early] [--no-truth]

Reads data/simulation/<scenario>/run_<k>/ and writes
results/robot/dashboard_<scenario>.html. Open that file in a browser: it
needs no internet and no server. --no-truth leaves the hidden wear out of the
page altogether.

The page shows what can be read from the sweeps: each joint's health index
against the service threshold, the workload, the temperature and one sweep.
It shows no forecast, because there is none yet.

Everything here is simulation with illustrative parameters: the wear is
injected by hand.
"""

import argparse
import json
import os
import re

import numpy as np
import pandas as pd

from robot import config
from robot.health import daily_friction, health_index

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "results", "robot")
TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard_template.html")
SWEEP_EVERY = 10           # one whole sweep is kept every this many days: all of them would make the page 25 MB


def run_folders(scenario_dir):
    """The run_<k> folders of a scenario, in number order."""
    runs = [name for name in os.listdir(scenario_dir)
            if re.fullmatch(r"run_\d+", name) and os.path.isdir(os.path.join(scenario_dir, name))]
    return [os.path.join(scenario_dir, name) for name in sorted(runs, key=lambda name: int(name[4:]))]


def significant(value):
    """Five significant digits: the joints differ 200 times in size, so a fixed number of decimals fits none."""
    return float(f"{value:.5g}")


def per_day(days, values, n_days, rounded):
    """A list with one entry per day of the run: the rounded value, or None on a day without a sweep."""
    out = [None] * n_days
    for day, value in zip(days, values):
        out[int(day)] = rounded(float(value))
    return out


def load_run(folder, include_truth):
    sweeps = pd.read_parquet(os.path.join(folder, "sweeps.parquet"))
    planned = pd.read_csv(os.path.join(folder, "schedule.csv"))["duty_planned"]
    worked = pd.read_csv(os.path.join(folder, "actual_duty.csv"))["duty_actual"]
    n_days = len(planned)
    truth = pd.read_csv(os.path.join(folder, "ground_truth.csv")) if include_truth else None

    joints = []
    for joint in sorted(int(j) for j in sweeps["joint"].unique()):
        daily = daily_friction(sweeps, joint)
        days, fc, temperature = daily["day"].to_numpy(), daily["fc"].to_numpy(), daily["temperature_c"].to_numpy()
        rows = sweeps[(sweeps["joint"] == joint) & (sweeps["day"] % SWEEP_EVERY == 0)]
        entry = {
            "joint": joint,
            "fc": per_day(days, fc, n_days, significant),
            "fv": per_day(days, daily["fv"], n_days, significant),
            "temp": per_day(days, temperature, n_days, lambda x: round(x, 2)),
            "index": per_day(days, health_index(fc, temperature), n_days, lambda x: round(x, 4)),
            "index_raw": per_day(days, health_index(fc), n_days, lambda x: round(x, 4)),
            "sweeps": [{"day": int(day), "v": [round(float(x), 4) for x in group["v_measured"]],
                        "tau": [significant(x) for x in group["friction_torque"]]}
                       for day, group in rows.groupby("day")],
        }
        if include_truth:
            mine = truth[truth["joint"] == joint].sort_values("day")
            service = mine["service_day"].iloc[0]
            entry["wear"] = per_day(mine["day"], mine["wear"], n_days, lambda x: round(x, 4))
            entry["service_day"] = None if pd.isna(service) else int(service)
        joints.append(entry)

    return {"run": int(os.path.basename(folder)[4:]), "days": n_days,
            "duty_planned": [round(float(x), 4) for x in planned], "duty_actual": [round(float(x), 4) for x in worked],
            "joints": joints}


def build_payload(scenario_dir, include_truth=True):
    """Everything the page draws, as plain numbers."""
    folders = run_folders(scenario_dir)
    if not folders:
        raise ValueError(f"no run_<k> folders in {scenario_dir}: make them with python -m tools.robot demo --runs 5")
    scenario = os.path.basename(os.path.normpath(scenario_dir))
    return {"scenario": scenario, "threshold": config.FAIL_W, "ramp_day": config.RAMP_DAY.get(scenario),
            "sweep_every": SWEEP_EVERY, "truth": bool(include_truth),
            "runs": [load_run(folder, include_truth) for folder in folders]}


def render(payload):
    """The page: the template with the data put in."""
    with open(TEMPLATE, encoding="utf-8") as f:
        template = f.read()
    # "</" must not appear inside a script block; "<\/" is the same text to a JSON parser
    data = json.dumps(payload, allow_nan=False, separators=(",", ":")).replace("</", "<\\/")
    return template.replace("__DATA__", data)


def write(scenario_dir, path, include_truth=True):
    html = render(build_payload(scenario_dir, include_truth))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Dashboard of a simulated scenario (simulation only).")
    parser.add_argument("--scenario", choices=sorted(config.RAMP_DAY), default="ramp_early")
    parser.add_argument("--no-truth", action="store_true", help="leave the hidden wear out of the page")
    args = parser.parse_args(argv)

    path = write(os.path.join(config.SIMULATION_DIR, args.scenario), os.path.join(OUT_DIR, f"dashboard_{args.scenario}.html"),
                 include_truth=not args.no_truth)
    print(f"simulation only: dashboard of scenario {args.scenario}")
    print(f"wrote {path}  ({os.path.getsize(path) / 1e6:.1f} MB)")
    print("open it in a browser; it needs no internet")


if __name__ == "__main__":
    main()
