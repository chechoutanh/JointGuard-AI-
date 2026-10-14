"""Milestone M1 of the robot simulation: one correct sweep. Does the robot/ package read back the friction it injects?

    python results/2026-10-09_robot_sweep/run.py     (from the project root, about 15 s)

Writes results/robot/sweep_day0.png. Sensor noise is on, seed 0.

Everything here is simulation with illustrative parameters. The friction is
injected by the same package that then measures it, so the errors below check
the method's arithmetic. They are not an accuracy claim about any robot.
"""

import os
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.getcwd())

from robot import config
from robot.fit import fit_friction
from robot.friction import friction
from robot.sweep import run_health_check
from robot.world import connect, disconnect

PLOT = os.path.join("results", "robot", "sweep_day0.png")
REPEATS = 20


def columns(rows):
    return np.array([r["v_measured"] for r in rows]), np.array([r["friction_torque"] for r in rows])


def fitted(rows):
    v, tau = columns(rows)
    return fit_friction(v, tau, config.RATED_RAD_S[rows[0]["joint"]])


def plot(new, worn, path):
    rated = config.RATED_RAD_S[3]
    speeds = np.linspace(-0.85 * rated, 0.85 * rated, 2001)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for rows, wear, colour, label in ((new, 0.0, "tab:blue", "day 0, new"), (worn, config.FAIL_W, "tab:red", f"wear {config.FAIL_W}")):
        v, tau = columns(rows)
        fc, fv = fitted(rows)
        ax.plot(speeds, friction(speeds, wear, config.TEMP_REF_C, 3), color=colour, linewidth=0.8, alpha=0.6)
        ax.plot(v, tau, "o", color=colour, markersize=4, label=f"{label}: fitted Fc {fc:.2f}, Fv {fv:.2f}")
    ax.axhline(0, color="black", linewidth=0.5)
    ax.axvline(0, color="black", linewidth=0.5)
    ax.set_xlabel("measured joint speed (rad/s)")
    ax.set_ylabel("friction torque (N m)")
    ax.set_title("Health-check sweep of joint 3 (simulation)\ndots: what the sweep reads; lines: the friction that was injected")
    ax.legend(loc="lower right", fontsize=8, title="Fc in N m, Fv in N m s/rad", title_fontsize=8)
    fig.tight_layout()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=150)


def main(seed=0):
    rng = np.random.default_rng(seed)
    world = connect()
    n = config.N_JOINTS
    new, warm = np.zeros(n), np.full(n, config.TEMP_REF_C)
    worn = np.full(n, config.FAIL_W)

    print(f"A. Every joint, new and at wear {config.FAIL_W} (18 speeds, noise on)")
    print(f"  {'joint':>5s} {'Fc injected':>11s} {'Fc day 0':>9s} {'error':>7s} {'Fv injected':>11s} {'Fv day 0':>9s} {'error':>7s} "
          f"{'Fc worn':>8s} {'health index':>12s} {'lag new':>8s} {'lag worn':>8s}")
    started = time.time()
    sweeps = {}
    for joint in range(n):
        sweeps[joint] = (run_health_check(world, joint, new, warm, rng), run_health_check(world, joint, worn, warm, rng))
    seconds = (time.time() - started) / (2 * n)
    for joint, (rows_new, rows_worn) in sweeps.items():
        size = config.JOINT_SIZE[joint]
        fc, fv = fitted(rows_new)
        fc_worn, _ = fitted(rows_worn)
        index = (fc_worn / fc - 1) / config.WEAR_GAIN_FC
        lag_new = max(1 - r["v_measured"] / r["v_target"] for r in rows_new)
        lag_worn = max(1 - r["v_measured"] / r["v_target"] for r in rows_worn)
        print(f"  {joint:5d} {config.FC0 * size:11.4f} {fc:9.4f} {fc / (config.FC0 * size) - 1:+7.1%} {config.FV0 * size:11.4f} {fv:9.4f} "
              f"{fv / (config.FV0 * size) - 1:+7.1%} {fc_worn:8.4f} {index:12.3f} {lag_new:8.1%} {lag_worn:8.1%}")

    print(f"\nB. Joint 3 swept {REPEATS} times with different noise (baseline: the mean Fc of {REPEATS} sweeps of the new joint)")
    print(f"  {'wear':>5s} {'health index, mean':>18s} {'spread (sd)':>11s} {'lowest':>7s} {'highest':>8s}")
    baseline = np.mean([fitted(run_health_check(world, 3, new, warm, rng))[0] for _ in range(REPEATS)])
    for level in (0.0, 0.4, config.FAIL_W):
        wear = np.full(n, level)
        index = np.array([(fitted(run_health_check(world, 3, wear, warm, rng))[0] / baseline - 1) / config.WEAR_GAIN_FC
                          for _ in range(REPEATS)])
        print(f"  {level:5.1f} {index.mean():18.4f} {index.std(ddof=1):11.4f} {index.min():7.3f} {index.max():8.3f}")

    print("\nC. Time")
    steps = len(config.SPEED_FRACS) * round((config.SETTLE_S + config.RECORD_S) / config.TIMESTEP)
    print(f"  {seconds:.2f} s per sweep ({steps} time steps); one day of {n} joints: {n * seconds:.1f} s; "
          f"400 days x 5 runs: {400 * 5 * n * seconds / 60:.0f} minutes")

    plot(*sweeps[3], PLOT)
    print(f"\nplot: {PLOT}")
    disconnect(world)


if __name__ == "__main__":
    main()
