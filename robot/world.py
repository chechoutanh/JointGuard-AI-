"""The PyBullet world: one KUKA iiwa arm on a fixed base, and the few calls the sweep needs."""

import os
from dataclasses import dataclass

import numpy as np
import pybullet as p
import pybullet_data

from robot import config


@dataclass
class World:
    client: int            # the PyBullet connection
    robot: int             # the arm's body id
    joints: list[int]      # every joint of the arm, base to flange
    lower: np.ndarray      # joint limits, rad
    upper: np.ndarray
    model_client: int      # where gravity and inertia are worked out: the same arm,
    model_robot: int       # unless the arm that moves was given other link masses


def load_arm(client):
    """Load the arm into one PyBullet connection, ready for torque control. Returns its body id and joints."""
    p.setGravity(0, 0, -config.GRAVITY, physicsClientId=client)
    p.setTimeStep(config.TIMESTEP, physicsClientId=client)
    urdf = os.path.join(pybullet_data.getDataPath(), "kuka_iiwa", "model.urdf")
    robot = p.loadURDF(urdf, useFixedBase=True, physicsClientId=client)
    joints = list(range(p.getNumJoints(robot, physicsClientId=client)))
    for j in joints:
        # Every joint loads with a hidden motor that holds it at speed 0 and fights any commanded torque.
        p.setJointMotorControl2(robot, j, p.VELOCITY_CONTROL, force=0, physicsClientId=client)
        # The robot file gives every joint a damping of 0.5, which the sweep would read as viscous friction.
        p.changeDynamics(robot, j, jointDamping=0.0, linearDamping=0.0, angularDamping=0.0, physicsClientId=client)
    return robot, joints


def connect(gui=False, mass_factors=None):
    """Start PyBullet (no window unless gui) and load the arm.

    mass_factors, one per link, makes the arm that moves heavier or lighter
    than the robot file says. The model that takes gravity out keeps the
    file's masses: it is a second, untouched copy of the arm.
    """
    client = p.connect(p.GUI if gui else p.DIRECT)
    if gui:
        p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0, physicsClientId=client)      # no side panels
        p.resetDebugVisualizerCamera(config.CAMERA_DISTANCE, config.CAMERA_YAW, config.CAMERA_PITCH, list(config.CAMERA_TARGET),
                                     physicsClientId=client)
    robot, joints = load_arm(client)
    model_client, model_robot = client, robot
    if mass_factors is not None:
        model_client = p.connect(p.DIRECT)
        model_robot, _ = load_arm(model_client)
        for link, factor in zip(joints, mass_factors):
            mass, _, inertia = p.getDynamicsInfo(robot, link, physicsClientId=client)[:3]
            p.changeDynamics(robot, link, mass=mass * factor, localInertiaDiagonal=[i * factor for i in inertia],
                             physicsClientId=client)
    info = [p.getJointInfo(robot, j, physicsClientId=client) for j in joints]
    return World(client, robot, joints, np.array([i[8] for i in info]), np.array([i[9] for i in info]), model_client, model_robot)


def disconnect(world):
    if is_open(world):                                            # a window may already have been closed by hand
        p.disconnect(physicsClientId=world.client)
    if world.model_client != world.client:
        p.disconnect(physicsClientId=world.model_client)


def is_open(world):
    return bool(p.isConnected(physicsClientId=world.client))


def show_text(world, text):
    """Write a line of text above the arm, in the window."""
    p.addUserDebugText(text, [0, 0, 0.85], textColorRGB=[0, 0, 0], textSize=1.6, physicsClientId=world.client)


def joint_states(world):
    """Angle (rad) and speed (rad/s) of every joint."""
    states = p.getJointStates(world.robot, world.joints, physicsClientId=world.client)
    return np.array([s[0] for s in states]), np.array([s[1] for s in states])


def gravity_torque(world, q):
    """Torque (N m) each joint needs to hold the arm still at angles q, according to the model."""
    zeros = [0.0] * len(world.joints)
    # plain lists: PyBullet does not take numpy arrays here
    return np.array(p.calculateInverseDynamics(world.model_robot, [float(x) for x in q], zeros, zeros,
                                               physicsClientId=world.model_client))


def joint_inertia(world, q, joint):
    """Inertia (kg m^2) one joint feels when the others are held: its entry on the mass-matrix diagonal."""
    mass = p.calculateMassMatrix(world.model_robot, [float(x) for x in q], physicsClientId=world.model_client)
    return mass[joint][joint]


def hold(world, joints):
    """Lock joints at the posture with the engine's position motor, as brakes would."""
    p.setJointMotorControlArray(world.robot, joints, p.POSITION_CONTROL,
                                targetPositions=[config.POSTURE[j] for j in joints],
                                forces=[config.HOLD_FORCE_NM] * len(joints), physicsClientId=world.client)


def release(world, joint):
    """Switch the engine's motor off on one joint, so that only the commanded torque moves it."""
    p.setJointMotorControl2(world.robot, joint, p.VELOCITY_CONTROL, force=0, physicsClientId=world.client)
