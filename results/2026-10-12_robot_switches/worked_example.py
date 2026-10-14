"""Three of the realism switches at points small enough to check by hand.

    python results/2026-10-12_robot_switches/worked_example.py     (from the project root, a few seconds)

The switches are turned on inside this script only.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.getcwd())

from robot import config
from robot.fit import fit_friction
from robot.simulate import wear_growth
from robot.sweep import run_health_check, sensor_faults
from robot.world import connect, disconnect, gravity_torque

config.NOISE_NM = 0.0
N = config.N_JOINTS
rng = np.random.default_rng(0)

print("1. WEAR_ACCEL: a day's wear is multiplied by 1 + 1.5 x (wear - 0.6) once the wear is past 0.6")
print("   one day of work 0.6 on a joint of rate 1: clean rule 1 x 0.6 / 480 = 0.001250")
config.WEAR_ACCEL = True
for wear in (0.5, 0.7, 0.8):
    factor = 1 + 1.5 * max(0.0, wear - 0.6)
    print(f"   wear so far {wear}: factor {factor:.2f}, by hand {0.00125 * factor:.6f}, wear_growth {wear_growth(np.array([wear]), np.ones(1), 0.6, rng)[0]:.6f}")
config.WEAR_ACCEL = False

print("\n2. MODEL_MISMATCH: every link 3% heavier than the model thinks. Joint 1, new, no noise.")
readings = {}
for label, factors in (("model is right", None), ("links 3% heavier", np.full(7, 1.03))):
    world = connect(mass_factors=factors)
    gravity = gravity_torque(world, config.POSTURE)[1]
    rows = run_health_check(world, 1, np.zeros(N), np.full(N, config.TEMP_REF_C), rng)
    disconnect(world)
    v = np.array([r["v_measured"] for r in rows])
    tau = np.array([r["friction_torque"] for r in rows])
    readings[label] = (tau, fit_friction(v, tau, config.RATED_RAD_S[1]))
print(f"   gravity on joint 1 by the model: {gravity:.2f} N m. The motor has to hold 3% more: 0.03 x {gravity:.2f} = {0.03 * gravity:.3f} N m")
print(f"   {'':18s} {'torque at -1.2 rad/s':>21s} {'at +1.2 rad/s':>14s} {'mean of all 18':>15s} {'fitted Fc':>10s} {'fitted Fv':>10s}")
for label, (tau, (fc, fv)) in readings.items():
    print(f"   {label:18s} {tau[0]:21.3f} {tau[-1]:14.3f} {tau.mean():15.3f} {fc:10.4f} {fv:10.4f}")
right, heavy = readings["model is right"], readings["links 3% heavier"]
print(f"   both directions move by about the same amount ({heavy[0][0] - right[0][0]:+.3f} and {heavy[0][-1] - right[0][-1]:+.3f} N m),")
print(f"   so the mean moves ({heavy[0].mean() - right[0].mean():+.3f}) and the fitted Fc hardly does ({heavy[1][0] / right[1][0] - 1:+.2%})")

print("\n3. SENSOR_FAULTS: every reading is rounded to 0.01 N m on joint 3")
config.MISSED_SWEEP_SHARE = config.OUTLIER_SHARE = 0.0
rows = [{"joint": 3, "friction_torque": t} for t in (1.8734, 1.9577, 2.1099)]
print("   " + ", ".join(f"{a['friction_torque']} -> {b['friction_torque']:.2f}" for a, b in zip(rows, sensor_faults(rows, rng))))
config.OUTLIER_SHARE = 1.0
print("   a wild reading is 0.2 N m off, either way: "
      + ", ".join(f"{a['friction_torque']} -> {b['friction_torque']:.2f}" for a, b in zip(rows, sensor_faults(rows, rng))))
