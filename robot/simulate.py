"""The day loop: wear grows with the work done, every joint is swept every day, and the dataset is written.

Everything here is simulation with illustrative parameters. The wear is
injected by hand, so nothing in these files says anything about a real robot.
"""

import os

import numpy as np
import pandas as pd

from robot import config
from robot.guard import assert_no_leakage
from robot.schedule import actual_duty, planned_duty
from robot.sweep import run_health_check, sensor_faults
from robot.thermal import next_temperature
from robot.world import connect, disconnect

SWEEP_COLUMNS = ["day", "joint", "v_target", "v_measured", "friction_torque", "temperature_c", "posture_q",
                 "payload_kg", "duty_planned"]
EVENTS = ("regrease",)


def check_events(events, n_days, joints):
    """An event that could never happen would be ignored without a word. Refuse it instead."""
    for day, joint, event in events:
        if event not in EVENTS:
            raise ValueError(f"unknown event {event!r}: choose from {list(EVENTS)}")
        if not 0 <= day < n_days:
            raise ValueError(f"event on day {day}, but the run has days 0 to {n_days - 1}")
        if joint not in joints:
            raise ValueError(f"event on joint {joint}, which is not simulated (joints {list(joints)})")


def wear_rates(seed):
    """How fast each joint wears in the run of this seed: its nominal rate times a factor of the run's own."""
    sigma = config.RATE_SPREAD
    rng = np.random.default_rng([seed, 2])                        # a third stream: it disturbs neither work nor sensor
    return config.RATE * rng.lognormal(-0.5 * sigma ** 2, sigma, config.N_JOINTS)


def link_mass_factors(seed):
    """What each link of this run's arm weighs, as a multiple of what the model thinks. Used when MODEL_MISMATCH is on."""
    rng = np.random.default_rng([seed, 3])
    return 1 + rng.uniform(-config.MASS_ERROR, config.MASS_ERROR, len(config.POSTURE))


def wear_growth(wear, rates, worked, rng):
    """The wear one day's work adds to each joint."""
    growth = config.K_WEAR * rates * worked
    if config.WEAR_NOISE:
        sigma = config.WEAR_NOISE_SIGMA
        growth = growth * rng.lognormal(-0.5 * sigma ** 2, sigma, len(wear))
    if config.WEAR_ACCEL:
        growth = growth * (1 + config.WEAR_ACCEL_GAIN * np.maximum(0.0, wear - config.WEAR_ACCEL_FROM))
    return growth


def simulate(scenario, n_days, seed, out_dir, joints=None, events=(), on_day=None, on_step=None):
    """Run n_days of one scenario and write the five files into out_dir. Returns out_dir.

    The seed decides everything that differs between two runs: the work done,
    the sensor noise and each joint's wear rate. The same seed gives the same
    files, byte for byte. events is a list of (day, joint, "regrease"): the
    grease goes in before that day's work.

    Two hooks let a screen follow the run without changing it. on_day(day,
    rows, world) is called after each day with that day's sweep rows, the
    same rows that go into the file, so it never sees the wear. If it raises,
    the run stops and nothing is written. on_step(world) is called after
    every time step of every sweep.
    """
    if n_days < 1:
        raise ValueError("a run needs at least 1 day")
    joints = list(range(config.N_JOINTS)) if joints is None else list(joints)
    planned_duty(scenario, 0)                                     # an unknown scenario fails here, before any work
    check_events(events, n_days, joints)
    # Two generators from one seed, one for the work and one for the sensor.
    # The work done, and so the wear, then does not depend on how many sweeps
    # were measured before it.
    duty_rng, sensor_rng = np.random.default_rng([seed, 0]), np.random.default_rng([seed, 1])
    # the realism switches have streams of their own, so switching one on leaves the rest of the run as it was
    wear_rng, fault_rng = np.random.default_rng([seed, 4]), np.random.default_rng([seed, 5])

    rates = wear_rates(seed)
    wear = np.zeros(config.N_JOINTS)                              # the hidden state
    temperature = np.full(config.N_JOINTS, config.AMBIENT_C)
    sweeps, schedule, actual, truth = [], [], [], []
    world = connect(mass_factors=link_mass_factors(seed) if config.MODEL_MISMATCH else None)
    try:
        for day in range(n_days):
            planned = planned_duty(scenario, day)
            worked = actual_duty(scenario, day, duty_rng)
            for _, joint, _ in (e for e in events if e[0] == day):
                wear[joint] *= config.REGREASE_KEEP
            wear += wear_growth(wear, rates, worked, wear_rng)    # the work really done wears the joints, not the plan
            temperature = next_temperature(temperature, worked, config.WORK_SPEED)

            first_row = len(sweeps)
            for joint in joints:
                # the sweep is the only place the wear is read: it plays the physical joint
                rows = run_health_check(world, joint, wear, temperature, sensor_rng, on_step=on_step)
                if config.SENSOR_FAULTS:
                    rows = sensor_faults(rows, fault_rng)
                for row in rows:
                    sweeps.append({"day": day, **row, "payload_kg": config.PAYLOAD_KG, "duty_planned": planned})
                truth.append({"day": day, "joint": joint, "wear": wear[joint]})
            schedule.append({"day": day, "duty_planned": planned})
            actual.append({"day": day, "duty_actual": worked})
            if on_day:
                on_day(day, sweeps[first_row:], world)
    finally:
        disconnect(world)

    if not sweeps:
        raise ValueError("no sweep was recorded: every one was missed")
    sweeps = pd.DataFrame(sweeps)
    assert_no_leakage(sweeps.columns)                             # before anything is written

    truth = pd.DataFrame(truth)
    passed = truth[truth["wear"] >= config.FAIL_W].groupby("joint")["day"].min()
    truth["service_day"] = truth["joint"].map(passed).astype("Int64")   # first day at or past the threshold, else empty

    os.makedirs(out_dir, exist_ok=True)
    sweeps[SWEEP_COLUMNS].to_parquet(os.path.join(out_dir, "sweeps.parquet"), engine="pyarrow", index=False)
    pd.DataFrame(schedule).to_csv(os.path.join(out_dir, "schedule.csv"), index=False)
    pd.DataFrame(actual).to_csv(os.path.join(out_dir, "actual_duty.csv"), index=False)
    # the answer key. Nothing that trains or forecasts may read this file.
    truth.to_csv(os.path.join(out_dir, "ground_truth.csv"), index=False)
    pd.DataFrame(sorted(events), columns=["day", "joint", "event"]).to_csv(os.path.join(out_dir, "events.csv"), index=False)
    return out_dir
