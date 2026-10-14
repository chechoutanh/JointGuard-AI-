"""The production schedule: the duty planned for each day, and the duty that actually happened."""

from robot import config


def planned_duty(scenario, day):
    """Planned workload of one day (1 is a full day). The same every time it is asked: the model may see it."""
    if scenario not in config.RAMP_DAY:
        raise ValueError(f"unknown scenario {scenario!r}: choose from {sorted(config.RAMP_DAY)}")
    level = config.RAMP_DUTY if day >= config.RAMP_DAY[scenario] else config.BASE_DUTY
    week = config.WEEK_PATTERN[day % 7]
    spell = config.SPELL_PATTERN[(day // config.SPELL_DAYS) % len(config.SPELL_PATTERN)]
    return level * week * spell


def actual_duty(scenario, day, rng):
    """Workload that really happened: the plan times noise from rng. This is what wears the joints."""
    sigma = config.DUTY_NOISE_SIGMA
    # the mean of exp(normal(m, sigma)) is exp(m + sigma^2 / 2): m = -sigma^2 / 2 makes it 1
    return planned_duty(scenario, day) * float(rng.lognormal(-0.5 * sigma ** 2, sigma))
