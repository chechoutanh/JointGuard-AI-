"""The leakage guard: the hidden wear must never reach the file a model reads."""

FORBIDDEN = {"wear", "wear_true", "health_true", "service_day", "W"}


def assert_no_leakage(columns):
    """Raise if any column of the feature file is the answer key under one of its names."""
    bad = FORBIDDEN & set(columns)
    if bad:
        # raised by hand, not with "assert": python -O removes assert statements
        raise AssertionError(f"leakage: {sorted(bad)} must not be in the feature file")
