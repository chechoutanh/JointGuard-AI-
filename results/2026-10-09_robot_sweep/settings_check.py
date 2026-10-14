"""Which settings does the health-check sweep need? The build brief (sim.md) as written, then one change at a time.

    python results/2026-10-09_robot_sweep/settings_check.py     (from the project root, about 1 minute)

Stands alone: numpy and pybullet only, nothing imported from robot/, so it
keeps showing what was compared even when the package changes. No noise.
Every case injects a known friction on joints 0 to 5, sweeps each of them, and
fits Coulomb friction (Fc) and viscous friction (Fv) back.

What is varied:
  friction   "same": 1.80 N m on every joint (the brief's default)
             "sized": 1.80 N m on joint 3, other joints in proportion to their inertia
  hold       how the 6 joints that are not being swept are kept still
             "diagonal": torque from a PD law, gains times the mass-matrix diagonal (the brief)
             "full":     the same PD law times the whole mass matrix
             "locked":   the engine's own position motor
  rate       gain of the swept joint's speed loop, 1/s
  damping    whether the robot file's own joint damping (0.5) is left in
  grid       lowest target speed, as a share of rated speed

Everything here is simulation: the script injects the friction it then measures.
"""

import numpy as np
import pybullet as p
import pybullet_data

DT = 1 / 1000
FC0, FS0, FV0 = 1.80, 2.90, 0.55
VS, DELTA, EPS = 0.05, 1.5, 0.01
WEAR_GAIN_FC, WEAR_GAIN_FS = 1.5, 1.2
SETTLE_S, RECORD_S = 0.5, 0.5
FIT_MIN_FRAC = 0.08
POSTURE = np.array([0.0, 0.5, 0.0, -1.2, 0.0, 0.8, 0.0])
RATED = np.array([1.5, 1.5, 1.7, 1.3, 2.3, 2.3, 2.3])
N_SWEPT = 6
HOLD_KP, HOLD_KD = 3600.0, 120.0          # PD holds: per unit of inertia (60 rad/s, critically damped)
HOLD_FORCE = 300.0                        # locked holds: N m


def grid(lowest):
    return np.concatenate([-np.geomspace(lowest, 0.8, 9)[::-1], np.geomspace(lowest, 0.8, 9)])


def friction(v, size, wear=0.0, warmth=1.0):
    fc = FC0 * (1 + WEAR_GAIN_FC * wear)
    fs = FS0 * (1 + WEAR_GAIN_FS * wear)
    return size * warmth * ((fc + (fs - fc) * np.exp(-np.abs(v / VS) ** DELTA)) * np.tanh(v / EPS) + FV0 * v)


def load(zero_damping):
    p.resetSimulation()
    p.setGravity(0, 0, -9.81)
    p.setTimeStep(DT)
    robot = p.loadURDF(pybullet_data.getDataPath() + "/kuka_iiwa/model.urdf", useFixedBase=True)
    joints = list(range(p.getNumJoints(robot)))
    for j in joints:
        p.setJointMotorControl2(robot, j, p.VELOCITY_CONTROL, force=0)
        if zero_damping:
            p.changeDynamics(robot, j, jointDamping=0.0, linearDamping=0.0, angularDamping=0.0)
    return robot, joints


def sweep(target, size, hold, rate, zero_damping=True, lowest=0.08, wear=0.0, warmth=1.0):
    """Rows of (target speed, measured speed, torque beyond gravity), and the fastest any held joint moved."""
    robot, joints = load(zero_damping)
    n = len(joints)
    held = [j for j in joints if j != target]
    has_friction = np.arange(n) < N_SWEPT
    rows, fastest_held = [], 0.0
    for frac in grid(lowest):
        v_target = frac * RATED[target]
        start = POSTURE[target] - 0.5 * v_target * (SETTLE_S + RECORD_S)
        for j in joints:
            p.resetJointState(robot, j, start if j == target else POSTURE[j], v_target if j == target else 0.0)
        if hold == "locked":
            p.setJointMotorControlArray(robot, held, p.POSITION_CONTROL, targetPositions=POSTURE[held].tolist(),
                                        forces=[HOLD_FORCE] * len(held))
        torque, speed = [], []
        for k in range(round((SETTLE_S + RECORD_S) / DT)):
            state = p.getJointStates(robot, joints)
            q = np.array([s[0] for s in state])
            v = np.array([s[1] for s in state])
            mass = np.array(p.calculateMassMatrix(robot, q.tolist()))
            gravity = np.array(p.calculateInverseDynamics(robot, q.tolist(), [0.0] * n, [0.0] * n))
            accel = HOLD_KP * (POSTURE - q) - HOLD_KD * v                 # held joints: PD
            accel[target] = rate * (v_target - v[target])                # swept joint: speed loop
            command = gravity + (mass @ accel if hold == "full" else np.diag(mass) * accel)
            applied = command - np.where(has_friction, friction(v, size, wear, warmth), 0.0)
            if hold == "locked":
                p.setJointMotorControl2(robot, target, p.TORQUE_CONTROL, force=float(applied[target]))
            else:
                p.setJointMotorControlArray(robot, joints, p.TORQUE_CONTROL, forces=applied.tolist())
            p.stepSimulation()
            if k * DT >= SETTLE_S:
                torque.append(command[target] - gravity[target])
                speed.append(v[target])
                fastest_held = max(fastest_held, np.abs(v[held]).max())
        rows.append((v_target, np.mean(speed), np.mean(torque)))
    return np.array(rows), fastest_held


def fit(v, tau, rated):
    keep = np.abs(v) >= FIT_MIN_FRAC * rated
    if keep.sum() < 2:
        return np.nan, np.nan, int(keep.sum())
    (fc, fv), *_ = np.linalg.lstsq(np.column_stack([np.sign(v[keep]), v[keep]]), tau[keep], rcond=None)
    return fc, fv, int(keep.sum())


def case(label, size, hold, rate, **settings):
    fc_errors, fv_errors, lags, held_speeds, points = [], [], [], [], []
    for target in range(N_SWEPT):
        rows, fastest = sweep(target, size, hold, rate, **settings)
        fc, fv, used = fit(rows[:, 1], rows[:, 2], RATED[target])
        fc_errors.append(abs(fc / (FC0 * size[target]) - 1) if used >= 2 else np.inf)
        fv_errors.append(abs(fv / (FV0 * size[target]) - 1) if used >= 2 else np.inf)
        lags.append(np.max(1 - rows[:, 1] / rows[:, 0]))
        held_speeds.append(fastest)
        points.append(used)
    good = sum(e < 0.05 for e in fc_errors)
    print(f"  {label:48s} {good} of {N_SWEPT} {min(max(fc_errors), 99.99):9.1%} {min(max(fv_errors), 99.99):9.1%} "
          f"{min(max(lags), 9.99):8.1%} {max(held_speeds):10.4f} {min(points):6d} to {max(points)}")


def main():
    p.connect(p.DIRECT)
    robot, joints = load(True)
    inertia = np.diag(np.array(p.calculateMassMatrix(robot, POSTURE.tolist())))
    same, sized = np.ones(7), inertia / inertia[3]
    print("joint inertia at the posture (kg m^2):", " ".join(f"{x:.4f}" for x in inertia))
    print("relative to joint 3                  :", " ".join(f"{x:.4f}" for x in sized))

    print("\nA. Fitted friction against injected friction, joints 0 to 5 (worst joint of each case)")
    print(f"  {'friction, hold, loop rate':48s} {'Fc ok':>6s} {'Fc error':>9s} {'Fv error':>9s} {'max lag':>8s} "
          f"{'held rad/s':>10s} {'points fitted':>13s}")
    case("same,  diagonal, 600 /s, damping left in (brief)", same, "diagonal", 600.0, zero_damping=False)
    case("same,  diagonal, 600 /s", same, "diagonal", 600.0)
    case("same,  diagonal, 120 /s", same, "diagonal", 120.0)
    case("sized, diagonal,  60 /s", sized, "diagonal", 60.0)
    case("sized, diagonal, 120 /s", sized, "diagonal", 120.0)
    case("sized, diagonal, 240 /s", sized, "diagonal", 240.0)
    case("sized, diagonal, 600 /s", sized, "diagonal", 600.0)
    case("sized, full,     600 /s", sized, "full", 600.0)
    case("same,  locked,   600 /s", same, "locked", 600.0)
    case("sized, locked,   600 /s", sized, "locked", 600.0)
    case("sized, locked,   600 /s, damping left in", sized, "locked", 600.0, zero_damping=False)
    case("sized, locked,   600 /s, grid from 0.10 (used)", sized, "locked", 600.0, lowest=0.10)

    print("\nB. No friction injected, sized/locked/600: largest torque read on any joint (should be 0)")
    worst = max(np.abs(sweep(t, 0.0 * sized, "locked", 600.0)[0][:, 2]).max() for t in range(N_SWEPT))
    print(f"  {worst:.2e} N m")

    print("\nC. Lowest target speed: how many of the 18 points the fit can use (joint 3, sized/locked/600)")
    print(f"  {'grid from':>9s} {'joint state':>24s} {'slowest measured / rated':>25s} {'points fitted':>14s}")
    for lowest in (0.08, 0.10):
        for label, wear, warmth in (("new, 35 C", 0.0, 1.0), ("wear 0.8, 35 C", 0.8, 1.0), ("wear 1.0, 15 C", 1.0, 1.16)):
            rows, _ = sweep(3, sized, "locked", 600.0, lowest=lowest, wear=wear, warmth=warmth)
            used = int((np.abs(rows[:, 1]) >= FIT_MIN_FRAC * RATED[3]).sum())
            print(f"  {lowest:9.2f} {label:>24s} {np.abs(rows[:, 1]).min() / RATED[3]:25.4f} {used:14d}")


if __name__ == "__main__":
    main()
