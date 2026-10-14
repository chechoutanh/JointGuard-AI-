"""The five checks of the data-collection spec, runnable on demand (the collection screen has a button for each).

Each check must pass on the code as it is, and must FAIL when the thing it
guards is broken: a check that cannot fail checks nothing.
"""

import numpy as np
import pytest

from robot import checks, config, sweep
from robot.world import connect, disconnect


@pytest.fixture(scope="module")
def world():
    world = connect()
    yield world
    disconnect(world)


@pytest.fixture()
def fast(monkeypatch):
    monkeypatch.setattr(config, "SETTLE_S", 0.1)
    monkeypatch.setattr(config, "RECORD_S", 0.05)


def test_sweep_shape_passes_and_says_how_symmetric_the_curve_is(world, fast):
    result = checks.sweep_shape(world)

    assert result.passed
    assert result.name == "Sweep shape"
    assert "N m" in result.detail


def test_sweep_shape_fails_when_the_curve_is_pushed_to_one_side(world, fast, monkeypatch):
    real = sweep.friction
    monkeypatch.setattr(sweep, "friction", lambda v, wear, temp, joint: real(v, wear, temp, joint) + 0.5)     # the same push both ways

    assert not checks.sweep_shape(world).passed


def test_fit_sanity_passes(world, fast):
    result = checks.fit_sanity(world)

    assert result.passed
    assert "%" in result.detail


def test_fit_sanity_fails_when_the_sweep_reads_a_fifth_too_much(world, fast, monkeypatch):
    real = sweep.friction
    monkeypatch.setattr(sweep, "friction", lambda v, wear, temp, joint: 1.2 * real(v, wear, temp, joint))

    assert not checks.fit_sanity(world).passed


def test_isolation_passes(world, fast):
    result = checks.isolation(world)

    assert result.passed
    assert "joint 3" in result.detail


def test_isolation_fails_when_every_sweep_is_given_the_wear_of_joint_3(world, fast, monkeypatch):
    real = checks.run_health_check
    monkeypatch.setattr(checks, "run_health_check",
                        lambda world, joint, wear, temp, rng: real(world, joint, np.full(len(wear), wear[3]), temp, rng))

    assert not checks.isolation(world).passed


def test_determinism_passes(fast):
    result = checks.determinism()

    assert result.passed
    assert "5 of 5" in result.detail


def test_determinism_fails_when_the_second_run_gets_another_seed(fast, monkeypatch):
    real, calls = checks.simulate, []

    def drifting(scenario, n_days, seed, out_dir, **options):
        calls.append(seed)
        return real(scenario, n_days, seed + len(calls) - 1, out_dir, **options)

    monkeypatch.setattr(checks, "simulate", drifting)

    assert not checks.determinism().passed


def test_no_leakage_passes(fast):
    assert checks.no_leakage().passed


def test_no_leakage_fails_when_the_guard_lets_everything_through(fast, monkeypatch):
    monkeypatch.setattr(checks, "assert_no_leakage", lambda columns: None)

    result = checks.no_leakage()

    assert not result.passed
    assert "wear" in result.detail


def test_all_five_run_in_the_order_of_the_spec_and_each_result_is_handed_on(monkeypatch):
    # each check is tested above with the real simulation; here stand-ins keep the order test quick
    for name in ("sweep_shape", "isolation", "fit_sanity"):
        monkeypatch.setattr(checks, name, lambda world, name=name: checks.Check(name, True, "stand-in"))
    for name in ("determinism", "no_leakage"):
        monkeypatch.setattr(checks, name, lambda name=name: checks.Check(name, name != "no_leakage", "stand-in"))
    seen = []

    results = checks.run_all(on_result=seen.append)

    assert [r.name for r in results] == ["sweep_shape", "isolation", "determinism", "fit_sanity", "no_leakage"]
    assert seen == results
    assert [r.passed for r in results] == [True, True, True, True, False]      # a failed check does not stop the others
