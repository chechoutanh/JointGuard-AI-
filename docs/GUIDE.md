# Guide: every experiment in plain language

Each section has the same four parts: what was observed, what was expected,
the numbers, and the verdict (kept or rejected, and why). The script and raw
output of each one are in `results/`; `results/LOG.md` is the index.

Status on 12 Oct 2026: the data can be loaded, features are extracted for the
development bearings, the three RUL baselines are scored on them, and the
robot simulation has written its dataset: five simulated robots in each of two
scenarios, swept daily until every joint needs service (sections 6 to 8).
Five switches that make the simulation less tidy are built and off (section
9), and one sweep can be watched live in a window (section 10). That
completes the simulator's build brief. A dashboard shows what the sweeps say
(section 11). There is no RUL model yet, no result about faults, and no robot
forecast.

---

## 1. Loading the five datasets (7 Oct 2026)

**What was built.** One adapter per dataset in `sources/`. Each returns a list
of `Recording` objects: who the unit is, its sampling rate, the time of each
snapshot, and a function that reads one snapshot from disk when asked. No
signal is read until then, so a dataset never sits in memory.

**Observation.** The five datasets store their data in five different ways,
and each one has a trap that would have gone unnoticed:

| Dataset | Trap in the files | What the adapter does | Test that guards it |
|---|---|---|---|
| XJTU-SY | files are `1.csv` ... `2538.csv`; sorted by name, `10.csv` comes before `2.csv` and time runs backwards | sorts by number | `test_snapshots_follow_the_file_number_not_the_alphabet` |
| IMS | all four bearings of a test share one file; the third archive unpacks to `4th_test` | reads only the failed bearing's columns | `test_each_failed_bearing_reads_its_own_columns` |
| IMS | the rig stopped for up to 148 hours between snapshots | a step longer than 10 minutes counts as 10 minutes | `test_a_stop_of_the_rig_adds_one_normal_step_not_the_whole_stop` |
| KAIST | files have no header and no time column; a few readings are missing | reads the first 10 s; missing readings stay missing | `test_a_missing_reading_stays_in_its_place` |
| SEU | 16 header lines; 19 files use tabs and 1 uses commas | reads the rate and the separator from each header | `test_seu_reads_tab_files_and_comma_files` |
| CWRU | `normal_2.mat` also holds a copy of `normal_1`'s signal | takes the file's own record (the later one) | `test_cwru_file_holding_two_records_uses_the_later_one` |

The CWRU trap matters most. Reading the first record in each file would have
made `normal_1` and `normal_2` the same signal, and a split by file would then
have put the same data in training and in testing.

**Expectation.** The counts in `CLAUDE.md`: 15 XJTU-SY bearings, 4 failed IMS
bearings in 3 runs, 1 KAIST bearing of about 128 hours, SEU with two
conditions, CWRU with four classes.

**Numbers** (`python -m tools.sources`, 8 s):

| Source | Recordings | Snapshots | Rate | Length of the run |
|---|---|---|---|---|
| XJTU-SY | 15 bearings | 9216 | 25,600 Hz | 0.68 to 42.28 hours |
| IMS | 4 bearings, 3 runs | 11,620 | 20,000 Hz | 345.3, 163.8 and 1053.4 running hours |
| KAIST | 1 bearing | 129 | 25,600 Hz | 128.0 hours |
| SEU | 20 files (10 gear, 10 bearing) | 20 | 5,120 Hz | 204.8 s each |
| CWRU | 40 files (4 normal, 12 each of ball, inner, outer) | 40 | 12,000 Hz, normal 48,000 Hz | 5.1 to 10.2 s each |

No two recordings hold the same signal. 25 tests on small synthetic files pass.

**Verdict: kept.** The counts match. Three things are assumptions, not
measurements, and are listed in `docs/LIMITS.md`: the IMS rate (20.0 or
20.48 kHz), counting IMS stops as 10 minutes, and reading only the first 10 s
of each KAIST file.

**Two fields were added to `Recording`** beyond the eight in the first plan:
`channels` (the name of each column, needed to tell torque from vibration in
SEU) and `snapshot` (the function that reads one snapshot).

---

## 2. Which sampling rate do the files have? (7 Oct 2026)

**Why it matters.** Every frequency feature is defined in Hz. If the rate is
wrong, a feature meant for "0 to 500 Hz" measures a different band, and two
datasets can no longer be compared.

**Observation.** Only the SEU files store their rate. For KAIST the earlier
project had used 6666.7 Hz (2,000,000 rows read as a 5 minute record). The
dataset's Mendeley page says 25.6 kHz and 78.125 s per file, and
2,000,000 / 25,600 is exactly 78.125. For CWRU the normal files are four times
longer than the fault files.

**Hypothesis.** A wrong rate moves every spectral line by the same factor. A
line whose true position is known therefore shows which rate is right.

**KAIST numbers.** The shaft turns at 1770 to 1780 rpm, about 29.6 Hz. The
strongest line in the spectrum, in 8 signals (4 snapshots, 2 axes):

| Rate assumed | Strongest line | As a multiple of shaft speed | Second line |
|---|---|---|---|
| 6666.7 Hz | 7.8 Hz | 0.26x | 15.6 Hz = 0.53x |
| 25,600 Hz | 29.9 Hz (29.8 in the last snapshot) | 1.01x | 59.7 Hz = 2.02x |

A machine shakes once per turn. Nothing in it shakes once every four turns.

**CWRU numbers.** The 36 fault files are the documented 12 kHz set, so they
show which lines this rig produces. "Height" is how far a line stands above
its surroundings; 1 means there is no line.

| Multiple of shaft speed | 0.25x | 0.5x | 1x | 1.235x | 1.35x | 1.6x | 2x | 4x | 4.94x | 5.4x | 6.4x |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Fault files with a line there (height over 5) | 0% | 0% | 100% | 3% | 8% | 31% | 100% | 100% | 100% | 100% | 100% |
| Fault files, median height | 1.3 | 1.1 | 75 | 1.2 | 1.8 | 2.7 | 87 | 74 | 183 | 461 | 247 |
| `normal_3` read at 12 kHz | 14 | 20 | 27 | 172 | 364 | 201 | 14 | 25 | 14 | 129 | 10 |
| `normal_3` read at 48 kHz | 1.6 | 1.0 | 14 | 2.0 | 1.6 | 1.0 | 20 | 27 | 172 | 364 | 201 |

Read at 48 kHz, the normal file has lines where the fault files have them and
none where they have none. Read at 12 kHz, its three strongest lines (1.235x,
1.35x and 1.6x) sit where 3%, 8% and 31% of fault files have anything. The
other three normal files behave the same way (`output.txt`).

Two more checks agree. Electrical lines: in the fault files the lines at 120,
240, 360 and 720 Hz are strong (median height 44 to 211) and the lines at 180
and 300 Hz are weak (4.4 and 2.5); the normal files match that pattern at
48 kHz and not at 12 kHz. Length: every fault file lasts 10.1 to 10.2 s; the
normal files last 10.1 s at 48 kHz (5.1 s for `normal_0`) and 40 s at 12 kHz.

**A check that misled me first.** I started by looking for mains hum at 60 and
180 Hz. The normal files, read at 12 kHz, showed strong lines exactly there
(height 176 and 204 at 180 Hz), which pointed to 12 kHz. It was wrong: those
are this rig's 240 and 720 Hz lines read at the wrong rate. The fault files
settled it, because their own 180 Hz line is weak (median height 4.4). The
lesson: check an assumed line against files whose rate is known before using
it as a ruler.

**Verdict: kept.** KAIST is 25,600 Hz. CWRU normal files are 48,000 Hz and
fault files 12,000 Hz. The values and their reasons are in `config.py`.

**Consequences.**

- The earlier project's KAIST rate was wrong by a factor of 3.84. Its "first
  10 seconds" were really 2.6 seconds, and its frequency features for KAIST
  were in the wrong bands.
- CWRU normal and fault files were recorded at different rates. Any feature
  that compares them must stay below 6 kHz (the lower of the two limits), and
  a classifier could still tell "normal" apart by a side effect of the
  recording setup instead of the bearing. This is a limit of the dataset; see
  `docs/LIMITS.md`.
- The XJTU-SY and IMS rates were not checked this way. They come from the
  documentation.

---

## 3. Can the robot sweep run without the old simulator? (7 Oct 2026)

**Question.** `ROBOT_SIM_DATA_SPEC.md` describes how the robot dataset is
collected: move one joint at constant speed, read the torque, subtract
gravity, and what is left is friction. Does that work in plain PyBullet, in
one small script, with nothing from the old PyQt simulator?

**Expectation.** Yes. The old simulator is a real-time window at 240 steps
per second. The spec needs batch runs at 1000 steps per second with no
window, which is what PyBullet's DIRECT mode is for.

**Numbers** (`results/2026-10-07_sweep_feasibility/check.py`, KUKA iiwa, 7
joints, 18 velocities per sweep):

| Setting | Joints whose friction is recovered within 2% | Worst error | Held joints move up to |
|---|---|---|---|
| Friction sized to each joint, gains through the full mass matrix | 7 of 7 | 0.3% | 0.09 rad/s |
| Same, but gains from the mass-matrix diagonal only | 6 of 7 | 87% | 100 rad/s |
| One friction value for every joint | 4 of 7 | 126% | 20.7 rad/s |

With the first setting: wear of 0.5 put on joint 3 alone gives a health index
of 0.4999 on joint 3 and at most 0.0001 on the others. One sweep takes 0.17 s
of computer time, so a year of daily sweeps on 7 joints takes 7 minutes.

**Three things the spec does not say, each found by a wrong number first.**

1. **The robot file has friction of its own.** With no friction injected, the
   sweep still read a viscous friction of 0.53 N m s/rad. The KUKA file gives
   every joint a damping of 0.5, and PyBullet applies it silently. After
   setting it to 0 the sweep reads 0.0000. Without this, every fitted viscous
   value is 0.5 too high and the "day 0 equals the baseline" check fails.
2. **One friction value for all joints breaks the wrist.** The spec says joint
   inertias differ by about 100 times. At the test posture they differ by
   4183 times (2.52 against 0.0006 kg m^2). A friction torque that is mild
   for the shoulder flips the wrist's direction on every time step, and the
   arm shakes. Friction must be sized to each joint; here it is proportional
   to the joint's inertia.
3. **Diagonal gains are not enough once friction is on.** The spec scales each
   joint's gain by the diagonal of the mass matrix. With no friction that is
   stable. With friction, one sweep made the held joints run away to PyBullet's
   speed limit. Multiplying by the whole mass matrix instead of its diagonal
   (one changed line) fixed it on all 7 joints.

**Verdict: kept.** The method works without the old simulator, with the three
changes above.

**What this is not.** The script injects the friction and then measures it,
so 0.3% shows the arithmetic is right, not that anything is accurate. It
writes no dataset, has no noise, temperature or payload, and uses an assumed
rated speed of 1.5 rad/s, because the robot file says 10 rad/s for every
joint.

**Update, 9 Oct 2026.** The `robot/` package now exists (section 6). It keeps
findings 1 and 2. It does not use finding 3: instead of the whole mass
matrix, it locks the held joints with PyBullet's own motor, which holds them
600 times stiller.

---

## 4. Features (7 Oct 2026)

**What was built.** Three small pieces.

1. `features/snapshot.py` turns one snapshot into 10 numbers per sensor.
2. `features/relative.py` divides each number by the bearing's own healthy
   value.
3. `python -m tools.features xjtu` does step 1 for every snapshot and saves
   the result, so the 11 GB of raw files are read once.

**The 10 numbers.**

| Feature | What it measures |
|---|---|
| `rms` | how hard the bearing shakes overall |
| `peak` | the largest single excursion |
| `kurtosis` | how spiky the signal is: 1.5 for a pure sine, 3 for random noise, higher when there are impacts |
| `crest` | peak divided by rms: another measure of spikes |
| `band_10_500` ... `band_4000_8000` | the rms inside each of five frequency bands |
| `centroid_hz` | the average frequency, weighted by power |

**Decisions, and the reason for each.**

| Decision | Reason | Guarded by the test |
|---|---|---|
| Bands are in Hz, top edge 8 kHz | the same band must mean the same thing at 20 kHz (IMS) and 25.6 kHz (XJTU-SY, KAIST); the lowest limit among them is 10 kHz | `test_bands_are_in_hz_so_two_sampling_rates_agree` |
| A band above what the rate can show is an error, not a zero | a wrong band should stop the run, not quietly measure nothing | `test_a_band_above_what_the_sampling_rate_can_show_is_refused` |
| The mean is removed first | a sensor's constant offset says nothing about the machine | `test_a_constant_sensor_offset_changes_nothing` |
| Relative = value / median of the first 10 snapshots | total life is unknown while predicting, so the reference is a count of snapshots, never a share of life | `test_relative_is_the_ratio_to_the_median_of_the_first_snapshots` |
| Before 10 snapshots exist, the median of those seen so far | a value exists from the first snapshot, and still uses nothing from the future | `test_a_run_shorter_than_the_healthy_count_still_gets_values` |
| Each sensor is compared with its own reference, then the largest is kept | damage shows in whichever direction it pushes; works with one sensor or two | `test_channels_are_combined_by_the_one_that_changed_most` |

**No hindsight, checked two ways.** `test_the_past_does_not_change_when_the_future_does`
changes the later snapshots and checks that the earlier values do not move.
`test_streaming_equals_batch` computes each value with only the snapshots that
existed at that moment and checks it equals the value computed over the whole
run. Before writing the real code I ran both against a deliberately wrong
version that used the median of the whole life: both failed, so they do catch
hindsight.

**Worked example, to redo by hand.** Six snapshots. Each is the 8 samples
`0, 1, 0, -1, 0, 1, 0, -1` (a 2 Hz sine at 8 samples per second) times an
amplitude: 2, 3, 2, 4, 8, 16.

For amplitude 2 the samples are `0, 2, 0, -2, 0, 2, 0, -2`:

- mean = 0
- squares: `0, 4, 0, 4, 0, 4, 0, 4`, mean 2, so rms = sqrt(2) = 1.4142
- peak = 2
- fourth powers: `0, 16, 0, 16, ...`, mean 8, so kurtosis = 8 / 2^2 = 2
- crest = 2 / 1.4142 = 1.4142
- all the power is at 2 Hz, so the 1 to 4 Hz band holds all of it (1.4142)
  and the average frequency is 2 Hz

The rms of the six snapshots is amplitude / sqrt(2): 1.4142, 2.1213, 1.4142,
2.8284, 5.6569, 11.3137. With 3 healthy snapshots:

| Snapshot | rms | Reference | Relative rms |
|---|---|---|---|
| 0 | 1.4142 | median(1.4142) = 1.4142 | 1.0 |
| 1 | 2.1213 | median(1.4142, 2.1213) = 1.7678 | 1.2 |
| 2 | 1.4142 | median(1.4142, 2.1213, 1.4142) = 1.4142 | 1.0 |
| 3 | 2.8284 | 1.4142, fixed from now on | 2.0 |
| 4 | 5.6569 | 1.4142 | 4.0 |
| 5 | 11.3137 | 1.4142 | 8.0 |

The code prints exactly these numbers (`results/2026-10-07_features/output.txt`).

**Sanity check on the real development data.** Expectation, written in the
script before the run: a bearing shakes harder before it fails, so the
relative rms of its last snapshot should be above 1 for all 15 XJTU-SY
bearings, and near 1 over its healthy start.

| | Result |
|---|---|
| Snapshots extracted | 9216, in 69 s; 0 missing readings; cache is 1.6 MB |
| Bearings whose last snapshot is above 1 | 15 of 15 |
| Relative rms of the last snapshot | 4.78 (Bearing1_4) to 22.79 (Bearing3_1), median 13.90 |
| Mean relative rms over the first 10 snapshots | 0.985 to 1.042 for 14 bearings; 1.453 for Bearing3_5 |

**Verdict: kept.** The expectation is met. This shows the pipeline produces
sensible numbers. It is not a result about predicting remaining life: the
last snapshot is the easiest one, and nothing here says how early the rise
starts.

**One thing to watch: Bearing3_5.** Its vibration was already rising during
its first 10 snapshots (mean relative rms 1.453, against at most 1.042 for the
others). Its healthy reference is therefore taken from a bearing that was not
steady, which is the weakness listed in `docs/LIMITS.md`. It stays in the
data: no bearing is removed to make a number look better.

**Not done in this step.** IMS and KAIST features are not extracted; they are
left for the final test. SEU and CWRU need the signal cut into windows first,
which belongs to the faults step.

---

## 5. Baselines, metrics and the evaluation harness (8 Oct 2026)

**What was built.** `rul/` now holds the target, three baselines, the metrics
and the two splits. `python -m tools.rul evaluate` runs all of it on the 15
XJTU-SY bearings in under a second, from the cached features.

**The target.** s = share of life left: 1 at the first snapshot, 0 at
failure. A bearing that fails at 4 hours has s = 0.25 at 3 hours.

**The three baselines.** A model is only worth something if it beats these.

| Baseline | What it says | Why it is there |
|---|---|---|
| constant 0.5 | always "half of the life is left" | knows nothing; its error is 0.25 by construction |
| elapsed time | s = 1 - hours run / median life of the training bearings | knows only the clock |
| rms only | looks up the vibration level in a table built from the training bearings | knows one feature; shows what the other nine must add |

The rms-only table: the training snapshots are sorted by relative rms into 10
groups of equal weight. A group answers with the middle share of life left of
its snapshots, and with the range that holds 90% of them. Every training
bearing has the same total weight, so the two bearings with 2500 snapshots do
not drown out the one with 42.

**The two splits.** A bearing is always scored by a model that never saw it.

- Leave one bearing out: 15 rounds, train on 14, test on 1.
- Leave one condition out: 3 rounds, train on the 10 bearings of two speeds,
  test on the 5 of the third. This is the harder question: does it work at a
  speed and load it has never seen?

**The metrics.** Each is computed per bearing first, then combined, so every
bearing counts once.

| Metric | Meaning | What a know-nothing gets |
|---|---|---|
| MAE | mean error of s | 0.25 |
| beat 0.250 | on how many bearings the MAE is below 0.25 | 0 |
| near-failure recall | of the snapshots in the last 20% of life, the share predicted below 0.2 | 0 |
| hours error | hours left = hours run x s / (1 - s); median error in hours | - |
| % of left | the same error as a % of the true hours left | - |
| rank within | inside one bearing, does s fall as time passes (Spearman) | 0 |
| triage | of two snapshots from two different bearings, is the one nearer failure predicted lower | 0.50 |
| coverage, width | how often the truth is inside the 90% range, and how wide the range is | 0.90 at width 0.90 |

Triage is my reading of "rank across bearings at matched life fractions":
every bearing is read at the same ten shares of its life (5%, 15% ... 95%),
and every pair of readings from two different bearings is checked.

**Expectations, written before the first run** (`results/2026-10-08_baselines/README.md`):
the constant gets 0.25 and beats nothing; the clock is worse than the constant
because lives differ by a factor of 60; rms only beats the constant when one
bearing is left out and is weaker when a whole condition is left out.

**Numbers.**

Leave one bearing out:

| Predictor | MAE | Beat 0.250 | Near-failure recall | Hours error | % of left | Rank within | Triage | Coverage | Width |
|---|---|---|---|---|---|---|---|---|---|
| constant 0.5 | 0.252 | 0 of 15 | 0.00 | 1.33 | 83% | 0.00 | 0.50 | 0.90 | 0.90 |
| elapsed time | 0.317 | 3 of 15 | 0.47 | 3.08 | 112% | 0.86 | 0.66 | 0.87 | 0.73 |
| rms only | 0.200 | 10 of 15 | 0.37 | 1.11 | 71% | 0.70 | 0.68 | 0.86 | 0.69 |

Leave one condition out:

| Predictor | MAE | Beat 0.250 | Near-failure recall | Hours error | % of left | Rank within | Triage | Coverage | Width |
|---|---|---|---|---|---|---|---|---|---|
| constant 0.5 | 0.252 | 0 of 15 | 0.00 | 1.33 | 83% | 0.00 | 0.50 | 0.90 | 0.90 |
| elapsed time | 0.329 | 2 of 15 | 0.53 | 4.50 | 100% | 0.86 | 0.65 | 0.74 | 0.62 |
| rms only | 0.203 | 10 of 15 | 0.43 | 1.20 | 66% | 0.72 | 0.70 | 0.83 | 0.67 |

**Expectation against result.**

| Expectation | Result |
|---|---|
| constant: 0.25, beats nothing, coverage 0.90 at width 0.90 | met: 0.252, 0 of 15, 0.90 at 0.90 |
| the clock is worse than the constant | met: 0.317 and 0.329 against 0.252 |
| the clock still ranks well inside a bearing | met: 0.86, the highest in the table |
| rms only beats the constant with one bearing left out | met: 0.200, on 10 of 15 bearings |
| rms only is weaker with a condition left out | **not met**: 0.203, the same 10 of 15 |

The last one was wrong. The likely reason: rms is measured against each
bearing's own healthy start, so the speed and load are already divided out
before the table is built. I have not tested that explanation.

**What the table says, honestly.**

- **Rms only is a weak predictor.** Its error is 0.200 against 0.252 for
  knowing nothing: 21% better. It is worse than knowing nothing on 5 of 15
  bearings, and 4 of those 5 are at 40 Hz.
- **Near-failure recall is easy to game.** The clock scores 0.47, more than
  rms only (0.37), while having the worst error in the table. It says
  "failed" for every bearing that outlives the median, so it is right near
  the end by saying it far too early. Recall must be read next to MAE.
- **Rank within a bearing mostly measures that time passes.** The clock gets
  0.86 with no sensor at all.
- **Triage barely separates the clock from rms only**: 0.66 against 0.68. As
  defined here it is not a sharp test yet.
- **The hours estimate is poor.** For rms only the median error is 71% of the
  true hours left; for the know-nothing it is 83%.
- **The 90% ranges are too narrow.** Rms only covers 0.86 and 0.83 instead of
  0.90. They are narrower than the trivial range (0.69 against 0.90), but
  they do not keep their promise.
- **One lucky number.** With a condition left out, the clock has an error of
  0.005 on Bearing2_2. The median life of its training bearings happens to
  equal its own life (2.67 h). It is luck, not skill.

**Verdict: kept, as the reference.** These rows go into every later results
table. The bar a model has to clear is 0.200 (leave one bearing out) and 0.203
(leave one condition out), on more than 10 of 15 bearings.

**No hindsight.** `test_streaming_predictions_equal_batch_predictions` redoes
every prediction from only the snapshots that existed at that moment and
checks it equals the prediction made over the whole run, for all three
baselines. I gave two baselines hindsight on purpose (the clock reading the
bearing's last time stamp; the table reading the largest rms of the whole
run): the test failed both times.

**Worked example, to redo by hand.** One made-up bearing, snapshots at 0, 1,
2, 3, 4 hours, failure at 4 hours.

| Hour | True s | Predicted s | Error | True hours left | Predicted hours left | Error (h) | % of left |
|---|---|---|---|---|---|---|---|
| 0 | 1.00 | 0.90 | 0.10 | 4 | 0 x 0.9 / 0.1 = 0 | 4 | 100% |
| 1 | 0.75 | 0.80 | 0.05 | 3 | 1 x 0.8 / 0.2 = 4 | 1 | 33.3% |
| 2 | 0.50 | 0.50 | 0.00 | 2 | 2 x 0.5 / 0.5 = 2 | 0 | 0% |
| 3 | 0.25 | 0.10 | 0.15 | 1 | 3 x 0.1 / 0.9 = 0.333 | 0.667 | 66.7% |
| 4 | 0.00 | 0.10 | 0.10 | 0 | 4 x 0.1 / 0.9 = 0.444 | 0.444 | - |

- MAE = (0.10 + 0.05 + 0 + 0.15 + 0.10) / 5 = 0.08
- near-failure recall: only hour 4 has true s below 0.2; predicted 0.1 is
  below 0.2, so 1 of 1 = 1.00
- hours error: the errors sorted are 0, 0.444, 0.667, 1, 4; the middle one is
  0.667
- % of left: 0, 33.3, 66.7, 100 (hour 4 has nothing left); the middle is 50
- rank within: ranks of true s are 5, 4, 3, 2, 1; of predicted s 5, 4, 3,
  1.5, 1.5 (a tie); their correlation is 9.5 / sqrt(10 x 9.5) = 0.9747
- always saying 0.5 would give (0.5 + 0.25 + 0 + 0.25 + 0.5) / 5 = 0.30

The code prints these numbers
(`results/2026-10-08_baselines/worked_example_output.txt`). Hour 0 shows a
weakness of the hours formula: with no time run yet, it says 0 hours are left
whatever s is.

**Not done in this step.** No model yet. The paired bootstrap of the adoption
rule is not built; it is needed when the first model is compared with these
rows.

---

## 6. Robot simulation, milestone M1: one correct sweep (9 Oct 2026)

**Question.** The build brief `sim.md` asks for a small package, `robot/`,
that produces the simulated robot dataset. Its first milestone is one sweep:
move one joint at 18 constant speeds, hold the others, take gravity out of
the motor torque, and call what is left friction. If a known friction is put
into the simulated joint, does the sweep read the same friction back, on
every joint?

**Expectation.** Yes, by following the brief's settings as written: 1.80 N m
of Coulomb friction on every joint, and the other joints held by a PD torque
whose gains are multiplied by the mass-matrix diagonal. This was wrong.

**Numbers 1: the brief as written, then one change at a time**
(`results/2026-10-09_robot_sweep/settings_check.py`, no noise, joints 0 to 5):

| Friction | Held joints | Loop rate | Joints read within 5% | Worst error | Largest lag | Fastest held joint |
|---|---|---|---|---|---|---|
| same on every joint | PD, diagonal gains (the brief) | 600 /s | 3 of 6 | over 9999% | 100% | 100 rad/s |
| same on every joint | PD, diagonal gains | 120 /s | 4 of 6 | 1708% | 90% | 100 rad/s |
| sized to the joint | PD, diagonal gains | 60 to 600 /s | 5 of 6 at best | 58% at best | 47% at best | 100 rad/s |
| sized to the joint | PD, whole mass matrix | 600 /s | 6 of 6 | 1.0% | 26% | 0.18 rad/s |
| same on every joint | locked by the engine | 600 /s | 6 of 6 | 0.3% | 83% | 0.0008 rad/s |
| sized to the joint | locked by the engine | 600 /s | 6 of 6 | 0.3% | 5.9% | 0.0003 rad/s |
| **sized, grid from 0.10 (used)** | **locked by the engine** | **600 /s** | **6 of 6** | **0.4%** | **4.6%** | **0.0003 rad/s** |

"Lag" is how much slower than asked the joint runs. "Loop rate" is the gain
of the speed controller. 100 rad/s is PyBullet's speed limit: the held joints
ran away.

**Four settings differ from the brief, each found by a wrong number first.**

1. **The held joints are locked by PyBullet's position motor**, as brakes
   would hold them. The brief holds them with a PD torque computed in Python.
   With friction on, the held joints ran away whenever joint 1 was swept, at
   every one of the four gains tried. My explanation, which was not tested
   further: that torque is computed from the state before the time step, so
   it always acts one step late, and the joints of this arm pull on each other
   strongly (joint 0 feels 5.8 times less inertia when the others are free
   than when they are held). The engine's motor is solved inside the time
   step. Measured: it holds the other joints to 0.0003 rad/s.
2. **Friction is sized to each joint**, in proportion to its inertia: 8.64 N m
   on joint 1, 1.80 on joint 3, 0.038 on joint 5. The brief allows this. With
   1.80 N m everywhere and the held joints locked, the fit still reads Fc
   within 0.3%, but a wrist joint runs up to 83% slower than asked and only
   10 of its 18 speed points are fast enough to fit. Sensor noise is sized the
   same way, or the wrist readings would be mostly noise.
3. **The robot file's own damping is set to 0**, as in section 3. Left in, it
   adds 0.5 N m s/rad to every joint's viscous friction, and the fitted
   viscous friction of a wrist joint comes out 4419% too high. The brief does
   not mention it.
4. **The slowest target speed is 0.10 of rated speed**, not 0.08. The speed
   controller is proportional only, so the joint always runs a little slower
   than asked: 5% on a new joint, 13% on a worn and cold one. The fit keeps
   speeds of at least 0.08 of rated. A target of exactly 0.08 was therefore
   measured at 0.075 or less and thrown away on every sweep (16 of 18 points
   used). From 0.10 the slowest measured speed is 0.087 at worst, and all 18
   points are used.

**Numbers 2: the package itself, noise on**
(`results/2026-10-09_robot_sweep/run.py`):

| Joint | Fc injected (N m) | Fc fitted, new joint | Error | Health index at wear 0.8 |
|---|---|---|---|---|
| 0 | 5.2740 | 5.2392 | -0.7% | 0.810 |
| 1 | 8.6400 | 8.6622 | +0.3% | 0.799 |
| 2 | 1.6740 | 1.6616 | -0.7% | 0.812 |
| 3 | 1.8000 | 1.8108 | +0.6% | 0.798 |
| 4 | 0.0576 | 0.0575 | -0.2% | 0.802 |
| 5 | 0.0378 | 0.0376 | -0.6% | 0.809 |

Health index = (Fc now / Fc when new - 1) / 1.5. It should equal the wear.

- The plot `results/robot/sweep_day0.png` shows joint 3: the dots lie on the
  injected curve, mirrored through zero, and the worn sweep sits at 4.03 to
  4.55 N m against 1.86 to 2.41 N m when new.
- With no friction injected, the largest torque read on any joint is
  0.000007 N m, although gravity pulls 33 N m on joint 1. Gravity is taken
  out exactly.
- Joint 3 swept 20 times at wear 0.8 reads 0.798 on average, with a spread
  (sd) of 0.004.
- One sweep takes 0.25 s of computer time. One day of 6 joints takes 1.5 s,
  and 400 days times 5 runs would take 49 minutes.

**One sweep by hand** (`worked_example.py`, no noise). At a target of 1.0400
rad/s joint 3 runs at 1.0325 and the sweep reads 2.3679 N m. The friction law
at 1.0325 rad/s is 1.80 + 0.55 x 1.0325 = 2.3679. The lag is 0.0075 rad/s,
which is the torque over the controller gain: 2.3679 / (600 x 0.5256) =
0.0075. From the two fastest points alone, Fv = 0.5500 and Fc = 1.8000,
exactly what was injected.

**The fit is slightly off, and why.** On all 18 points without noise the fit
gives Fc 1.8076 (+0.4%) and Fv 0.5394 (-1.9%). The model fitted is a flat
part plus a slope. The injected friction also has a bump at low speed, where
static friction has not fully died away, and at the slowest point 0.02 N m
of it is left. The fit reads that as a little more Fc and a little less
slope. The health index is a ratio of two fits with the same error, so it
still gives 0.7999 for a wear of 0.8.

**Do the tests test anything?** 31 new tests (104 in all, 6 s). Twenty
deliberate mistakes were put into the code one at a time, such as gravity
taken at the wrong angle, the wear of the wrong joint, or `sign` in place of
`tanh`. The first version of the tests caught 18. Two more tests were added
for the two that slipped through (the hidden motors left on at load, and the
temperature of the wrong joint), and now all 20 are caught.

**Verdict: kept.** M1 passes: the plot is an antisymmetric S-curve through
zero, the worn sweep sits clearly higher, and the fitted Fc is within 0.7% of
the injected value on all six joints (the brief asks for 5% on joint 3).

**What this is not.** Everything here is simulation with illustrative
parameters. The package injects the friction and then measures it with the
same physics model, so 0.7% checks the arithmetic of the method and says
nothing about a real robot. This section is one sweep only; the day loop came
three days later (section 7). The brief
refers to two files that are not on this computer (`PARTNER_SPEC.md` and
`pybullet_joint_data.py`), so nothing was checked against them, and nothing
was copied from `legacy/`.

---

## 7. Robot simulation, milestone M2: the day loop and its files (12 Oct 2026)

**Question.** The second milestone of `sim.md` wraps the sweep in days. Each
day the plant does some work, the work wears every joint a little, and at the
end of the day every joint is swept. Three things must hold. The same seed
must give the same files, byte for byte. The hidden wear must never be in the
file a model reads. And the friction in that file must still follow the wear
after hundreds of days.

**How a day goes** (`robot/simulate.py`):

1. Planned duty comes from the schedule: a level (0.6, or 1.2 once the plant
   doubles its output), times a weekly pattern, times busy and quiet spells
   of four weeks. It has no random part, because the model is allowed to see
   the plan.
2. Actual duty is the plan times random noise of about 18%, right on average.
3. Wear grows by (1/480) x the joint's rate x the **actual** duty.
4. Each joint's temperature moves 0.7 of the way to 26 C + 15 C x actual duty
   x how fast that joint works.
5. Every joint is swept. The rows get the day and the **planned** duty.
6. The wear goes into a separate file, `ground_truth.csv`.

Two scenarios differ in one number. In `ramp_early` the duty doubles on day
200, before any joint needs service. In `ramp_late` it doubles on day 1500,
after every joint would have been serviced, so in a run shorter than that it
never happens.

**Expectation.** All three hold. I also expected the plain health index to
follow the wear closely without any correction. That part was wrong.

**Numbers 1: the brief's check**
(`results/2026-10-12_robot_dayloop/check.py`):

| Check | Result |
|---|---|
| `python -m tools.robot demo --days 60 --seed 0` writes five files | yes: 6,480 sweep rows, 1.5 minutes |
| Run again, same seed | all five files byte-identical |
| Run with seed 1 | sweeps, actual duty and ground truth differ; schedule and event log do not |
| Leakage guard on the file | passes |
| Leakage guard with a `wear` column added | refuses |

**Numbers 2: a 400-day run of each scenario** (`life.py`). The health index
is (Fc / mean Fc of the joint's first 7 days - 1) / 1.5, and the error is its
mean distance from what the true wear would give, over all days:

| Scenario | Joints that reach service | Index error, raw | Temperature taken out | Joint temperature |
|---|---|---|---|---|
| `ramp_early` | 4 of 6 (days 304, 329, 360, 399) | 0.025 to 0.063 | 0.0025 to 0.0031 | 28 to 64 C |
| `ramp_late` | 1 of 6 (day 395) | 0.009 to 0.018 | 0.0025 to 0.0030 | 28 to 45 C |

The plots are `results/robot/life_ramp_early.png` and `life_ramp_late.png`.

**Three things the numbers say.**

1. **The files are consistent over a whole life.** Once temperature is taken
   out, the friction in `sweeps.parquet` follows the hidden wear to 0.003 on
   every joint, in both runs, from new to past the service threshold.
2. **The raw index is not enough, and I did not expect that.** A warm joint
   has less friction (0.8% per degree). On a busy day the joint is warm, so
   the raw index reads low. After the duty doubles in `ramp_early`, the wrist
   joints reach 64 C and the raw index is on average 0.06 too low, which is
   8% of the service threshold of 0.8. The plot shows it as a drop on day
   200, exactly when the wear starts to grow faster. The temperature is saved
   with every sweep so that a model can take it out. Here it was taken out
   with the true coefficient, which a model does not know and has to estimate.
3. **400 days is too short for the forecast.** A joint that never reaches the
   threshold has no service day to compare a forecast with. In 400 days that
   leaves 4 of 6 joints in `ramp_early` and 1 of 6 in `ramp_late`. By the
   plan, the last joint reaches the threshold on day 551 in `ramp_early` and
   on day 907 in `ramp_late`.

Service came 2 to 5 days later than the plan says (day 304 against 301 for
joint 5 in `ramp_early`), because the work really done differs from the plan.

**Three days by hand** (`worked_example.py`, joint 3, rate 1.24). Day 0 is a
Monday of a normal spell, so the plan is 0.6 x 1.12 x 1.0 = 0.672. The work
really done was 0.6763. Wear added: 1.24 x 0.6763 / 480 = 0.001747, which is
the first line of `ground_truth.csv`. The joint settles at 26 + 15 x 0.6763
x 0.7 = 33.10 C and covers 0.7 of the way from 26: 30.97 C, which is the
temperature in `sweeps.parquet`.

**Time.** One day takes 1.50 s, so a 400-day run takes 10 minutes and two
scenarios of five runs take 100 minutes. Runs long enough for every joint
(601 and 957 days) would take 3.3 hours, which is over the two hours the
brief allows before asking. One option was measured and not adopted
(`sweep_length.py`): holding each speed for 0.1 s + 0.1 s instead of 0.5 s +
0.5 s changes the fitted friction by less than 0.0001% and brings the 3.3
hours down to 38 minutes.

**Choices the brief leaves open, and what was built.**

- The noise on the duty has mean 1. Plain lognormal noise with spread 0.18
  averages 1.016, so every plan would be 1.6% too low.
- The work and the sensor noise come from two separate random streams of the
  same seed. With one shared stream, measuring fewer joints would change the
  next day's workload.
- A re-grease multiplies a joint's wear by 0.3 on the morning of its day and
  is written to `events.csv`. The two scenarios contain none.
- With the same seed, the two scenarios are the same data up to day 199
  (checked: every row is equal). They share the plan and the random streams
  until the duty doubles. That makes a clean comparison: the same past, two
  different planned futures. It also means the two runs are not independent
  evidence.
- `ground_truth.csv` is written next to `sweeps.parquet`, as the brief's
  check lists it. The brief also says it should not be in a folder that
  training code reads. For now the separation is the file name and the guard.

**Do the tests test anything?** 45 new tests (149 in all, 9 s). To stay fast
they shorten the sweeps and speed the wear up about 100 times, so a joint
goes from new to past its threshold in 6 days. Twenty-eight deliberate
mistakes were put into the new code one at a time, such as wearing the joints
with the planned duty, writing the actual duty into the sweeps file, or
taking the last day past the threshold as the service day. All 28 are caught.

**Verdict: kept.** M2 passes.

**What this is not.** Everything here is simulation with illustrative
parameters. The wear is injected by hand and read back by the same code, so
0.003 shows that the files agree with each other. It is not an accuracy.
Nothing is forecast yet. There is one run per scenario, with one seed. Wear
grows in exact proportion to the work done, with no noise of its own: the
brief's realism switches are all off.

**Update, later on 12 Oct 2026.** Section 8 changed two settings, so the same
command no longer gives the numbers of this section: every run now draws its
own wear rates, and each speed is held for 0.1 s + 0.1 s. With both put back,
today's code writes the 60-day files of this section byte for byte
(`results/2026-10-12_robot_runs/m2_still_reproduces.py`).

---

## 8. Robot simulation, milestone M3: isolation and many runs (12 Oct 2026)

**Question.** One run is an anecdote. The forecast will be scored on joints
that wear at different rates it does not know in advance, and each of them
needs a service day to be scored against. Section 7 left two problems: one
run per scenario, and in 400 days only 4 of 6 and 1 of 6 joints reached
service. Can the simulator write five different robots per scenario, each
followed until every joint needs service? And does wear on one joint stay out
of the other joints' readings in the saved files?

**What was built.**

1. **Every run is a different robot.** In each run a joint wears at its
   nominal rate times a factor of its own, drawn from the seed: about 15%
   spread, 1 on average. The brief asks for these factors and gives no size.
2. **`--runs 5`** writes five runs into `run_0` to `run_4`, with seeds 0 to
   4. Run k is exactly what `--seed k` alone would write.
3. **Each speed is held for 0.1 s + 0.1 s**, not the brief's 0.5 s + 0.5 s.
   Section 7 measured that this changes the fitted friction by less than
   0.0001%. A day now takes 0.32 s of computer time instead of 1.50 s.
4. **The runs are 850 days (`ramp_early`) and 1450 days (`ramp_late`).** By
   the plan, the last joint of these five robots reaches service on day 780
   and on day 1370.

**Expectation.** All 30 joints of each scenario reach service, and the
friction in the files follows the wear as well as in section 7.

**Numbers 1: isolation** (`results/2026-10-12_robot_runs/isolation.py`). A
special run in which only joint 3 wears, 20 times faster than normal, so that
it passes its threshold in 30 days. Fitted Coulomb friction, temperature
taken out, first 3 days against last 3 days:

| Joint | True wear at the end | Change of fitted Fc |
|---|---|---|
| 0 | 0.000 | -0.41% |
| 1 | 0.000 | -0.44% |
| 2 | 0.000 | +0.28% |
| 3 | 0.962 | +113.74% |
| 4 | 0.000 | -0.44% |
| 5 | 0.000 | +0.53% |

The other five move by the sensor noise and no more. This holds by
construction, because the held joints are locked (section 6). The test
guards the bookkeeping: that each sweep is given the wear of its own joint.

**Numbers 2: the ten runs** (`runs.py`):

| | `ramp_early` | `ramp_late` |
|---|---|---|
| Days per run | 850 | 1450 |
| Joints that reach service | 30 of 30 | 30 of 30 |
| Earliest and latest service day | 257 and 784 | 324 and 1376 |
| Same joint in different runs: latest minus earliest | 60 to 249 days | 136 to 509 days |
| Health index against true wear, up to the service day | 0.0028 (worst 0.0037) | 0.0028 (worst 0.0038) |
| Speed points the fit could use, up to the service day | all 18 | all 18 |
| The same, over the whole run | 16 at worst | 16 at worst |
| Highest wear at the end of a run | 3.72 | 3.60 |

The dataset is 1,242,000 sweep rows in 25 MB. The plots are
`results/robot/runs_ramp_early.png` and `runs_ramp_late.png`.

**What the numbers say.**

1. **Every joint can now be scored.** All 60 trajectories have a service day
   inside their run.
2. **The runs really differ.** The wear factors run from 0.67 to 1.25. Joint
   0 needs service on day 867 in one late-ramp run and on day 1376 in
   another. A forecast cannot use the joint number as the answer.
3. **The files still follow the wear**, to 0.004 on every trajectory up to
   its service day, with temperature taken out.
4. **After its service day a joint goes where no plant would let it.**
   Nothing is serviced in these runs, so the fastest joint ends at a wear of
   3.7, against a threshold of 0.8. There its friction is so high that it
   runs up to 24% slower than asked, and the fit loses the slowest point on
   each side (16 of 18). Rows after a joint's service day should not be used.

**Three things that limit what the ten runs prove.**

- **Five robots, not ten.** Run k of both scenarios has the same seed, so the
  same wear rates and, up to day 199, the same rows (checked). That is a
  clean comparison, the same robot with two planned futures. It is not ten
  independent robots.
- **Six joints of one run share one history.** They see the same work on the
  same days. Thirty trajectories are fewer than thirty independent cases.
- **The run lengths were chosen knowing these five robots.** 850 and 1450
  days come from where their slowest joints end up. Other seeds may need
  longer runs.

**One joint by hand** (`worked_example.py`, late ramp, run 0, joint 3). Its
factor is 1.0329, so its rate is 1.24 x 1.0329 = 1.2808. The work done on
days 0 to 9 adds up to 6.1717, so the wear on day 9 is 1.2808 x 6.1717 / 480
= 0.016467, which is what `ground_truth.csv` says. Service needs a wear of
0.8, so work of 0.8 x 480 / 1.2808 = 299.82. The work done reaches 299.47 on
day 500 and 300.26 on day 501: service day 501, as in the file. With the
nominal rate it would have been day 517.

**Is section 7 still reproducible?** Yes. With the two settings put back (no
spread of wear rates, 0.5 s + 0.5 s), today's code writes the five 60-day
files of section 7 with the same SHA-256 (`m2_still_reproduces.py`).

**Do the tests test anything?** 9 new tests (158 in all, 11 s, and 1 skipped:
see below). Twelve deliberate mistakes were put into the new code. The first
version of the tests caught 11. The one that slipped through was giving all
six joints of a run the same factor; one line was added to a test and now all
12 are caught.

**Time.** The ten runs took 63 minutes of computing. On the clock it was
close to three hours, because the computer went to sleep after one idle
minute until that was noticed.

**Verdict: kept.** M3 passes.

**What this is not.** Everything here is simulation with illustrative
parameters. The wear is injected by hand, so agreement between the files and
the wear is by construction. Nothing is forecast yet. Wear still grows in
exact proportion to the work done: the brief's realism switches are off.

**A leftover.** `tests/test_robot_dashboard.py` belongs to a dashboard that
was started and stopped before any code was written. It skips itself.

---

## 9. Robot simulation, milestone M4: the realism switches (12 Oct 2026)

**Question.** The dataset of section 8 is very tidy. Wear grows in exact
proportion to the work done, the model that takes gravity out is exact, and
the sensor never fails. The brief lists five ways to make it less tidy, each
behind a switch that stays off until approved, and asks for each one's effect
on the forecast error before it is enabled. What does each one do?

**The five switches** (`robot/config.py`, all `False`):

| Switch | When on |
|---|---|
| `WEAR_NOISE` | the wear a day adds varies by about 15% from day to day and joint to joint |
| `WEAR_ACCEL` | past a wear of 0.6, a day adds more: x 1.3 at the service threshold of 0.8 |
| `WEAR_AFFECTS_FV` | wear also raises viscous friction, not only Coulomb friction |
| `MODEL_MISMATCH` | each link of the arm is up to 3% heavier or lighter than the model thinks |
| `SENSOR_FAULTS` | 2 in 100 sweeps missing, 1 in 200 readings wild, every reading rounded |

**There is no forecast to measure with, so one was made for this purpose
only.** It is the plainest form of the method in `CLAUDE.md`: a straight line
through (planned work done so far, health index), and the first day that line
reaches 0.8 under the plan. It lives in the experiment script, not in the
package. It reads the sweeps and the plan, never the ground truth. It takes
the temperature out with the true coefficient, has no baselines, and was not
tested with a wrong plan. It is a yardstick.

**Expectation.** Wear noise and sensor faults would make the forecast
noticeably worse. Model mismatch would bias the health index, because a
gravity error looks like extra torque. Both were wrong.

**Numbers** (`results/2026-10-12_robot_switches/effect.py`). The early-ramp
dataset was made again six times, with the same five robots. Forecast error
is predicted minus true service day, in days, over 30 joints:

| Switched on | True service day moves by | Health index error | Forecast at half of life (mean abs; mean) | At 3/4 of life |
|---|---|---|---|---|
| nothing | 0 | 0.0028 | 3.0; +1.8 | 3.1; +2.3 |
| `WEAR_NOISE` | 4 days at most | 0.0028 | 3.8; +0.8 | 3.0; +2.0 |
| `WEAR_ACCEL` | 10 days earlier on average, 20 at most | 0.0028 | **11.3; +11.3** | **12.0; +12.0** |
| `WEAR_AFFECTS_FV` | 0 | 0.0028 | 3.0; +1.8 | 3.1; +2.3 |
| `MODEL_MISMATCH` | 0 | 0.0028 | 3.1; +1.8 | 3.1; +2.4 |
| `SENSOR_FAULTS` | 0 | 0.0036 | 3.6; +2.2 | 3.3; +2.5 |
| all five | 10 days earlier on average | 0.0036 | 10.6; +10.5 | 11.8; +11.8 |

**What the numbers say.**

1. **Only wear that speeds up matters.** With `WEAR_ACCEL` the forecast is
   late for 30 of 30 joints, by 11 days on average and 28 at worst. Late is
   the dangerous direction: the joint needs service before the forecast says
   so. The health index is as accurate as before (0.0028). The measurement is
   fine; what fails is the assumption that the future is a straight line.
   Nothing in the first half of a joint's life shows that it will speed up.
2. **Daily wear noise is nearly harmless**, against my expectation. Over
   hundreds of days the good and bad days cancel: the service day moves by 4
   days at most.
3. **A 3% mass error does not bias the health index**, against my
   expectation. It shifts the whole friction curve up or down by up to 15.6%
   of Coulomb friction, which is large. But a gravity error pushes the same
   way whichever way the joint turns, and Coulomb friction is the part that
   changes sign, so the fit separates them: fitted Coulomb friction changes
   by 0.04%. This works because the sweep has the same speeds in both
   directions. The fitted viscous friction does change, by up to 2.5%.
4. **Viscous growth changes nothing here**, for the same kind of reason: the
   fit keeps viscous and Coulomb friction apart, and the index reads only
   Coulomb.
5. **Sensor faults cost a little**: 2.1% of sweeps missing, and the forecast
   error goes from 3.0 to 3.6 days.
6. **The 3 days with every switch off are not zero.** They come from the work
   really done differing from the plan.

**By hand** (`worked_example.py`). Every link 3% heavier, joint 1, no noise:
the model says gravity is 33.08 N m, so the motor holds 0.03 x 33.08 = 0.99
N m more. The torque read at -1.2 rad/s goes from -11.787 to -12.722 and at
+1.2 rad/s from +11.787 to +10.745: both down by about 1. The mean of the 18
readings moves by -0.990. The fitted Coulomb friction moves from 8.6530 to
8.6565 (+0.04%).

**Is the clean dataset untouched?** Yes. With every switch off, today's code
writes the first 30 days of the dataset on disk row for row. Each switch
draws its random numbers from a stream of its own, and only when it is on.

**Do the tests test anything?** 19 new tests (177 in all, 15 s). Twenty-six
deliberate mistakes were put into the new code. The first tests caught 24.
The two that slipped through were the sensor faults sharing the sensor
noise's random stream, and the size of a wild reading not being scaled to the
joint. One check was added for each, and all 26 are now caught.

**Verdict: built, and left off.** Which switches to turn on is the user's
decision. `WEAR_ACCEL` is the one that would make the forecast's job harder
and the result more honest.

**What this is not.** Everything here is simulation with illustrative
parameters. Each switch is one invented way of being less tidy, with an
invented size: none was measured on a robot. The 11 days are the error of a
yardstick with a known flaw, not of the project's forecast, which does not
exist. Only the early ramp was run. The mass error changes weights only: link
lengths, the friction law and the temperature coefficient stay exactly known.

---

## 10. Robot simulation, milestone M5: the live demo (12 Oct 2026)

**Question.** The last milestone of `sim.md` is a small demo: open the
PyBullet window, run one sweep live, and print the joint's health index. Does
it work on a real screen, and is the number it prints right?

**What was built.** `python -m tools.robot demo --gui --joint 3 --wear 0.5`
does four things. It sweeps the new joint out of sight, to get the joint's
own baseline. It opens the window and sweeps the same joint again with the
wear given on the command line. It prints the fitted friction and the health
index, and writes the index above the arm. Then it waits until the window is
closed. Nothing is written to disk.

One sweep lasts 3.6 s of simulated time, too fast to follow. The demo
therefore waits between time steps, so that the sweep is shown 5 times slower
and each speed is on screen for 1 s. The wait does not touch the physics.

**Expectation.** The window opens and the index printed equals the wear
given, to within the noise of two sweeps.

**Numbers.**

| Check | Result |
|---|---|
| Run once with the real window (joint 3, wear 0.5) | window opened, 29 s, printed 0.51 |
| Same run without the window | the same numbers to four decimals |
| All six joints at wear 0, 0.2, 0.5, 0.8 and 1.0, without the window | largest difference between the index and the wear: 0.021 |

A frame of the window is in `results/robot/demo_view.png`. The first frame
showed the arm small in a corner of the view; the camera was moved closer.

**Why 0.021 and not 0.004.** Section 6 gave a spread of 0.004 for the index,
but there the baseline was the mean of 20 sweeps. The demo uses one baseline
sweep, so the baseline's own noise goes into every index it prints.

**Three things nobody looked at.** The check run closed the window from the
program, so that a person closing the window ends the command was not tried.
The line of text above the arm is drawn by PyBullet's window and does not
appear in a saved frame, so it was not seen. And the window was opened on one
Mac only.

**Do the tests test anything?** 7 new tests (184 in all, 16 s). They run the
live sweep without a window, since a test cannot look at a screen. Eleven
deliberate mistakes were put into the new code and all 11 are caught.

**Verdict: kept.** M5 passes, with the three unseen points left for a person.

**What this is not.** Everything here is simulation with illustrative
parameters. The demo sets a wear by hand and reads it back with the same
code. It shows the method. It proves nothing about a robot. It has no sliders
(`CLAUDE.md` mentions a demo with sliders; the brief asks for one sweep and
"keep it small"), and it shows no forecast, because there is none.

---

## 11. The dashboard of the simulated robot (12 Oct 2026)

**Question.** The dataset is ten runs of numbers. Can one page show what
those numbers say about each joint, so that a person can see it without
running code? This is not a milestone of `sim.md`; the user asked for it.

**What was built.**

- `robot/health.py` turns saved sweeps into a health index: (Coulomb friction
  / the joint's own first week - 1) / 1.5, with the temperature effect taken
  out. It never looks ahead: the value of a day uses that day and the first
  week only, and inside the first week only the days so far. It never reads
  the hidden wear.
- `python -m tools.dashboard` writes one HTML file per scenario. The file
  holds its own data, drawing code and styles, so it opens in a browser
  without internet and without a server. No new dependency was added.

**What the page shows.** A row of filters (robot, joint, a day slider, an
answer-key switch). Six tiles with each joint's index on the chosen day as a
share of the service threshold. The index of all six joints over the run.
For one joint: the index with and without temperature taken out, one sweep
next to the sweep of the new joint, and the temperature. The workload,
planned and actually done. Every chart has a tooltip, works from the
keyboard, and has a table behind it.

**Design choices, with their reasons.**

- **The day slider is "as of".** Tiles show what was known on the chosen day
  and the charts fade the days after it, because a maintenance planner never
  sees the future.
- **The answer key is off until switched on**, and `--no-truth` leaves it out
  of the file. The page is about what the sweeps say; the hidden wear is only
  there to check them.
- **Workload and temperature are 7-day means.** Daily values swing with the
  weekly pattern and draw as a solid band.
- **The index axis stops at 1.2.** Nothing is serviced in these runs, so the
  index climbs to 3.7 and would squash the part that matters.
- **Six fixed colours, one per joint number.** They pass a colour-blind check
  in light and dark mode. Three are faint on a light background, which is
  why each chart also has a table.

**Expectation.** The page opens and every control responds. The "service
due" flag appears on the true service day, give or take the sensor noise.
The second part was wrong.

**Numbers** (`results/2026-10-12_robot_dashboard/check.py`, headless Chrome):

| Check | Result |
|---|---|
| Page loads and draws | yes, no script error |
| Hover, keyboard, click, joint, robot, answer key | all respond |
| Size of the pages | 1.9 MB (early ramp) and 3.3 MB (late ramp) |
| "Service due" flag against the true service day, early ramp | 4.0 days late on average, 1 to 9 days, 30 joints |
| The same, late ramp | 7.5 days late on average, -6 to 16 days, 30 joints |

**Why the flag is late.** The index compares a joint with its own first week.
In that week the joint already has a little wear (about 0.005), so the
reference is slightly too high and the index reads slightly low: 0.80 when
the wear is 0.82. A few hundredths of wear are a few days. The lag is larger
in the late ramp because wear grows more slowly there, so the same shortfall
costs more days.

**Do the tests test anything?** 22 new tests (206 in all, 17 s): 9 for the
health index on made-up sweeps that can be worked out by hand, 13 for the
numbers put into the page. Twenty deliberate mistakes were put into the new
Python code and all 20 are caught. What the page draws cannot be tested that
way; it was checked by a script that opens the page in Chrome and prods it.

**Verdict: kept.**

**What this is not.** Everything here is simulation with illustrative
parameters. The page has no forecast, because none is built: it shows where a
joint is, not when it will need service. The index uses the simulation's own
wear gain and temperature coefficient. Nobody has used the page yet: it was
checked by a script and by looking at two pictures, in Chrome at one window
size only.
