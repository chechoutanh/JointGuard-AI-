"""The simulated robot: write its dataset, or watch one health-check sweep live.

    python -m tools.robot demo [--scenario ramp_late] [--days 400] [--seed 0] [--runs 5]
    python -m tools.robot demo --gui [--joint 3] [--wear 0.5]

Without --gui it writes a dataset: one run to data/simulation/<scenario>/, or
with --runs N, N runs to data/simulation/<scenario>/run_0 ... run_<N-1> with
seeds seed, seed + 1, ... Each run is a different robot: its own work done,
sensor noise and wear rates.

With --gui it opens a PyBullet window, sweeps one joint whose wear is set by
hand, and prints the health index it reads back. Nothing is written.

Everything here is simulation with illustrative parameters: the wear is
injected by hand.
"""

import argparse
import os
import time

import numpy as np
import pandas as pd

from robot import config
from robot.fit import fit_friction
from robot.simulate import simulate
from robot.sweep import run_health_check
from robot.world import connect, disconnect, is_open, show_text


def parse(argv):
    parser = argparse.ArgumentParser(description="Simulated robot dataset, or one live sweep (simulation only).")
    parser.add_argument("command", choices=["demo"])
    parser.add_argument("--scenario", choices=sorted(config.RAMP_DAY), default="ramp_late")
    parser.add_argument("--days", type=int, default=400)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--runs", type=int, default=None, help="write this many runs, one folder each")
    parser.add_argument("--gui", action="store_true", help="show one live sweep in a window instead of writing a dataset")
    parser.add_argument("--joint", type=int, default=3, help="with --gui: the joint to sweep, 0 to 5")
    parser.add_argument("--wear", type=float, default=0.5, help="with --gui: the wear to give that joint (service is due at 0.8)")
    args = parser.parse_args(argv)
    if args.runs is not None and args.runs < 1:
        parser.error("--runs must be at least 1")
    if not 0 <= args.joint < config.N_JOINTS:
        parser.error(f"--joint must be 0 to {config.N_JOINTS - 1}")
    if args.wear < 0:
        parser.error("--wear cannot be negative")
    return args


def coulomb(rows):
    """Fitted Coulomb and viscous friction of one sweep."""
    v = [r["v_measured"] for r in rows]
    tau = [r["friction_torque"] for r in rows]
    return fit_friction(v, tau, config.RATED_RAD_S[rows[0]["joint"]])


def live_sweep(joint, wear, seed=0, gui=True, keep_open=True):
    """Sweep one joint whose wear is set by hand, in a window when gui is on, and print the health index read back."""
    rng = np.random.default_rng(seed)
    n = config.N_JOINTS
    warm = np.full(n, config.TEMP_REF_C)
    print(f"simulation only: live sweep of joint {joint}, with its wear set to {wear} by hand")

    # the joint's own baseline: a sweep of the new joint, out of sight
    world = connect()
    fc_new, _ = coulomb(run_health_check(world, joint, np.zeros(n), warm, rng))
    disconnect(world)

    world = connect(gui=gui)
    if gui:
        print(f"  shown {config.DEMO_SLOWDOWN} times slower than real time: 18 speeds, 9 each way")
    pause = config.DEMO_SLOWDOWN * config.TIMESTEP
    slow_motion = (lambda world: time.sleep(pause)) if gui else None
    fc, fv = coulomb(run_health_check(world, joint, np.full(n, float(wear)), warm, rng, on_step=slow_motion))
    index = (fc / fc_new - 1) / config.WEAR_GAIN_FC

    print(f"  new joint (its own baseline):  Fc {fc_new:.4f} N m")
    print(f"  this sweep:                    Fc {fc:.4f} N m, Fv {fv:.4f} N m s/rad")
    print(f"  health index = (Fc / Fc new - 1) / {config.WEAR_GAIN_FC} = {index:.2f}      service is due at {config.FAIL_W}")
    if gui and is_open(world):
        show_text(world, f"joint {joint}: health index {index:.2f} (service at {config.FAIL_W})")
        if keep_open:
            print("  close the window to end")
            while is_open(world):
                time.sleep(0.1)
    disconnect(world)
    return {"joint": joint, "fc_new": fc_new, "fc": fc, "fv": fv, "health_index": index}


def main(argv=None):
    args = parse(argv)
    if args.gui:
        live_sweep(args.joint, args.wear, args.seed, gui=True)
        return

    scenario_dir = os.path.join(config.SIMULATION_DIR, args.scenario)
    if args.runs is None:
        jobs = [(args.seed, scenario_dir)]
    else:
        jobs = [(args.seed + k, os.path.join(scenario_dir, f"run_{k}")) for k in range(args.runs)]
    print(f"simulation only: scenario {args.scenario}, {args.days} days, {len(jobs)} run(s) from seed {args.seed}")

    for seed, out_dir in jobs:
        started = time.time()
        simulate(args.scenario, args.days, seed, out_dir)
        rows = len(pd.read_parquet(os.path.join(out_dir, "sweeps.parquet")))
        print(f"wrote {out_dir}  (seed {seed}, {rows} rows, {time.time() - started:.0f} s)")

    print("in each folder:")
    print("  sweeps.parquet     one row per day, joint and speed. This is the dataset; it holds no wear")
    print("  schedule.csv       the planned duty of each day")
    print("  actual_duty.csv    the duty that really happened")
    print("  events.csv         maintenance events")
    print("  ground_truth.csv   the hidden wear and each joint's service day: the answer key, not for a model")


if __name__ == "__main__":
    main()
