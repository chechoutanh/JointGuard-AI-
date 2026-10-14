# Robot simulation, milestone M2: the day loop and its files

Build brief: `sim.md`, milestone M2. Explained in `docs/GUIDE.md`, section 7.

| File | What it is |
|---|---|
| `check.py`, `output.txt` | The brief's "done when": the real command run twice, files compared byte for byte, guard checked. About 4 minutes. |
| `demo_ramp_early_400.txt`, `demo_ramp_late_400.txt` | What `python -m tools.robot demo --scenario ...` printed for the two 400-day runs now in `data/simulation/`. |
| `life.py`, `life_output.txt` | Over those two runs: does the friction read from the saved sweeps follow the hidden wear? Writes `results/robot/life_<scenario>.png`. |
| `sweep_length.py`, `sweep_length_output.txt` | Does a shorter time at each speed change the reading? An option, not used. |
| `worked_example.py`, `worked_example_output.txt` | Three days of one joint, to check by hand. |

## Does M2 pass?

| The brief's "done when" | Result |
|---|---|
| `python -m tools.robot demo --days 60 --seed 0` writes the five files to `data/simulation/<scenario>/` | Yes: `sweeps.parquet` (6,480 rows), `schedule.csv`, `actual_duty.csv`, `ground_truth.csv`, `events.csv`, in 1.5 minutes. |
| Run twice, the files are byte-identical | Yes, all five (same SHA-256). With seed 1 the sweeps, the actual duty and the ground truth differ; the schedule and the empty event log do not. |
| The leakage guard passes on `sweeps.parquet` | Yes. With a `wear` column added it refuses: "leakage: ['wear'] must not be in the feature file". |

## A whole run of each scenario (400 days, seed 0)

The health index is the plain one from `CLAUDE.md`: (Fc / mean Fc of the joint's first 7 days - 1) / 1.5. The error is its mean absolute difference from what the true wear would give, over all 400 days.

| Scenario | Joints that reach the service threshold | Index error, raw | Index error, temperature taken out | Joint temperature |
|---|---|---|---|---|
| `ramp_early` (duty doubles on day 200) | 4 of 6, on days 304, 329, 360, 399 | 0.025 to 0.063 | 0.0025 to 0.0031 | 28 to 64 C |
| `ramp_late` (duty doubles on day 1500) | 1 of 6, on day 395 | 0.009 to 0.018 | 0.0025 to 0.0030 | 28 to 45 C |

- **The loop is right over a whole life.** With temperature taken out, the friction in the saved file follows the hidden wear to 0.003 on every joint in both runs.
- **Temperature is a strong disturbance.** A warm joint has less friction, so the raw index reads low on busy days. After the duty doubles it is up to 0.06 too low on average. The temperature is saved with every sweep so that a model can take it out. Here it was taken out with the true coefficient, which a model would have to estimate.
- **400 days is too short.** A joint that never reaches the threshold has no service day to forecast. For every joint to reach it, `ramp_early` needs 551 days and `ramp_late` 907 days (by the plan, without noise).
- **The two runs are the same data up to day 199.** With the same seed they share the plan and the random streams until the duty doubles in `ramp_early`.
- **Service came 2 to 5 days later than the plan says** (for example day 304 against 301), because the work really done differs from the plan.

## Time

| What | Computer time |
|---|---|
| One day (6 joints, 18 speeds, 1 s at each speed) | 1.50 s |
| One run of 400 days | 10 minutes |
| 2 scenarios x 5 runs x 400 days | 100 minutes |
| 2 scenarios x 5 runs, long enough for every joint (601 and 957 days) | 3.3 hours |
| The same with 0.1 s + 0.1 s at each speed instead of 0.5 s + 0.5 s | 38 minutes |

The shorter sweep changes the fitted Fc by less than 0.0001% (`sweep_length_output.txt`). It was not adopted: 0.5 s + 0.5 s is the brief's setting.

**Verdict: kept.** M2 passes.

Everything here is simulation with illustrative parameters. The wear is injected by hand and then read back, so the 0.003 shows that the files are consistent with each other. It is not an accuracy claim about any robot. Nothing is forecast yet.

**Note, later on 12 Oct 2026.** The two 400-day runs that `life.py` read were deleted at the user's request once the ten runs of milestone M3 existed. `life_output.txt` and the two `life_*.png` plots are what is left of them. To make them again, put M2's settings back first (`results/2026-10-12_robot_runs/m2_still_reproduces.py` shows how), because the same command now writes different data.
