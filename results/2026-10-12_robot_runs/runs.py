"""Milestone M3 of the robot simulation: many runs. Does every joint of every run reach service, and how do runs differ?

    python -m tools.robot demo --scenario ramp_early --days 850 --seed 0 --runs 5      (about 25 minutes)
    python -m tools.robot demo --scenario ramp_late --days 1450 --seed 0 --runs 5      (about 40 minutes)
    python results/2026-10-12_robot_runs/runs.py                                       (from the project root, under a minute)

Reads data/simulation/<scenario>/run_<k>/ and writes results/robot/runs_<scenario>.png.

This script checks the simulator, so it reads ground_truth.csv. A model must
not. The health index is the plain one of CLAUDE.md, (Fc / mean Fc of the
joint's first 7 days - 1) / 1.5, with the temperature effect taken out using
the true coefficient. Nothing is trained.

Everything here is simulation with illustrative parameters.
"""

import glob
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

BASELINE_DAYS = 7
N, SPEEDS = config.N_JOINTS, len(config.SPEED_FRACS)


def load(folder):
    """One run as arrays: sweeps by (day, joint, speed), wear by (day, joint), service day by joint, work done by day."""
    sweeps = pd.read_parquet(os.path.join(folder, "sweeps.parquet"))
    truth = pd.read_csv(os.path.join(folder, "ground_truth.csv"))
    work = pd.read_csv(os.path.join(folder, "actual_duty.csv"))["duty_actual"].to_numpy()
    days = len(work)
    shape = (days, N, SPEEDS)                                     # the file is written day by day, joint by joint
    assert sweeps["joint"].to_numpy().reshape(shape)[0, :, 0].tolist() == list(range(N))
    run = {name: sweeps[name].to_numpy().reshape(shape) for name in ("v_measured", "friction_torque", "temperature_c")}
    run["wear"] = truth["wear"].to_numpy().reshape(days, N)
    run["service_day"] = truth["service_day"].to_numpy().reshape(days, N)[0]
    run["work"] = work
    run["sweeps"] = sweeps
    return run


def index_and_points(run):
    """Health index by (day, joint), temperature taken out, and the number of speed points each fit could use."""
    days = len(run["work"])
    fc, points = np.empty((days, N)), np.empty((days, N), dtype=int)
    for joint in range(N):
        rated = config.RATED_RAD_S[joint]
        for day in range(days):
            v, tau = run["v_measured"][day, joint], run["friction_torque"][day, joint]
            fc[day, joint] = fit_friction(v, tau, rated)[0]
            points[day, joint] = (np.abs(v) >= config.FIT_MIN_FRAC * rated).sum()
    fc = fc / (1 - config.TEMP_COEF * (run["temperature_c"][:, :, 0] - config.TEMP_REF_C))
    return (fc / fc[:BASELINE_DAYS].mean(axis=0) - 1) / config.WEAR_GAIN_FC, points


def report(scenario):
    folders = sorted(glob.glob(os.path.join(config.SIMULATION_DIR, scenario, "run_*")), key=lambda f: int(f.rsplit("_", 1)[1]))
    runs = [load(folder) for folder in folders]
    days = len(runs[0]["work"])
    rows = sum(len(run["sweeps"]) for run in runs)
    size = sum(os.path.getsize(os.path.join(f, "sweeps.parquet")) for f in folders) / 1e6
    print(f"\n{scenario}: {len(runs)} runs of {days} days, {rows} sweep rows, {size:.1f} MB of sweeps.parquet")

    print("  each joint's wear rate in each run, as a multiple of its nominal rate (from ground truth and work done)")
    print(f"  {'run':>5s} " + " ".join(f"{'joint ' + str(j):>8s}" for j in range(N)))
    for k, run in enumerate(runs):
        factor = run["wear"][-1] / (config.K_WEAR * config.RATE * run["work"].sum())
        print(f"  {k:5d} " + " ".join(f"{x:8.2f}" for x in factor))

    print("  service day of each joint in each run (first day the true wear is at or past the threshold)")
    print(f"  {'run':>5s} " + " ".join(f"{'joint ' + str(j):>8s}" for j in range(N)) + f" {'wear at end, highest':>21s}")
    service = np.array([run["service_day"] for run in runs])
    for k, run in enumerate(runs):
        print(f"  {k:5d} " + " ".join(f"{'-' if np.isnan(d) else int(d):>8}" for d in service[k]) + f" {run['wear'][-1].max():21.2f}")
    reached = int((~np.isnan(service)).sum())
    print(f"  {'range':>5s} " + " ".join(f"{int(np.nanmax(service[:, j]) - np.nanmin(service[:, j])):>8d}" for j in range(N))
          + "   (latest minus earliest, days)")
    print(f"  joint trajectories with a service day: {reached} of {service.size}; latest service day {int(np.nanmax(service))}, "
          f"{days - int(np.nanmax(service))} days before the end of the run")

    errors, fewest_before, fewest_after = [], SPEEDS, SPEEDS
    for run in runs:
        index, points = index_and_points(run)
        start = run["wear"][:BASELINE_DAYS].mean(axis=0)
        expected = ((1 + config.WEAR_GAIN_FC * run["wear"]) / (1 + config.WEAR_GAIN_FC * start) - 1) / config.WEAR_GAIN_FC
        for joint in range(N):
            end = days if np.isnan(run["service_day"][joint]) else int(run["service_day"][joint]) + 1
            errors.append(np.abs(index[:end, joint] - expected[:end, joint]).mean())
            fewest_before = min(fewest_before, points[:end, joint].min())
            fewest_after = min(fewest_after, points[:, joint].min())
    print(f"  health index against true wear, up to each joint's service day: mean error {np.mean(errors):.4f}, "
          f"worst trajectory {np.max(errors):.4f}")
    print(f"  fewest of the 18 speed points the fit could use: {fewest_before} up to the service day, {fewest_after} over the whole run")

    fig, axes = plt.subplots(2, 3, figsize=(12, 6.5), sharex=True, sharey=True)
    for joint, ax in zip(range(N), axes.ravel()):
        for k, run in enumerate(runs):
            ax.plot(run["wear"][:, joint], linewidth=1.0, label=f"run {k}")
            if not np.isnan(service[k, joint]):
                ax.plot(service[k, joint], config.FAIL_W, "o", color=ax.lines[-1].get_color(), markersize=3)
        ax.axhline(config.FAIL_W, color="black", linewidth=0.7, linestyle="--")
        if config.RAMP_DAY[scenario] < days:
            ax.axvline(config.RAMP_DAY[scenario], color="tab:gray", linewidth=0.8, linestyle=":")
        ax.set_ylim(0, 1.6)
        ax.set_title(f"joint {joint}", fontsize=9)
    for ax in axes[1]:
        ax.set_xlabel("day")
    for ax in axes[:, 0]:
        ax.set_ylabel("hidden wear (ground truth)")
    axes[0, 0].legend(fontsize=7, loc="lower right")
    fig.suptitle(f"Simulated robot, scenario {scenario}: true wear of each joint in 5 runs. Dashed: service threshold. "
                 f"Dots: service day.\n(simulation: the wear is injected by hand)", fontsize=10)
    fig.tight_layout()
    path = os.path.join("results", "robot", f"runs_{scenario}.png")
    fig.savefig(path, dpi=130)
    print(f"  plot: {path}")
    return runs


def main():
    runs = {scenario: report(scenario) for scenario in sorted(config.RAMP_DAY)}

    print("\nAre run k of the two scenarios the same robot? (same seed: same wear rates, same work until the duty doubles)")
    ramp = config.RAMP_DAY["ramp_early"]
    for k, (early, late) in enumerate(zip(runs["ramp_early"], runs["ramp_late"])):
        before = np.array_equal(early["friction_torque"][:ramp], late["friction_torque"][:ramp])
        after = np.array_equal(early["friction_torque"][ramp:ramp + 50], late["friction_torque"][ramp:ramp + 50])
        print(f"  run {k}: sweeps identical on days 0 to {ramp - 1}: {before}; on days {ramp} to {ramp + 49}: {after}")


if __name__ == "__main__":
    main()
