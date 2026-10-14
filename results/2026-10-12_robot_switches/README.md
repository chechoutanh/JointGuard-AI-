# Robot simulation, milestone M4: the realism switches

Build brief: `sim.md`, milestone M4. Explained in `docs/GUIDE.md`, section 9.

| File | What it is |
|---|---|
| `generate.py`, `generate_<name>.txt` | Makes the early-ramp dataset again with one switch on (and once with all five), into `data/switches/<name>/`. Six times about 25 minutes. |
| `effect.py`, `effect_output.txt` | What each switch does to the data and to a forecast of the service day. About 2 minutes. |
| `worked_example.py`, `worked_example_output.txt` | Three switches at points small enough to check by hand. |

**Every switch is off in `robot/config.py`.** The brief says to report each one's effect before enabling it. This is that report.

## The five switches

| Switch | What it does when on | Setting |
|---|---|---|
| `WEAR_NOISE` | The wear a day adds varies from day to day and from joint to joint | lognormal, spread 0.15, mean 1 |
| `WEAR_ACCEL` | Wear speeds up late in life | a day's wear x (1 + 1.5 x (wear - 0.6)) once the wear is past 0.6 |
| `WEAR_AFFECTS_FV` | Wear also raises viscous friction | x (1 + 0.9 x wear) |
| `MODEL_MISMATCH` | Each link of the arm is up to 3% heavier or lighter than the model that takes gravity out | drawn for each run |
| `SENSOR_FAULTS` | 2 in 100 sweeps are missing, 1 in 200 readings is wild (0.2 N m off), every reading is rounded (0.01 N m) | sized to each joint |

## The forecast used here is a yardstick

The project has no forecast yet. To put a number on each switch, `effect.py` uses the plainest form of the method in `CLAUDE.md`: fit a straight line through (planned work done so far, health index), and take the first day the line reaches 0.8 under the plan. It reads the sweeps and the plan, never the ground truth. It takes temperature out with the true coefficient. It has no baselines and no test with a wrong plan.

## What each switch does

The same 30 joints in every row (5 robots x 6 joints, early ramp, 850 days). Forecast error is predicted minus true service day, in days.

| Switched on | True service day moves by (mean; largest) | Health index error | Forecast at half of life: mean abs error; mean | Forecast at 3/4 of life: mean abs error; mean |
|---|---|---|---|---|
| nothing | 0 | 0.0028 | 3.0; +1.8 | 3.1; +2.3 |
| `WEAR_NOISE` | -0.1; -4 | 0.0028 | 3.8; +0.8 | 3.0; +2.0 |
| `WEAR_ACCEL` | -9.6; -20 | 0.0028 | **11.3; +11.3** | **12.0; +12.0** |
| `WEAR_AFFECTS_FV` | 0 | 0.0028 | 3.0; +1.8 | 3.1; +2.3 |
| `MODEL_MISMATCH` | 0 | 0.0028 | 3.1; +1.8 | 3.1; +2.4 |
| `SENSOR_FAULTS` | 0 | 0.0036 | 3.6; +2.2 | 3.3; +2.5 |
| all five | -9.6; -19 | 0.0036 | 10.6; +10.5 | 11.8; +11.8 |

- **Only `WEAR_ACCEL` matters to the forecast.** Service comes 10 days earlier on average, and the straight-line forecast is late for all 30 joints, by 11 days on average and 28 at worst. A late forecast is the dangerous kind. The health index itself is as good as before (0.0028): the measurement is fine, the straight line into the future is wrong.
- **`WEAR_NOISE` is nearly harmless.** Daily luck averages out over hundreds of days: the service day moves by at most 4 days.
- **`WEAR_AFFECTS_FV` changes nothing** in the forecast. Viscous friction rises (3.6% in the first 30 days), but the fit keeps it apart from Coulomb friction, which is what the index reads.
- **`MODEL_MISMATCH` shifts the whole curve and the fit ignores it.** The curve moves up or down by up to 15.6% of Coulomb friction. The fitted Coulomb friction changes by 0.04%, because a gravity error pushes the same way in both directions and Coulomb friction is the part that changes sign. The fitted viscous friction changes by up to 2.5%.
- **`SENSOR_FAULTS` cost a little**: 2.1% of sweeps missing, index error 0.0036 instead of 0.0028, forecast error 3.6 instead of 3.0 days.
- **With every switch off the forecast is already 3 days off**, because the work really done differs from the plan.

With every switch off, today's code still writes the first 30 days of the dataset on disk, row for row (`effect_output.txt`, part A).

**Verdict: the switches are built and stay off.** Which to turn on is the user's decision.

Everything here is simulation with illustrative parameters. Each switch is one invented way of being less tidy, with invented sizes. None was measured on a robot.
