"""One sweep of joint 3 with the noise switched off, to check by hand.

    python results/2026-10-09_robot_sweep/worked_example.py     (from the project root)

Joint 3 is the reference joint: Coulomb 1.80 N m, static 2.90 N m, viscous
0.55 N m s/rad, inertia 0.5256 kg m^2, rated speed 1.3 rad/s.
"""

import math
import os
import sys

import numpy as np

sys.path.insert(0, os.getcwd())

from robot import config
from robot.fit import fit_friction
from robot.friction import friction
from robot.sweep import run_health_check
from robot.world import connect, disconnect, joint_inertia

config.NOISE_NM = 0.0          # so every number below can be reproduced exactly
JOINT = 3


def by_hand(v, wear=0.0):
    """The friction law written out with plain numbers, for a positive speed of joint 3 at 35 C."""
    coulomb = 1.80 * (1 + 1.5 * wear)
    static = 2.90 * (1 + 1.2 * wear)
    bump = (static - coulomb) * math.exp(-((v / 0.05) ** 1.5))
    return (coulomb + bump) * math.tanh(v / 0.01) + 0.55 * v, bump


world = connect()
n = config.N_JOINTS
inertia = joint_inertia(world, config.POSTURE, JOINT)
rows = run_health_check(world, JOINT, np.zeros(n), np.full(n, 35.0), np.random.default_rng(0))
worn = run_health_check(world, JOINT, np.full(n, 0.8), np.full(n, 35.0), np.random.default_rng(0))
disconnect(world)

print("1. The friction law at three speeds (new joint): (1.80 + bump) * tanh(v / 0.01) + 0.55 * v")
print(f"   {'v rad/s':>8s} {'bump':>8s} {'tanh':>8s} {'0.55 v':>8s} {'by hand':>8s} {'robot.friction':>15s}")
for v in (0.05, 0.13, 1.00):
    value, bump = by_hand(v)
    print(f"   {v:8.2f} {bump:8.4f} {math.tanh(v / 0.01):8.4f} {0.55 * v:8.4f} {value:8.4f} {float(friction(v, 0.0, 35.0, JOINT)):15.4f}")

print(f"\n2. The sweep (new joint, no noise). Gain of the speed loop: 600 x inertia {inertia:.4f} = {600 * inertia:.2f} N m s/rad")
print(f"   {'target':>8s} {'measured':>9s} {'torque read':>12s} {'law at measured':>16s} {'difference':>11s} {'lag':>8s} {'torque / gain':>14s}")
for r in rows[9:]:
    law, _ = by_hand(r["v_measured"])
    lag = r["v_target"] - r["v_measured"]
    print(f"   {r['v_target']:8.4f} {r['v_measured']:9.4f} {r['friction_torque']:12.4f} {law:16.4f} "
          f"{r['friction_torque'] - law:+11.4f} {lag:8.4f} {r['friction_torque'] / (600 * inertia):14.4f}")
mirror = max(abs(a["friction_torque"] + b["friction_torque"]) for a, b in zip(rows[:9], rows[:8:-1]))
print(f"   the 9 negative speeds mirror these: largest |torque(v) + torque(-v)| = {mirror:.1e} N m")

a, b = rows[-2], rows[-1]
fv_hand = (b["friction_torque"] - a["friction_torque"]) / (b["v_measured"] - a["v_measured"])
fc_hand = a["friction_torque"] - fv_hand * a["v_measured"]
v = np.array([r["v_measured"] for r in rows])
tau = np.array([r["friction_torque"] for r in rows])
fc, fv = fit_friction(v, tau, config.RATED_RAD_S[JOINT])
print("\n3. The fit: torque = Fc + Fv * v for positive v")
print(f"   by hand from the two fastest points: Fv = ({b['friction_torque']:.4f} - {a['friction_torque']:.4f}) / "
      f"({b['v_measured']:.4f} - {a['v_measured']:.4f}) = {fv_hand:.4f}")
print(f"                                        Fc = {a['friction_torque']:.4f} - {fv_hand:.4f} * {a['v_measured']:.4f} = {fc_hand:.4f}")
print(f"   least squares on all 18 points:      Fc = {fc:.4f}, Fv = {fv:.4f}      (injected: 1.8000 and 0.5500)")

v_worn = np.array([r["v_measured"] for r in worn])
tau_worn = np.array([r["friction_torque"] for r in worn])
fc_worn, _ = fit_friction(v_worn, tau_worn, config.RATED_RAD_S[JOINT])
print("\n4. The same joint at wear 0.8")
print(f"   injected Coulomb friction: 1.80 * (1 + 1.5 * 0.8) = {1.80 * (1 + 1.5 * 0.8):.4f} N m; fitted: {fc_worn:.4f} N m")
print(f"   health index = (Fc worn / Fc new - 1) / 1.5 = ({fc_worn:.4f} / {fc:.4f} - 1) / 1.5 = {(fc_worn / fc - 1) / 1.5:.4f}      (injected wear: 0.8)")
