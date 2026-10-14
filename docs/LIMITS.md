# Limits: everything that is weak, unvalidated or simulated

Updated 12 Oct 2026. At this date the project can load its data, extract
features, score three RUL baselines, and write a simulated robot dataset.
There is no RUL model, no fault detector, and no robot forecast.

## The whole project

- Nothing is validated on a real robot. The real data is from bearing and
  gearbox test rigs. The robot part is a simulation with wear injected by
  hand.
- `legacy/robot_simulator_8/` is the earlier PyQt simulator, parked. It has no
  tests, and none of its numbers are results of this project.

## Robot simulation

- **Everything in `robot/` is simulation with illustrative parameters.**
  Nothing here says anything about a real robot. The friction values, rated
  speeds, posture and noise level were chosen, not measured.
- **There is a dataset and no forecast.** `data/simulation/` holds five runs
  of each scenario (850 and 1450 days, seeds 0 to 4). Nothing predicts a
  service day yet.
- **Five robots, not ten.** Run k of the two scenarios has the same seed: the
  same wear rates and, up to day 199, the same rows. They are five robots
  with two planned futures each.
- **Thirty trajectories are not thirty independent cases.** The six joints of
  a run see the same work on the same days. Only their wear rates differ.
- **The run lengths were chosen knowing these five robots**, from where their
  slowest joints end up by the plan. Other seeds may need longer runs.
- **Nothing is ever serviced.** After its service day a joint keeps wearing,
  up to 3.7 against a threshold of 0.8. There the fit loses 2 of its 18 speed
  points. Rows after a joint's service day should not be used.
- **The spread of wear rates is a guess**: 15% between robots, bell-shaped on
  a log scale. The brief asks for the spread and gives no size.
- **The sweep holds each speed for 0.2 s**, not the brief's 1 s. In this
  simulation that changes nothing measurable (less than 0.0001%), because
  nothing in it vibrates. On a real joint 0.2 s would be too short to average.
- **The dataset on disk is the tidy one.** Wear is exactly proportional to
  the work done, the gravity model is exact and the sensor never fails. Five
  switches that change this are built and all off.
- **Wear that speeds up late in life would break a straight-line forecast.**
  With that switch on, a plain forecast was late for 30 of 30 joints, by 11
  days on average and 28 at worst. Late is the dangerous direction. With the
  switch off, this weakness cannot be seen in the data at all.
- **That forecast was a yardstick**, written into one experiment script to
  measure the switches. It used the true temperature coefficient and the true
  wear gain. The project's own forecast is not built.
- **The switches are inventions.** Their sizes (15% wear noise, 3% mass
  error, 2 in 100 sweeps missing, and so on) were chosen, not measured. The
  mass error changes link weights only; link lengths, the friction law and
  the temperature coefficient stay exactly known.
- **The switches were measured on the early ramp only**, with the same five
  robots as the tidy dataset.
- **The raw health index is wrong by up to 0.06** (8% of the threshold) when
  the joint is warm, because warm joints have less friction. With the
  temperature taken out it is within 0.003, but that used the true
  temperature coefficient, which a model does not know.
- **The temperature model is one line.** A joint moves 0.7 of the way to
  26 C + 15 C per unit of duty each day. The numbers were chosen so that the
  joints sit between 31 and 35 C at normal duty. After the duty doubles, the
  wrist joints reach 64 C.
- **The schedule is a fixed pattern**: a week, and six four-week spells that
  repeat every 168 days. Real plans are not periodic.
- **The answer key sits next to the data.** `ground_truth.csv` is in the same
  folder as `sweeps.parquet`. Nothing but its name, and the guard on the
  sweeps file's columns, stops a model from reading it.
- **Whether a model may read `actual_duty.csv` is not decided.** The sweeps
  file holds the planned duty only.
- **Byte-identical means on this computer.** The same seed gives the same
  files here. A different pyarrow version may write the same numbers into a
  different `sweeps.parquet`.
- **No maintenance in the scenarios.** A re-grease can be simulated and is
  tested, but neither scenario contains one.
- **The dashboard shows where a joint is, not when it will need service.**
  It has no forecast. Its "service due" flag comes after the true service
  day: 4.0 days on average in the early ramp and 7.5 in the late ramp,
  because the index compares a joint with its own first week, when it
  already has a little wear.
- **The dashboard was checked by a script, not by a person**, in Chrome at
  one window size. Safari, Firefox, a phone and touch were not tried.
- **The health index is in wear units only by courtesy.** It divides by the
  wear gain the simulation was built with and takes temperature out with the
  simulation's own coefficient. A real system would have to estimate both.
- **The live demo shows one sweep and nothing else.** It has no sliders and
  no forecast, and it reads back a wear that was typed on the command line.
  Its index is within 0.02 of that wear, not 0.004, because it compares one
  sweep with one baseline sweep. Closing its window by hand, and the text it
  draws above the arm, were not checked by a person.
- **The sweep reads back what the same code injected.** Fitted Coulomb
  friction is within 0.7% of the injected value on all six joints. That
  checks the arithmetic. It is not an accuracy.
- **Gravity is taken out with the same model the simulation runs on**, so it
  cancels to 0.000007 N m. A real robot's model is never exact, and the error
  would be read as friction. A switch for this is planned and not built.
- **The held joints are locked rigidly** by the physics engine (they move at
  most 0.0003 rad/s). So one joint's wear cannot reach another joint's
  reading: the isolation test passes by construction. On a real arm the held
  joints give a little.
- **Friction is sized to each joint's inertia** so that one controller works
  on all of them. The wrist joints get 0.04 to 0.06 N m. That is a choice
  that makes the simulation run, not a statement about wrist joints.
- **The noise is simple**: independent, bell-shaped, 1.1% of Coulomb
  friction, on the torque only. No noise on speed, no outliers, no drift.
- **The fit is slightly biased.** Without noise it reads Fc 0.4% high and Fv
  1.9% low on joint 3, because the slowest speed points still carry a little
  static friction. The health index is a ratio, so it is not affected (0.7999
  for a wear of 0.8).
- **The joint runs slower than asked**: 5% slower when new, 13% when worn and
  cold. The fit uses the measured speed, so this does not bias it, but a
  joint with much more friction than was tested here would fall below the
  speed the fit accepts.
- **Temperature only scales friction** (0.8% per degree), in a straight
  line, also at 64 C.
- **Two files named by the build brief are not on this computer**
  (`PARTNER_SPEC.md`, `pybullet_joint_data.py`). The package was built from
  `sim.md` and `ROBOT_SIM_DATA_SPEC.md` only.

## Features

- **The settings are first choices, not tuned ones.** The five frequency
  bands, the Hann window and the 10 healthy snapshots were picked by
  reasoning and have not been compared with alternatives.
- **The healthy reference can be wrong.** It is the median of a bearing's
  first 10 snapshots. For the shortest XJTU-SY bearing (42 snapshots) that is
  24% of its life. If a bearing is already degrading in its first 10
  snapshots, its reference is too high and every relative feature understates
  the damage for the rest of its life. This is visible in one bearing already:
  Bearing3_5's vibration was rising during its first 10 snapshots (mean
  relative rms 1.453, against 0.985 to 1.042 for the other 14).
- **The first 10 snapshots say nothing.** Their relative features are close to
  1 by construction, because they are compared with themselves.
- **"The sensor that changed most" is not the same thing with one sensor.**
  XJTU-SY, KAIST and IMS test 1 have two sensors per bearing; IMS tests 2 and
  3 have one. The largest of two noisy values is on average higher than a
  single one, so a model trained on XJTU-SY sees slightly higher values than
  IMS tests 2 and 3 will give it. Not measured yet.
- **Missing readings are filled with a straight line** between their
  neighbours before any feature is computed. XJTU-SY has none.
- **Only XJTU-SY features are cached.** IMS and KAIST are left for the final
  test. SEU and CWRU need the signal cut into windows first, which belongs to
  the faults step and is not built.

## RUL evaluation

- **There is no model yet.** The numbers so far are three baselines.
- **The best baseline is weak.** Rms only has an error of 0.200 against 0.252
  for knowing nothing, and it is worse than knowing nothing on 5 of 15
  bearings (4 of them at 40 Hz).
- **15 bearings is few.** No difference in this project has been tested for
  significance yet; the paired bootstrap of the adoption rule is not built.
- **Near-failure recall can be gamed** by predicting "failed" too early. The
  clock-only baseline scores 0.47 that way, above rms only (0.37), with the
  worst error in the table. Never quote recall without MAE.
- **Rank within a bearing mostly measures that time passes**: the clock alone
  gets 0.86.
- **The triage score is not sharp.** It is my reading of "rank across bearings
  at matched life fractions", and the clock alone gets 0.66 against 0.68 for
  rms only.
- **The hours estimate is poor.** It is derived as hours run x s / (1 - s),
  which says 0 hours at the first snapshot whatever s is. The median error is
  71% of the true hours left for rms only and 83% for knowing nothing.
- **The 90% ranges do not hold 90%.** Rms only covers 0.86 (one bearing left
  out) and 0.83 (one condition left out).
- **The rms-only table has 10 groups**, a first choice that was not tuned.
- **Predicted hours are capped** at the longest life among the training
  bearings.

## Data

- **Sampling rates are mostly not in the files.** Only SEU stores its rate.
  KAIST and the CWRU normal files were checked against the signals
  (`docs/GUIDE.md`, section 2). XJTU-SY (25.6 kHz) and IMS (20 kHz) come from
  the documentation and were not checked.
- **IMS rate is uncertain by 2.4%.** The readme says 20 kHz and 1 s per file,
  but a file has 20,480 samples. The rate is 20.0 or 20.48 kHz. 20.0 is used.
- **IMS time is an assumption.** Test 1 stopped for 486 of its 828 calendar
  hours. A step longer than 10 minutes is counted as 10 minutes
  (`config.IMS_MAX_STEP_MINUTES`), which gives 345 running hours. The data
  does not say when in each gap the rig actually stopped. Using calendar time
  instead would change the "share of life left" target for both bearings of
  test 1. This was chosen before looking at any IMS signal, and it must not be
  changed after the final test.
- **IMS test 3: the failure time is in doubt.** The readme says the test
  ended on 4 Apr 2004 after 4,448 files with an outer-race failure of
  bearing 3. The archive holds 6,324 files, to 18 Apr 2004, with no gap at
  4 Apr. The adapter takes the last file as the failure. If the failure was
  on 4 Apr, the life of this bearing is 30% shorter and every target value
  for it changes. This is one of only 3 independent IMS runs. The choice must
  be made from documents, not by looking at where the signal changes, and it
  must be written in `results/final_test/README.md` before the final test.
- **IMS and KAIST are not pristine.** The user has seen results on them from
  the earlier project. They are still held out: no setting is chosen on them.
- **Few independent runs.** XJTU-SY has 15 bearings whose lives differ by a
  factor of 60 (0.68 to 42.3 hours). IMS has 4 failed bearings but 3
  independent runs. KAIST is one bearing: a case, not a statistic.
- **KAIST: only the first 10 s of each 78 s file are read**, and some readings
  are missing (80 values in the first and last snapshot together). The adapter
  returns them as missing; nothing handles them yet.
- **CWRU normal files were recorded differently from the fault files**: 48 kHz
  against 12 kHz, and only 4 normal files against 36 fault files. A classifier
  can separate "normal" from "fault" for reasons that have nothing to do with
  the bearing. Features must stay below 6 kHz, and a perfect normal-versus-fault
  score on CWRU must not be read as proof of detection.
- **CWRU faults are at the drive-end bearing.** The files hold a drive-end and
  a fan-end sensor. The fan-end sensor, used by the paper the files came with,
  is the far one.
- **SEU has one file per class and condition.** A split by file inside one
  condition is impossible without putting parts of the same file on both
  sides, which the rules forbid. The only split that obeys the rules is across
  conditions (train on `20_0`, test on `30_2`, and the reverse).
- **SEU files are cut short.** Each header states 4,194,304 rows; each file
  holds 1,048,560, a quarter of the recording.
- **Licences.** Only KAIST's is checked (CC BY 4.0). Until the others are,
  no derived features or models are committed.
