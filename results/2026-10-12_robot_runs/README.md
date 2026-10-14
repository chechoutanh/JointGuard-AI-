# Robot simulation, milestone M3: isolation and many runs

Build brief: `sim.md`, milestone M3. Explained in `docs/GUIDE.md`, section 8.

| File | What it is |
|---|---|
| `demo_ramp_early.txt`, `demo_ramp_late.txt` | What the two generating commands printed. The time of each first run (about 9000 s) includes two hours in which the computer was asleep. |
| `runs.py`, `runs_output.txt` | Over the ten runs: wear rates, service days, and whether the friction in the files follows the hidden wear. Writes `results/robot/runs_<scenario>.png`. |
| `isolation.py`, `isolation_output.txt` | A special run in which only joint 3 wears. |
| `m2_still_reproduces.py`, `m2_still_reproduces_output.txt` | With M2's settings, today's code still writes M2's files byte for byte. |
| `worked_example.py`, `worked_example_output.txt` | One joint's wear rate and service day, to check by hand. |

The dataset was made with:

```
python -m tools.robot demo --scenario ramp_early --days 850 --seed 0 --runs 5
python -m tools.robot demo --scenario ramp_late --days 1450 --seed 0 --runs 5
```

## Does M3 pass?

| The brief's "done when" | Result |
|---|---|
| Isolation: wear on joint 3 only, only joint 3's Fc rises | Yes. Read from a saved dataset: joint 3 +113.7%, the other five between -0.44% and +0.53%. |
| `--runs 5` writes 5 runs, each with its own seed and its own wear rates, to `data/simulation/<scenario>/run_<k>/` | Yes, for both scenarios: 10 runs, 1,242,000 sweep rows, 25 MB. |
| 30 or more joint trajectories | 30 per scenario, and all 30 reach the service threshold within the run. |

## The ten runs

| | `ramp_early` | `ramp_late` |
|---|---|---|
| Days per run | 850 | 1450 |
| Joint trajectories with a service day | 30 of 30 | 30 of 30 |
| Earliest and latest service day | 257 and 784 | 324 and 1376 |
| Same joint, different runs: latest minus earliest service day | 60 to 249 days | 136 to 509 days |
| Health index against true wear, up to the service day (mean; worst trajectory) | 0.0028; 0.0037 | 0.0028; 0.0038 |
| Fewest of the 18 speed points a fit could use, up to the service day | 18 | 18 |
| The same, over the whole run | 16 | 16 |
| Highest wear at the end of a run | 3.72 | 3.60 |

- **Each run is a different robot.** A joint wears at its nominal rate times a factor of the run's own, between 0.67 and 1.25 in these ten runs. That moves a joint's service day by up to 509 days from one run to another.
- **The files still follow the wear.** Up to each joint's service day, the health index (temperature taken out) is within 0.004 of what the true wear gives, on all 60 trajectories.
- **Run k of the two scenarios is the same robot.** With the same seed, every sweep row is identical up to day 199. The runs are five robots with two futures each, not ten robots.
- **Long after its service day a joint is at wear no plant would allow** (up to 3.7, against a threshold of 0.8). There the joint runs so much slower than asked that the fit loses its slowest point on each side. Nothing is serviced in these runs.

## Three settings changed for this milestone

1. **Every run draws its own wear rates** (`RATE_SPREAD` = 0.15). The brief asks for them and gives no size.
2. **Each speed is held for 0.1 s + 0.1 s**, not 0.5 s + 0.5 s. The fitted friction changes by less than 0.0001%, and a day takes 0.32 s instead of 1.50 s.
3. **The runs are 850 and 1450 days long**, not 400. By the plan, the last joint of these five robots reaches service on day 780 and on day 1370. The lengths were chosen from that, so they depend on these five seeds.

With settings 1 and 2 put back, the code writes M2's 60-day files byte for byte (`m2_still_reproduces_output.txt`).

## Time

One day takes 0.32 s. A run of 850 days took 4.5 to 5.3 minutes and a run of 1450 days 7.2 to 8.8 minutes, so the ten runs are 63 minutes of computing, or 39 minutes with the two scenarios side by side.

**Verdict: kept.** M3 passes.

Everything here is simulation with illustrative parameters. The wear is injected by hand and read back by the same code. Nothing is forecast yet.

The single 400-day runs of M2 that sat next to the `run_<k>` folders were deleted at the user's request later the same day.
