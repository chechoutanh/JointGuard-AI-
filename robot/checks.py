"""The five checks of the data-collection spec, to run before trusting a day of output.

The same things the test suite checks, as functions that report in plain
words, so that the collection screen can run them at the press of a button.

Everything here is simulation with illustrative parameters.
"""

import os
import tempfile
from dataclasses import dataclass

import numpy as np
import pandas as pd

from robot import config
from robot.fit import fit_friction
from robot.guard import assert_no_leakage
from robot.simulate import simulate
from robot.sweep import run_health_check
from robot.world import connect, disconnect

FILES = ("sweeps.parquet", "schedule.csv", "actual_duty.csv", "ground_truth.csv", "events.csv")


@dataclass
class Check:
    name: str
    passed: bool
    detail: str            # the numbers behind the verdict, in one line


def swept(world, joint, wear, seed):
    """Measured speeds and torques of one sweep at 35 C."""
    rows = run_health_check(world, joint, wear, np.full(config.N_JOINTS, config.TEMP_REF_C), np.random.default_rng(seed))
    return np.array([r["v_measured"] for r in rows]), np.array([r["friction_torque"] for r in rows])


def coulomb(world, joint, wear, seed):
    v, tau = swept(world, joint, wear, seed)
    return fit_friction(v, tau, config.RATED_RAD_S[joint])[0]


def sweep_shape(world):
    """A sweep of a new joint is the same curve in both directions, mirrored, and passes through zero."""
    v, tau = swept(world, 3, np.zeros(config.N_JOINTS), 0)
    mirror, middle = np.abs(tau + tau[::-1]).max(), abs(tau.mean())
    passed = bool((np.sign(tau) == np.sign(v)).all() and mirror < 0.15 and middle < 0.05)
    return Check("Sweep shape", passed, f"joint 3, new: largest |torque(v) + torque(-v)| is {mirror:.3f} N m (limit 0.15), "
                                        f"mean of all 18 torques {middle:.3f} N m (limit 0.05)")


def isolation(world):
    """Wear on joint 3 only: joint 3's friction rises, and no other joint's does."""
    new = np.zeros(config.N_JOINTS)
    worn = new.copy()
    worn[3] = config.FAIL_W
    change = np.array([coulomb(world, j, worn, 100 + j) / coulomb(world, j, new, j) - 1 for j in range(config.N_JOINTS)])
    others = np.abs(np.delete(change, 3)).max()
    return Check("Isolation", bool(change[3] > 0.5 and others < 0.05),
                 f"only joint 3 worn to {config.FAIL_W}: joint 3 reads {change[3]:+.0%}, the others at most {others:.1%} (limit 5%)")


def determinism():
    """The same seed gives the same five files, byte for byte."""
    with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
        simulate("ramp_early", 2, 0, first)
        simulate("ramp_early", 2, 0, second)
        same = 0
        for name in FILES:
            with open(os.path.join(first, name), "rb") as a, open(os.path.join(second, name), "rb") as b:
                same += a.read() == b.read()
    return Check("Same seed, same files", same == len(FILES), f"2 days, seed 0, run twice: {same} of {len(FILES)} files identical")


def fit_sanity(world):
    """The fit reads back the friction that was put in, on every joint, and at the service threshold the wear."""
    new = np.zeros(config.N_JOINTS)
    errors = [abs(coulomb(world, j, new, j) / (config.FC0 * config.JOINT_SIZE[j]) - 1) for j in range(config.N_JOINTS)]
    worn = np.full(config.N_JOINTS, config.FAIL_W)
    index = (coulomb(world, 3, worn, 50) / coulomb(world, 3, new, 3) - 1) / config.WEAR_GAIN_FC
    return Check("Fit sanity", bool(max(errors) < 0.05 and abs(index - config.FAIL_W) < 0.05),
                 f"new joints: fitted Fc off by at most {max(errors):.1%} (limit 5%); joint 3 at wear {config.FAIL_W} reads {index:.2f}")


def no_leakage():
    """The file a model reads holds no wear, and the guard would refuse it if it did."""
    with tempfile.TemporaryDirectory() as folder:
        simulate("ramp_early", 1, 0, folder)
        columns = list(pd.read_parquet(os.path.join(folder, "sweeps.parquet")).columns)
    try:
        assert_no_leakage(columns)
    except AssertionError as error:
        return Check("No leakage", False, f"the guard refuses the file as written: {error}")
    try:
        assert_no_leakage(columns + ["wear"])
    except AssertionError:
        return Check("No leakage", True, f"sweeps.parquet has {len(columns)} columns and no wear; a file with a wear column is refused")
    return Check("No leakage", False, "the guard let a file with a wear column through")


def run_all(on_result=None):
    """All five, in the order of the spec. on_result is called with each result as it comes."""
    world = connect()
    results = []
    try:
        for check in (lambda: sweep_shape(world), lambda: isolation(world), determinism, lambda: fit_sanity(world), no_leakage):
            results.append(check())
            if on_result:
                on_result(results[-1])
    finally:
        disconnect(world)
    return results
