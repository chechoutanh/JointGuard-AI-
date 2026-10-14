"""Can the health-check sweep of ROBOT_SIM_DATA_SPEC.md run in plain PyBullet, without the old simulator?

    python results/2026-10-07_sweep_feasibility/check.py     (from the project root, about 1 minute)

This is a feasibility check, not the robot/ package. It is one file, headless
(DIRECT mode), numpy and pybullet only. It answers four questions:

  A. With no friction injected, does the sweep read zero?
  B. With friction injected, does the fit recover it on all 7 joints, and
     which settings does that depend on?
  C. Does wear on one joint leave the other joints' health index at zero?
  D. How long does a sweep take?

Friction model, as in CLAUDE.md: (Fc (1 + gain * wear) + Stribeck bump) * tanh(v / eps) + Fv * v.
Controller: gravity + mass matrix @ (kp * position error + kd * velocity error).
The "rated speed" is an assumption (1.5 rad/s): the URDF says 10 rad/s for every joint.
"""

import time

import numpy as np
import pybullet as p
import pybullet_data

DT = 1 / 1000
RATED_SPEED = 1.5                 # rad/s
GRID = np.concatenate([-np.geomspace(0.08, 0.80, 9)[::-1], np.geomspace(0.08, 0.80, 9)]) * RATED_SPEED
SETTLE, RECORD = 0.3, 0.2         # seconds held at each velocity: discarded, then averaged
POSTURE = np.array([0.0, 0.5, 0.0, -1.2, 0.0, 0.8, 0.0])
STRIBECK_SPEED, WEAR_GAIN = 0.05, 1.0
OMEGA = 60.0                      # controller: kp = OMEGA^2, kd = 2 OMEGA, both times the mass matrix


def setup(zero_damping=True):
    p.resetSimulation()
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setGravity(0, 0, -9.81)
    p.setTimeStep(DT)
    robot = p.loadURDF("kuka_iiwa/model.urdf", useFixedBase=True)
    joints = list(range(p.getNumJoints(robot)))
    for j in joints:
        p.setJointMotorControl2(robot, j, p.VELOCITY_CONTROL, force=0)   # switch off the hidden motor
        if zero_damping:
            # the URDF gives every joint damping 0.5, which the sweep would read as friction
            p.changeDynamics(robot, j, jointDamping=0.0, linearDamping=0.0, angularDamping=0.0)
    return robot, joints


def sweep(target, fc0, fv0, eps=0.03, full_matrix=True, wear=None, zero_damping=True):
    """Fitted Fc and Fv of the target joint, and the fastest any held joint moved."""
    robot, joints = setup(zero_damping)
    n = len(joints)
    wear = np.zeros(n) if wear is None else wear
    held = [j for j in joints if j != target]
    readings, fastest_held = [], 0.0
    for v in GRID:
        start = POSTURE[target] - v * (SETTLE + RECORD) / 2            # travel centred on the posture
        for j in joints:
            p.resetJointState(robot, j, POSTURE[j] if j != target else start, v if j == target else 0.0)
        samples = []
        for k in range(int((SETTLE + RECORD) / DT)):
            state = p.getJointStates(robot, joints)
            q = np.array([s[0] for s in state])
            qd = np.array([s[1] for s in state])
            q_ref, qd_ref = POSTURE.copy(), np.zeros(n)
            q_ref[target], qd_ref[target] = start + v * k * DT, v
            mass = np.array(p.calculateMassMatrix(robot, q.tolist()))
            gravity = np.array(p.calculateInverseDynamics(robot, q.tolist(), [0.0] * n, [0.0] * n))
            accel = OMEGA ** 2 * (q_ref - q) + 2 * OMEGA * (qd_ref - qd)
            commanded = gravity + (mass @ accel if full_matrix else np.diag(mass) * accel)
            fc = fc0 * (1 + WEAR_GAIN * wear)
            friction = (fc + 0.25 * fc0 * np.exp(-(qd / STRIBECK_SPEED) ** 2)) * np.tanh(qd / eps) + fv0 * qd
            p.setJointMotorControlArray(robot, joints, p.TORQUE_CONTROL, forces=(commanded - friction).tolist())
            p.stepSimulation()
            if k * DT >= SETTLE:
                samples.append(commanded[target] - gravity[target])
                fastest_held = max(fastest_held, np.abs(qd[held]).max())
        readings.append(np.mean(samples))
    design = np.column_stack([np.sign(GRID), GRID])
    (fc_fit, fv_fit), *_ = np.linalg.lstsq(design, np.array(readings), rcond=None)
    return fc_fit, fv_fit, fastest_held


def main():
    p.connect(p.DIRECT)
    robot, _ = setup()
    inertia = np.diag(np.array(p.calculateMassMatrix(robot, POSTURE.tolist())))
    print("joint inertia at the test posture (kg m^2):", " ".join(f"{m:.4f}" for m in inertia))
    print(f"largest over smallest: {inertia.max() / inertia.min():.0f}x")

    zero = np.zeros(7)
    print("\nA. no friction injected: what the sweep of joint 3 reads (should be 0)")
    for zero_damping in (False, True):
        fc, fv, _ = sweep(3, zero, zero, zero_damping=zero_damping)
        print(f"   URDF damping {'set to 0     ' if zero_damping else 'left as loaded'}: Fc {fc:+.4f} N m, Fv {fv:+.4f} N m s/rad")

    print("\nB. friction injected: worst error of the fitted Fc over the 7 joints")
    scaled = (5 * inertia, 2.5 * inertia)
    same = (np.full(7, 2.0), np.full(7, 1.0))
    cases = [
        ("friction scaled by joint inertia, full mass matrix", scaled, True),
        ("friction scaled by joint inertia, diagonal gains only", scaled, False),
        ("same friction on every joint (Fc 2), full mass matrix", same, True),
    ]
    for label, (fc0, fv0), full_matrix in cases:
        errors, held = [], []
        for target in range(7):
            fc, _, fastest = sweep(target, fc0, fv0, full_matrix=full_matrix)
            errors.append(abs(fc / fc0[target] - 1))
            held.append(fastest)
        print(f"   {label:55s} worst error {max(errors):7.1%}, joints within 2%: {sum(e < 0.02 for e in errors)}/7, "
              f"held joints move up to {max(held):6.2f} rad/s")

    print("\nC. wear 0.5 on joint 3 only: health index of each joint (should be 0.5 for joint 3, 0 elsewhere)")
    wear = np.zeros(7)
    wear[3] = 0.5
    started = time.time()
    for target in range(7):
        baseline, _, _ = sweep(target, *scaled)
        worn, _, _ = sweep(target, *scaled, wear=wear)
        print(f"   joint {target}: {(worn / baseline - 1) / WEAR_GAIN:+.4f}")
    per_sweep = (time.time() - started) / 14

    print(f"\nD. {per_sweep:.2f} s of computer time per sweep ({len(GRID)} velocities, {int((SETTLE + RECORD) / DT) * len(GRID)} steps)")
    print(f"   7 joints x 365 days: {7 * 365 * per_sweep / 60:.0f} minutes")
    print(f"   largest joint travel in one velocity step: {abs(GRID).max() * (SETTLE + RECORD):.2f} rad (limits are 2.09 rad or more)")


if __name__ == "__main__":
    main()
