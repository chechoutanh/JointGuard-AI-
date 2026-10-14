"""Milestone M4: what does each realism switch do to the data, and to a forecast of the service day?

    python results/2026-10-12_robot_switches/generate.py <name>     (six times, see that file)
    python results/2026-10-12_robot_switches/effect.py              (from the project root, about 2 minutes)

Compares data/switches/<name>/ with data/simulation/ramp_early/ (every switch
off). Both hold the same five robots: seeds 0 to 4, 850 days, 30 joints.

THE FORECAST HERE IS A YARDSTICK, NOT THE PROJECT'S FORECAST. The project has
none yet. To put a number on each switch this script uses the plainest form
of the method in CLAUDE.md, for one joint, on the day the forecast is made:

  1. Coulomb friction of every day so far, from sweeps.parquet (fit_friction),
     with the temperature effect taken out using the true coefficient.
  2. health index = (Fc / mean Fc of the first 7 days - 1) / 1.5.
  3. a straight line through (planned work done so far, health index): its
     slope is the wear per unit of work.
  4. service day = the first day slope x planned work reaches 0.8, with the
     plan known into the future.

It reads the sweeps and the plan. It never reads ground_truth.csv; this
script reads that file only to score it. No baselines, no sensitivity to a
wrong plan, no tuning.

Everything here is simulation with illustrative parameters.
"""

import os
import sys
import tempfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())

from robot import config
from robot.fit import fit_friction
from robot.schedule import planned_duty
from robot.simulate import simulate

SCENARIO, RUNS, BASELINE_DAYS, HORIZON = "ramp_early", 5, 7, 3000
N = config.N_JOINTS
PLAN = np.cumsum([planned_duty(SCENARIO, d) for d in range(HORIZON)])     # planned work done by the end of each day
SWITCHED = os.path.join(os.path.dirname(config.SIMULATION_DIR), "switches")
CASES = [("every switch off", os.path.join(config.SIMULATION_DIR, SCENARIO)),
         ("WEAR_NOISE", os.path.join(SWITCHED, "wear_noise")),
         ("WEAR_ACCEL", os.path.join(SWITCHED, "wear_accel")),
         ("WEAR_AFFECTS_FV", os.path.join(SWITCHED, "wear_affects_fv")),
         ("MODEL_MISMATCH", os.path.join(SWITCHED, "model_mismatch")),
         ("SENSOR_FAULTS", os.path.join(SWITCHED, "sensor_faults")),
         ("all five on", os.path.join(SWITCHED, "all"))]


def joint_series(sweeps, joint):
    """Per day with a sweep: day, fitted Fc, fitted Fv, temperature, mean torque of the sweep."""
    rows = sweeps[sweeps["joint"] == joint]
    day = rows["day"].to_numpy()
    v, tau, temp = rows["v_measured"].to_numpy(), rows["friction_torque"].to_numpy(), rows["temperature_c"].to_numpy()
    days, start = np.unique(day, return_index=True)
    out = []
    for d, a, b in zip(days, start, list(start[1:]) + [len(day)]):
        fc, fv = fit_friction(v[a:b], tau[a:b], config.RATED_RAD_S[joint])
        out.append((d, fc, fv, temp[a], tau[a:b].mean()))
    return np.array(out).T


def health_index(fc, temp):
    fc = fc / (1 - config.TEMP_COEF * (temp - config.TEMP_REF_C))
    return (fc / fc[:BASELINE_DAYS].mean() - 1) / config.WEAR_GAIN_FC


def yardstick(days, index, today):
    """Predicted service day, using only the sweeps up to today and the plan."""
    seen = days <= today
    slope, _ = np.polyfit(PLAN[days[seen].astype(int)], index[seen], 1)
    if slope <= 0:
        return np.nan
    reached = slope * PLAN >= config.FAIL_W
    return float(np.argmax(reached)) if reached.any() else np.nan


def score(folder):
    """One row per joint trajectory of the five runs in a folder."""
    out = []
    for k in range(RUNS):
        run = os.path.join(folder, f"run_{k}")
        sweeps = pd.read_parquet(os.path.join(run, "sweeps.parquet"))
        truth = pd.read_csv(os.path.join(run, "ground_truth.csv"))
        for joint in range(N):
            wear = truth[truth["joint"] == joint].sort_values("day")["wear"].to_numpy()
            service = truth[truth["joint"] == joint]["service_day"].iloc[0]
            days, fc, fv, temp, offset = joint_series(sweeps, joint)
            index = health_index(fc, temp)
            start = wear[:BASELINE_DAYS].mean()
            expected = ((1 + config.WEAR_GAIN_FC * wear) / (1 + config.WEAR_GAIN_FC * start) - 1) / config.WEAR_GAIN_FC
            alive = days <= service
            row = {"run": k, "joint": joint, "service": service,
                   "index_error": np.abs(index[alive] - expected[days[alive].astype(int)]).mean(),
                   "missing": 1 - len(days) / len(wear),
                   "offset": np.mean(offset[:30]) / (config.FC0 * config.JOINT_SIZE[joint]),
                   "fc_start": fc[:30].mean(), "fv_start": fv[:30].mean()}
            for share in (0.5, 0.75):
                today = int(round(share * service))
                row[f"error_{share}"] = yardstick(days, index, today) - service
            out.append(row)
    return pd.DataFrame(out)


def main():
    print("A. With every switch off, does today's code still write the dataset on disk? (seed 0, first 30 days)")
    stored = os.path.join(config.SIMULATION_DIR, SCENARIO, "run_0")
    with tempfile.TemporaryDirectory() as folder:
        simulate(SCENARIO, 30, 0, folder)
        for name in ("sweeps.parquet", "ground_truth.csv"):
            read = pd.read_parquet if name.endswith(".parquet") else pd.read_csv
            now, then = read(os.path.join(folder, name)), read(os.path.join(stored, name))
            then = then[then["day"] < 30].reset_index(drop=True)
            same = now.drop(columns=["service_day"], errors="ignore").equals(then.drop(columns=["service_day"], errors="ignore"))
            print(f"  {name:18s} identical to the first 30 days on disk: {same}")

    scores = {label: score(folder) for label, folder in CASES if os.path.isdir(os.path.join(folder, "run_0"))}
    off = scores["every switch off"]

    print("\nB. What each switch does, over the same 30 joints (5 robots x 6 joints, early ramp, 850 days)")
    print("   service day: change against the same joint with every switch off; 'never' counts joints that do not reach")
    print("   service in 850 days. Forecast error: predicted minus true service day, in days, with the yardstick")
    print("   described at the top of this file.")
    print(f"  {'':18s} {'true service day':^26s} {'health index':>12s} {'forecast at half of life':^27s} {'forecast at 3/4 of life':^27s} {'sweeps':>8s}")
    print(f"  {'switched on':18s} {'mean change':>12s} {'largest':>8s} {'never':>5s} {'error':>11s} {'mean |err|':>10s} {'mean':>7s} {'worst':>8s} "
          f"{'mean |err|':>10s} {'mean':>7s} {'worst':>8s} {'missing':>8s}")
    for label, s in scores.items():
        shift = (s["service"] - off["service"]).dropna()
        cells = []
        for share in (0.5, 0.75):
            e = s[f"error_{share}"].dropna()
            cells.append(f"{e.abs().mean():10.1f} {e.mean():+7.1f} {e[e.abs().idxmax()]:+8.0f}")
        print(f"  {label:18s} {shift.mean():+12.1f} {shift[shift.abs().idxmax()]:+8.0f} {int(s['service'].isna().sum()):5d} "
              f"{s['index_error'].mean():11.4f} {cells[0]} {cells[1]} {s['missing'].mean():8.1%}")

    print("\nC. What each switch does to the first 30 days of sweeps, against the same joint with every switch off")
    print(f"  {'switched on':18s} {'Fc, largest change':>19s} {'Fv, largest change':>19s} {'offset of the curve, largest (share of Fc)':>43s}")
    for label, s in scores.items():
        fc = (s["fc_start"] / off["fc_start"] - 1).abs().max()
        fv = (s["fv_start"] / off["fv_start"] - 1).abs().max()
        print(f"  {label:18s} {fc:19.2%} {fv:19.2%} {s['offset'].abs().max():43.1%}")

    print("\nD. The forecast error of every joint, at half of life, days (rows: robot, columns: joint)")
    for label in ("every switch off", "WEAR_ACCEL", "all five on"):
        if label in scores:
            table = scores[label].pivot(index="run", columns="joint", values="error_0.5")
            print(f"  {label}")
            for k, row in table.iterrows():
                print(f"    robot {k}: " + " ".join(f"{x:+6.0f}" for x in row))


if __name__ == "__main__":
    main()
