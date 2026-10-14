"""Joint temperature from one day to the next.

The first-order model of legacy/robot_simulator_8/simulator/thermal_model.py
(ThermalModel.step), cut down to its one line: move a share of the way toward
a settling temperature that rises with the work done. The old model stepped
in seconds from motor torque and speed; this one steps in days from duty.
"""

from robot import config


def next_temperature(temp, duty, speed_proxy):
    """Temperature (deg C) at the next day's health check, after a day at this duty.

    speed_proxy is how fast the joint moves in the work cycle, 1 for the
    fastest: a joint that moves more heats more.
    """
    settled = config.AMBIENT_C + config.TEMP_RISE_C * duty * speed_proxy
    return temp + config.THERMAL_ALPHA * (settled - temp)
