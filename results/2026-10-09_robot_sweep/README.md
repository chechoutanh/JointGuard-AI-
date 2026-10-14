# Robot simulation, milestone M1: one correct sweep

Build brief: `sim.md`, milestone M1. Explained in `docs/GUIDE.md`, section 6.

| File | What it is |
|---|---|
| `settings_check.py`, `settings_output.txt` | The brief as written, then one change at a time. Stands alone, no noise, about 30 s. |
| `run.py`, `output.txt` | The `robot/` package on every joint, noise on, about 15 s. Writes `results/robot/sweep_day0.png`. |
| `worked_example.py`, `worked_example_output.txt` | One sweep of joint 3 without noise, to check by hand. |

## Does M1 pass?

| The brief's "done when" | Result |
|---|---|
| A sweep of joint 3 at wear 0 plots as an antisymmetric S-curve through the origin | Yes: `results/robot/sweep_day0.png`. Without noise, torque(v) + torque(-v) is at most 0.0000016 N m. |
| The same sweep at wear 0.8 sits clearly higher | Yes: 4.03 to 4.55 N m against 1.86 to 2.41 N m. |
| The fit on day 0 returns Fc within 5% of the injected value | Yes: joint 3 reads 1.811 for 1.800 (+0.6%). All six joints are within 0.7%. |

## The brief as written does not run

Fitted against injected friction, worst of joints 0 to 5 (`settings_output.txt`, part A):

| Friction | Held joints | Loop rate | Joints with Fc within 5% | Worst Fc error | Largest lag | Fastest held joint |
|---|---|---|---|---|---|---|
| same on every joint | PD, diagonal gains (the brief) | 600 /s | 3 of 6 | over 9999% | 100% | 100 rad/s |
| same on every joint | PD, diagonal gains | 120 /s | 4 of 6 | 1708% | 90% | 100 rad/s |
| sized to the joint | PD, diagonal gains | 60, 120, 240, 600 /s | 5, 5, 3, 3 of 6 | 58% to over 9999% | 47% to 100% | 100 rad/s |
| sized to the joint | PD, full mass matrix | 600 /s | 6 of 6 | 1.0% | 26% | 0.18 rad/s |
| same on every joint | locked by the engine | 600 /s | 6 of 6 | 0.3% | 83% | 0.0008 rad/s |
| sized to the joint | locked by the engine | 600 /s | 6 of 6 | 0.3% | 5.9% | 0.0003 rad/s |
| **sized to the joint, grid from 0.10 (used)** | **locked by the engine** | **600 /s** | **6 of 6** | **0.4%** | **4.6%** | **0.0003 rad/s** |

"Lag" is how much slower than asked the joint runs. 100 rad/s is PyBullet's speed limit: the held joints ran away.

Four settings differ from the brief. Each is in `robot/config.py` or `robot/world.py` with its reason.

1. **Held joints are locked by PyBullet's position motor**, not held by a PD torque with diagonal gains. With PD holds, sweeping joint 1 made the held joints run away at every loop rate tried.
2. **Friction is sized to each joint** (in proportion to its inertia; the brief allows this). With one value everywhere, a wrist joint runs up to 83% slower than asked and only 10 of its 18 points can be fitted. Sensor noise is sized the same way.
3. **The robot file's own joint damping (0.5) is set to 0.** Left in, the fitted viscous friction of a wrist joint is 4419% too high. The brief does not mention it.
4. **The speed grid starts at 0.10 of rated speed**, not 0.08. A target of 0.08 is always measured below 0.08, so the fit used 16 of 18 points on every sweep. From 0.10 it uses all 18, also at wear 1.0 and 15 C (`settings_output.txt`, part C).

## The package on every joint

`output.txt`, part A, noise on:

| Joint | Fc injected (N m) | Fc fitted, new | Error | Health index at wear 0.8 | Lag, new | Lag, worn |
|---|---|---|---|---|---|---|
| 0 | 5.2740 | 5.2392 | -0.7% | 0.810 | 4.0% | 8.6% |
| 1 | 8.6400 | 8.6622 | +0.3% | 0.799 | 4.0% | 8.6% |
| 2 | 1.6740 | 1.6616 | -0.7% | 0.812 | 3.5% | 7.5% |
| 3 | 1.8000 | 1.8108 | +0.6% | 0.798 | 4.6% | 9.9% |
| 4 | 0.0576 | 0.0575 | -0.2% | 0.802 | 2.7% | 5.7% |
| 5 | 0.0378 | 0.0376 | -0.6% | 0.809 | 2.7% | 5.7% |

- Joint 3 swept 20 times at wear 0.8: health index 0.798 on average, spread (sd) 0.004, when the baseline is the mean of 20 sweeps of the new joint.
- With no friction injected, the largest torque read on any joint is 0.000007 N m: gravity is taken out exactly.
- 0.25 s of computer time per sweep. One day of 6 joints takes 1.5 s; 400 days times 5 runs would take 49 minutes.

**Verdict: kept.** M1 passes with the four changes above.

Everything here is simulation with illustrative parameters. The package injects the friction and then measures it, so these errors check the arithmetic of the method. They say nothing about a real robot.
