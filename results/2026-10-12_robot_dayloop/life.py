"""Over a 400-day run of each scenario: does the friction read from the saved sweeps follow the hidden wear?

    python -m tools.robot demo --scenario ramp_early      (10 minutes)
    python -m tools.robot demo --scenario ramp_late       (10 minutes)
    python results/2026-10-12_robot_dayloop/life.py       (from the project root, a few seconds)

Reads data/simulation/<scenario>/ and writes results/robot/life_<scenario>.png.

This script is a check of the simulator, so it reads ground_truth.csv. A
model must not. The "health index" here is the plain one of CLAUDE.md:
(Fc / Fc of the first days - 1) / wear gain. Nothing is trained.

Everything here is simulation with illustrative parameters.
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())

from robot import config
from robot.fit import fit_friction
from robot.schedule import planned_duty

BASELINE_DAYS = 7          # the joint's own first week is its healthy reference
HORIZON = 2000             # days of plan to look ahead when asking how long a run must be


def load(scenario):
    folder = os.path.join(config.SIMULATION_DIR, scenario)
    sweeps = pd.read_parquet(os.path.join(folder, "sweeps.parquet"))
    truth = pd.read_csv(os.path.join(folder, "ground_truth.csv"))
    return sweeps, truth


def coulomb_by_day(sweeps, joint):
    """Fitted Coulomb friction and temperature of one joint on each day."""
    fc, temp = [], []
    for _, rows in sweeps[sweeps["joint"] == joint].groupby("day"):
        fc.append(fit_friction(rows["v_measured"], rows["friction_torque"], config.RATED_RAD_S[joint])[0])
        temp.append(rows["temperature_c"].iloc[0])
    return np.array(fc), np.array(temp)


def index(fc):
    return (fc / fc[:BASELINE_DAYS].mean() - 1) / config.WEAR_GAIN_FC


def planned_service_day(scenario, joint):
    """Day the joint would reach FAIL_W if every day went exactly to plan. No physics, no noise."""
    work = np.cumsum([planned_duty(scenario, d) for d in range(HORIZON)])
    return int(np.argmax(config.K_WEAR * config.RATE[joint] * work >= config.FAIL_W))


def report(scenario):
    sweeps, truth = load(scenario)
    days = int(sweeps["day"].max()) + 1
    print(f"\n{scenario}: {days} days, {len(sweeps)} rows, ramp on day {config.RAMP_DAY[scenario]}")
    print(f"  {'joint':>5s} {'wear at end':>11s} {'service day':>11s} {'day by the plan':>15s} {'index at end':>12s} "
          f"{'index error, raw':>16s} {'temperature taken out':>21s} {'temp C, low to high':>19s}")
    fig, axes = plt.subplots(2, 3, figsize=(12, 6.5), sharex=True, sharey=True)
    reached = 0
    for joint, ax in zip(range(config.N_JOINTS), axes.ravel()):
        rows = truth[truth["joint"] == joint].sort_values("day")
        wear = rows["wear"].to_numpy()
        service = rows["service_day"].iloc[0]
        reached += pd.notna(service)
        fc, temp = coulomb_by_day(sweeps, joint)
        raw = index(fc)
        cooled = index(fc / (1 - config.TEMP_COEF * (temp - config.TEMP_REF_C)))
        # the reference is the first week, when wear is already a little above 0: compare from the same start
        start = wear[:BASELINE_DAYS].mean()
        expected = ((1 + config.WEAR_GAIN_FC * wear) / (1 + config.WEAR_GAIN_FC * start) - 1) / config.WEAR_GAIN_FC
        print(f"  {joint:5d} {wear[-1]:11.3f} {'-' if pd.isna(service) else int(service):>11} "
              f"{planned_service_day(scenario, joint):15d} {raw[-1]:12.3f} {np.abs(raw - expected).mean():16.4f} "
              f"{np.abs(cooled - expected).mean():21.4f} {temp.min():9.1f} to {temp.max():.1f}")

        ax.plot(raw, color="tab:gray", linewidth=0.6, label="health index from the sweeps, raw")
        ax.plot(cooled, color="tab:blue", linewidth=0.8, label="same, temperature taken out")
        ax.plot(wear, color="black", linewidth=1.2, label="hidden wear (ground truth)")
        ax.axhline(config.FAIL_W, color="tab:red", linewidth=0.8, linestyle="--", label=f"service threshold {config.FAIL_W}")
        if config.RAMP_DAY[scenario] < days:
            ax.axvline(config.RAMP_DAY[scenario], color="tab:orange", linewidth=0.8, linestyle=":", label="duty doubles")
        ax.set_title(f"joint {joint}" + ("" if pd.isna(service) else f": service on day {int(service)}"), fontsize=9)
    print(f"  joints that reach the service threshold within the run: {reached} of {config.N_JOINTS}")
    for ax in axes[1]:
        ax.set_xlabel("day")
    for ax in axes[:, 0]:
        ax.set_ylabel("wear / health index")
    axes[0, 0].legend(fontsize=7, loc="lower right")
    fig.suptitle(f"Simulated robot, scenario {scenario}, seed 0 (simulation: the wear is injected by hand)", fontsize=10)
    fig.tight_layout()
    path = os.path.join("results", "robot", f"life_{scenario}.png")
    fig.savefig(path, dpi=130)
    print(f"  plot: {path}")


def main():
    print("Health index = (Fc / mean Fc of the joint's first 7 days - 1) / 1.5. 'Index error' is the mean absolute")
    print("difference from the index that the true wear would give, over all days.")
    for scenario in sorted(config.RAMP_DAY):
        report(scenario)

    print("\nHow long must a run be for every joint to reach the service threshold? (plan only, no noise)")
    for scenario in sorted(config.RAMP_DAY):
        last = max(planned_service_day(scenario, j) for j in range(config.N_JOINTS))
        first = min(planned_service_day(scenario, j) for j in range(config.N_JOINTS))
        print(f"  {scenario:11s} first joint on day {first}, last joint on day {last}: "
              f"a run of {last + 50} days takes {(last + 50) * 1.5 / 60:.0f} minutes")


if __name__ == "__main__":
    main()
