"""A picture of the arm without a window: PyBullet draws it in memory, and a screen of our own shows it."""

import numpy as np
import pybullet as p

from robot import config


def render(world, width, height):
    """The arm as it stands now: an array of height x width x 3 colour values, 0 to 255."""
    view = p.computeViewMatrixFromYawPitchRoll(list(config.CAMERA_TARGET), config.CAMERA_DISTANCE, config.CAMERA_YAW,
                                               config.CAMERA_PITCH, 0, 2)
    projection = p.computeProjectionMatrixFOV(60, width / height, 0.05, 10)
    image = p.getCameraImage(width, height, view, projection, renderer=p.ER_TINY_RENDERER, physicsClientId=world.client)
    return np.reshape(image[2], (height, width, 4))[:, :, :3].astype(np.uint8)       # drop the fourth value, opacity


def ppm(picture):
    """The picture as a PPM file in memory: the one image format tkinter reads without help."""
    height, width, _ = picture.shape
    return b"P6\n%d %d\n255\n" % (width, height) + picture.tobytes()
