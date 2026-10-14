"""Collect a dataset by name: a few simulated robots of one scenario, into a folder of their own.

This is what the collection screen does when Start is pressed. It never
writes over anything: a name that exists is refused.

Everything here is simulation with illustrative parameters.
"""

import datetime
import json
import os
import re
from contextlib import contextmanager

from robot import config
from robot.simulate import simulate

SWITCHES = ("WEAR_NOISE", "WEAR_ACCEL", "WEAR_AFFECTS_FV", "MODEL_MISMATCH", "SENSOR_FAULTS")


class CollectionStopped(Exception):
    """Raised inside a run when the person collecting asks to stop."""


@contextmanager
def switched(names):
    """Turn exactly these realism switches on, all others off, and put everything back afterwards."""
    unknown = [name for name in names if name not in SWITCHES]
    if unknown:
        raise ValueError(f"unknown switch {unknown[0]}: choose from {list(SWITCHES)}")
    before = {name: getattr(config, name) for name in SWITCHES}
    try:
        for name in SWITCHES:
            setattr(config, name, name in names)
        yield
    finally:
        for name, value in before.items():
            setattr(config, name, value)


def check_request(name, scenario, days, runs, folder):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name or ""):
        raise ValueError("the name may hold letters, digits, - and _ only, and cannot be empty")
    if scenario not in config.RAMP_DAY:
        raise ValueError(f"unknown scenario {scenario!r}: choose from {sorted(config.RAMP_DAY)}")
    if days < 1:
        raise ValueError("days must be at least 1")
    if runs < 1:
        raise ValueError("robots must be at least 1")
    if os.path.exists(folder):
        raise ValueError(f"{folder} already exists: choose another name, nothing is ever written over")


def collect(name, scenario, days, runs, first_seed=0, switches=(), events=(), joints=None, root=None,
            watch=None, should_stop=None, on_step=None):
    """Simulate `runs` robots of a scenario into <root>/<name>/<scenario>/run_<k>/. Robot k has seed first_seed + k.

    switches names the realism switches to turn on. events is a list of
    (day, joint, "regrease") that happens in every robot. watch(run, day,
    rows, world) is called after every day with that day's sweep rows.
    should_stop() is asked after every day: when it says yes, the robot in
    progress is dropped and the finished ones are kept. Returns the folder,
    how many robots were written, and whether it was stopped.
    """
    folder = os.path.join(root or config.COLLECTED_DIR, name or "")
    check_request(name, scenario, days, runs, folder)
    written, stopped = 0, False
    with switched(switches):
        for k in range(runs):
            def on_day(day, rows, world, k=k):
                if watch:
                    watch(k, day, rows, world)
                if should_stop and should_stop():
                    raise CollectionStopped
            try:
                if should_stop and should_stop():
                    raise CollectionStopped
                simulate(scenario, days, first_seed + k, os.path.join(folder, scenario, f"run_{k}"), joints=joints,
                         events=events, on_day=on_day, on_step=on_step)
                written += 1
            except CollectionStopped:
                stopped = True
                break

    if written:
        note = {"name": name, "scenario": scenario, "days": days, "runs_asked": runs, "runs_written": written,
                "first_seed": first_seed, "switches_on": [s for s in SWITCHES if s in switches],
                "events": [list(e) for e in sorted(events)], "stopped": stopped,
                "seconds_at_each_speed": [config.SETTLE_S, config.RECORD_S],
                "made": datetime.datetime.now().isoformat(timespec="seconds"),
                "note": "simulation only: the wear in ground_truth.csv was injected by hand"}
        with open(os.path.join(folder, "collection.json"), "w", encoding="utf-8") as f:
            json.dump(note, f, indent=2)
    return {"folder": folder, "runs_written": written, "stopped": stopped}
