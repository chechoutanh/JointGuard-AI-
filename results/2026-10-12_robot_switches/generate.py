"""Milestone M4: make the early-ramp dataset again with one realism switch on, to measure what the switch does.

    python results/2026-10-12_robot_switches/generate.py wear_noise        (from the project root, about 25 minutes each)
    ... wear_accel | wear_affects_fv | model_mismatch | sensor_faults | all

Five runs of 850 days, seeds 0 to 4: the same five robots as
data/simulation/ramp_early, which is the comparison with every switch off.
Written to data/switches/<name>/run_<k>/. The switch is turned on inside this
script only; robot/config.py keeps every switch off.

Everything here is simulation with illustrative parameters.
"""

import os
import sys
import time

sys.path.insert(0, os.getcwd())

from robot import config
from robot.simulate import simulate

SWITCHES = {
    "wear_noise": ["WEAR_NOISE"],
    "wear_accel": ["WEAR_ACCEL"],
    "wear_affects_fv": ["WEAR_AFFECTS_FV"],
    "model_mismatch": ["MODEL_MISMATCH"],
    "sensor_faults": ["SENSOR_FAULTS"],
    "all": ["WEAR_NOISE", "WEAR_ACCEL", "WEAR_AFFECTS_FV", "MODEL_MISMATCH", "SENSOR_FAULTS"],
}
SCENARIO, DAYS, RUNS = "ramp_early", 850, 5
OUT = os.path.join(os.path.dirname(config.SIMULATION_DIR), "switches")


def main(name):
    for flag in SWITCHES[name]:
        setattr(config, flag, True)
    print(f"simulation only: {SCENARIO}, {DAYS} days, {RUNS} runs, switched on: {', '.join(SWITCHES[name])}", flush=True)
    for k in range(RUNS):
        started = time.time()
        folder = simulate(SCENARIO, DAYS, k, os.path.join(OUT, name, f"run_{k}"))
        print(f"wrote {folder}  (seed {k}, {time.time() - started:.0f} s)", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
