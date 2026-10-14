"""The friction law of the simulated joint. This is the truth the sweep then measures."""

import numpy as np

from robot import config


def friction(v, wear, temp, joint):
    """Friction torque (N m) of a joint moving at v rad/s. It has the sign of v: subtract it from the motor torque.

    wear is the hidden state, 0 for a new joint. temp is in deg C.
    """
    coulomb = config.FC0 * (1 + config.WEAR_GAIN_FC * wear)
    static = config.FS0 * (1 + config.WEAR_GAIN_FS * wear)
    viscous = config.FV0 * (1 + config.WEAR_GAIN_FV * wear) if config.WEAR_AFFECTS_FV else config.FV0
    warmth = 1 - config.TEMP_COEF * (temp - config.TEMP_REF_C)

    # dry friction: static at rest, falling to Coulomb as the joint speeds up
    dry = coulomb + (static - coulomb) * np.exp(-np.abs(v / config.VS) ** config.DELTA)
    # tanh, never sign: sign(v) flips the full torque on every time step near rest
    return config.JOINT_SIZE[joint] * warmth * (dry * np.tanh(v / config.TANH_EPS) + viscous * v)
