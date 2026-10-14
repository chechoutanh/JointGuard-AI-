"""The health check: sweep one joint at constant speeds and read its friction torque."""

import pybullet as p

from robot import config
from robot.friction import friction
from robot.world import gravity_torque, hold, joint_inertia, joint_states, release


def start_angle(joint, v_target):
    """Angle the swept joint starts from, so that its travel is centred on the posture and stays clear of the limits."""
    travel = v_target * (config.SETTLE_S + config.RECORD_S)
    return config.POSTURE[joint] - 0.5 * travel


def run_health_check(world, joint, wear, temperature_c, rng, on_step=None):
    """One sweep of one joint: a row per speed point.

    wear and temperature_c hold one value per joint. This is the only function
    that reads wear: it stands in for the physical joint, and what it returns
    is what a sensor would see. rng adds the sensor noise. on_step(world), if
    given, is called after every time step: for watching the sweep, drawing
    it or slowing it down. It cannot change what is measured.
    """
    others = [j for j in world.joints if j != joint]
    hold(world, others)
    release(world, joint)
    # the swept joint's own inertia does not change along its travel, so once is enough
    gain = config.VELOCITY_GAIN * joint_inertia(world, config.POSTURE, joint)
    n_settle = round(config.SETTLE_S / config.TIMESTEP)
    n_record = round(config.RECORD_S / config.TIMESTEP)

    rows = []
    for frac in config.SPEED_FRACS:
        v_target = float(frac * config.RATED_RAD_S[joint])
        # every speed point starts from the same state, so no point depends on the one before
        for j in others:
            p.resetJointState(world.robot, j, config.POSTURE[j], 0.0, physicsClientId=world.client)
        p.resetJointState(world.robot, joint, start_angle(joint, v_target), v_target, physicsClientId=world.client)

        torque_sum = speed_sum = 0.0
        for step in range(n_settle + n_record):
            q, v = joint_states(world)
            tau_gravity = gravity_torque(world, q)[joint]                   # at the angle of this step
            tau_command = tau_gravity + gain * (v_target - v[joint])        # speed loop, proportional only
            tau_friction = friction(v[joint], wear[joint], temperature_c[joint], joint)
            p.setJointMotorControl2(world.robot, joint, p.TORQUE_CONTROL, force=float(tau_command - tau_friction),
                                    physicsClientId=world.client)
            p.stepSimulation(physicsClientId=world.client)
            if on_step:
                on_step(world)
            if step >= n_settle:
                torque_sum += tau_command - tau_gravity                     # what the motor adds beyond gravity
                speed_sum += v[joint]

        noise = rng.normal(0.0, config.NOISE_NM * config.JOINT_SIZE[joint])
        rows.append({
            "joint": joint,
            "v_target": v_target,
            "v_measured": float(speed_sum / n_record),
            "friction_torque": float(torque_sum / n_record + noise),
            "temperature_c": float(temperature_c[joint]),
            "posture_q": list(config.POSTURE),
        })
    return rows


def sensor_faults(rows, rng):
    """What an imperfect torque sensor makes of one sweep: sometimes nothing, sometimes a wild reading, always rounded."""
    if rng.random() < config.MISSED_SWEEP_SHARE:
        return []
    size = config.JOINT_SIZE[rows[0]["joint"]]
    step = config.QUANT_NM * size
    out = []
    for row in rows:
        torque = row["friction_torque"]
        if rng.random() < config.OUTLIER_SHARE:
            torque += rng.choice([-1.0, 1.0]) * config.OUTLIER_NM * size
        out.append({**row, "friction_torque": float(round(torque / step) * step)})
    return out
