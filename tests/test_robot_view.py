"""A picture of the arm without a window, for a screen that draws the picture itself."""

import numpy as np
import pybullet as p
import pytest

from robot import config
from robot.view import ppm, render
from robot.world import connect, disconnect


@pytest.fixture(scope="module")
def world():
    world = connect()
    for j in world.joints:
        p.resetJointState(world.robot, j, config.POSTURE[j], physicsClientId=world.client)
    yield world
    disconnect(world)


def test_the_picture_has_the_size_asked_for_and_three_colours_per_dot(world):
    picture = render(world, 320, 240)

    assert picture.shape == (240, 320, 3)
    assert picture.dtype == np.uint8


def test_the_arm_is_in_the_picture(world):
    picture = render(world, 320, 240).astype(int)
    background = picture[0, 0]                                   # the top left corner is empty space
    arm = (np.abs(picture - background).sum(axis=2) > 30).mean()

    assert 0.02 < arm < 0.6                                      # the arm fills a few per cent of the frame, not none and not all


def test_the_picture_follows_the_joints(world):
    before = render(world, 320, 240)
    p.resetJointState(world.robot, 1, config.POSTURE[1] + 0.6, physicsClientId=world.client)
    after = render(world, 320, 240)
    p.resetJointState(world.robot, 1, config.POSTURE[1], physicsClientId=world.client)

    assert (before != after).any(axis=2).sum() > 500


def test_a_picture_becomes_a_ppm_file_in_memory():
    picture = np.arange(2 * 3 * 3, dtype=np.uint8).reshape(2, 3, 3)       # 3 wide, 2 high

    data = ppm(picture)

    assert data.startswith(b"P6\n3 2\n255\n")
    assert data[len(b"P6\n3 2\n255\n"):] == picture.tobytes()
