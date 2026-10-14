"""The PyBullet world as it comes out of connect(), before any sweep touches it."""

import numpy as np
import pybullet as p
import pytest

from robot import config
from robot.world import connect, disconnect, gravity_torque, joint_inertia, joint_states


@pytest.fixture()
def world():
    world = connect()
    yield world
    disconnect(world)


def push_joint_0(world, extra_nm, steps=100):
    """Hold the arm against gravity by torque alone, with extra torque on joint 0. Returns joint 0's speed."""
    for j in world.joints:
        p.resetJointState(world.robot, j, config.POSTURE[j], 0.0, physicsClientId=world.client)
    for _ in range(steps):
        q, _ = joint_states(world)
        tau = gravity_torque(world, q)
        tau[0] += extra_nm
        p.setJointMotorControlArray(world.robot, world.joints, p.TORQUE_CONTROL, forces=tau.tolist(), physicsClientId=world.client)
        p.stepSimulation(physicsClientId=world.client)
    return joint_states(world)[1][0]


def test_the_arm_has_seven_joints_with_limits(world):
    assert world.joints == [0, 1, 2, 3, 4, 5, 6]
    assert world.lower[1] == pytest.approx(-2.0944, abs=1e-3)
    assert world.upper[1] == pytest.approx(2.0944, abs=1e-3)


def test_a_freshly_loaded_arm_obeys_commanded_torque(world):
    # 1 N m on an inertia of about 0.27 kg m^2 for 0.1 s. PyBullet's hidden motors would hold the joint at speed 0.
    assert push_joint_0(world, 1.0) > 0.2


def test_gravity_torque_alone_holds_the_arm_still(world):
    assert abs(push_joint_0(world, 0.0)) < 1e-6
    q, v = joint_states(world)
    assert q == pytest.approx(np.array(config.POSTURE), abs=1e-6)
    assert np.abs(v).max() < 1e-6


def test_joint_sizes_in_the_settings_match_the_arm(world):
    inertia = np.array([joint_inertia(world, config.POSTURE, j) for j in world.joints])

    # JOINT_SIZE is typed in by hand, rounded: it must stay within 5% of the inertia ratio it stands for
    assert config.JOINT_SIZE == pytest.approx(inertia / inertia[3], rel=0.05)
