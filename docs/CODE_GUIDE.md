# Code guide: write it yourself, step by step

For you to write the project's code yourself, in the order it was built. Each
function below has the same shape as your example: the signature, then the
steps as comments (what to do, which algorithm, how to think about the data).
There is no finished code in this file.

Status: covers everything built up to 12 Oct 2026 (data loading, features, RUL
baselines, the five robot milestones of the simulator, and the dashboard). The RUL model, the faults part and the rest of the robot part
are not built yet, so they are not here.

## How to use this guide

1. Make a scratch copy of the project (or move a function aside) and rewrite
   one function from its steps.
2. Run the test that guards it (named under "Check yourself"). Read the failure
   message: it tells you which step is wrong.
3. When it passes, compare with the real file. Differences are fine if the
   tests pass.
4. Work in the order of this file. Each part uses the one before.

Habits that run through every function:

- **Look at the real file first.** Open one raw file in a text editor before
  writing its loader. Every loader here has a trap you only see that way.
- **Think in shapes.** Write the shape of every array in a comment
  (`# (samples, channels)`). Most bugs are a wrong axis.
- **Test on a tiny example you can do on paper**, then on the real data.
- **Nothing may look at the future.** A value at snapshot i may use snapshots
  0 to i only.

---

## 0. `config.py`: the settings

One place for every number that could be argued about, each with its reason
next to it.

```python
# For each setting write three things: the value, WHY, and how it was checked.
#
# step 1: paths. Build every path from the folder of config.py itself
#         (os.path.dirname(os.path.abspath(__file__))), never from the folder
#         you happen to run in.
# step 2: sampling rates. Only the SEU files store theirs; for the rest, write
#         the rate, where it came from (readme, paper, web page) and how it
#         was checked against the signal.
# step 3: choices that are decisions, not facts (IMS_MAX_STEP_MINUTES,
#         HEALTHY_SNAPSHOTS, the frequency bands). Write the reasoning, and
#         say "first choice, not tuned" if that is the truth.
# step 4: nothing here may be computed from results. If a number came from
#         looking at a score, it does not belong in this file.
```

---

## 1. `sources/recording.py`: one record type for every dataset

```python
@dataclass
class Recording:
    # step 1: the fields, in the order of CLAUDE.md.
    # step 2: snapshot is a FUNCTION, not an array. snapshot(i) reads snapshot i
    #         from disk when asked. Why: XJTU-SY alone is 11 GB.
    # step 3: field(repr=False, compare=False) on snapshot, so printing a
    #         Recording does not print a function address, and two recordings
    #         compare by their data fields.
    # step 4: __len__ = number of snapshots = len(t_hours).
```

---

## 2. `sources/xjtu.py`: the first adapter

Layout on disk: `<condition>/<bearing>/<n>.csv`, one header line, 2 columns.

```python
def load(root=None):
    # step 1: root defaults to config.XJTU_DIR.
    # step 2: for each folder in sorted(os.listdir(root)): does its name look
    #         like "35Hz12kN" or "37.5Hz11kN"? Use a regex with two groups
    #         ([\d.]+Hz) and (\d+kN). Skip anything else (.DS_Store, the PDF).
    # step 3: condition label = the two groups joined with "_" -> "35Hz_12kN".
    # step 4: for each bearing folder inside: call _bearing(...).
    # step 5: return the list of Recordings.


def _bearing(path, unit_id, condition):
    # step 1: list the files; keep only names matching ^(\d+)\.csv$.
    # step 2: sort the numbers AS INTEGERS. Trap: sorted by name, "10.csv" comes
    #         before "2.csv" and time runs backwards.
    # step 3: t_hours = (numbers - numbers[0]) * minutes_per_snapshot / 60.
    # step 4: define snapshot(i) HERE, inside this function, so each bearing
    #         keeps its own path and numbers. (Defined in a loop in load(), every
    #         bearing would end up reading the last bearing's files: the classic
    #         closure bug.)
    #         Inside: pd.read_csv(file).to_numpy(dtype=float) -> (samples, 2).
    # step 5: failure_hours = t_hours[-1]. For a run-to-failure bearing the
    #         last snapshot IS the failure.
    # step 6: build and return the Recording. channels = ("horizontal", "vertical").
```

Check yourself: `tests/test_xjtu.py`.

---

## 3. `sources/ims.py`: file names are the clock

Layout: one tab-separated text file per snapshot, no header, named
`2004.02.12.10.32.39`.

```python
TESTS = ...
    # step 0: a table: test name -> (folder inside the archive, {failed bearing:
    #         its column numbers counted from 0}). Read the columns from the IMS
    #         readme PDF. Trap: the third archive unpacks to "4th_test/txt".


def load(root=None):
    # step 1: for each test in TESTS: does its folder exist? If not (not
    #         unpacked), skip it quietly.
    # step 2: names, t_hours = _snapshot_times(folder)   (once per TEST)
    # step 3: for each failed bearing of that test, make one Recording that
    #         shares names and t_hours but reads its own columns.
    # step 4: run_id = the test ("test1"). Bearings 3 and 4 of test 1 share one
    #         physical run, so they must share a run_id.
    # step 5: unit_id = "test1_b3", channels = ("x","y")[:number of columns].


def _snapshot_times(path):
    # step 1: for every file name, datetime.strptime(name, "%Y.%m.%d.%H.%M.%S");
    #         skip names that do not parse.
    # step 2: sort by time.
    # step 3: steps = np.diff(seconds since the first file).
    # step 4: if config.IMS_MAX_STEP_MINUTES is not None: cap each step with
    #         np.minimum. Think: the rig was STOPPED for days; a stopped
    #         bearing does not wear, so the stop counts as one normal step.
    # step 5: t_hours = cumulative sum of the steps, with a 0 put in front,
    #         divided by 3600. (n files -> n-1 steps -> n times.)
    # step 6: return the sorted names and t_hours.


def _reader(path, names, columns):
    # step 1: return a function snapshot(i).
    # step 2: inside: pd.read_csv(file, sep="\t", header=None, usecols=list(columns)).
    #         Without header=None the first data row becomes the header.
```

Check yourself: `tests/test_ims.py`.

---

## 4. `sources/kaist.py`: read only the start of a huge file

Layout: one CSV per hour, 2,000,001 rows, no header, 4 columns.

```python
def load(root=None):
    # step 1: keep names matching ^LogFile_(\d{4}-\d\d-\d\d-\d\d-\d\d-\d\d)\.csv$.
    # step 2: parse the time in the name, sort by time.
    # step 3: t_hours = hours since the first file. The gaps are real hours here.
    # step 4: rows_to_read = int(round(seconds * fs)) (config.KAIST_*).
    #         Why: reading all 129 files whole is 17 GB of text.
    # step 5: snapshot(i): pd.read_csv(file, header=None, usecols=[0, 1], nrows=rows_to_read).
    #         Columns 2 and 3 are temperatures: not vibration, leave them out.
    # step 6: missing readings arrive as NaN. Do NOT drop the rows here:
    #         dropping shifts every later sample and changes the time axis.
    #         Return them as NaN; features.snapshot.fill_missing deals with them.
    # step 7: ONE Recording in a list: one bearing, one run.
```

Check yourself: `tests/test_kaist.py`.

---

## 5. `sources/seu_cwru.py`: files that are one snapshot

### SEU

```python
def load_seu(root=None):
    # step 1: for each of "bearingset", "gearset": list the .csv files.
    # step 2: regex ^([A-Za-z]+)_(\d+_\d+)\.csv$ -> class word, condition ("20_0").
    #         Files that do not match (the text notes) are skipped.
    # step 3: unit_id = "gearset/Chipped_20_0": the folder is part of the name,
    #         because "health" exists in both folders.


def _seu_file(path, unit_id, class_name, condition):
    # step 1: header = _seu_header(path) -> (frequency limit, separator, header lines).
    # step 2: fs = frequency limit * 2.56 (an analyser samples at 2.56 x its limit;
    #         2000 Hz -> 5120 Hz).
    # step 3: fault_class = class word lowercased; "health" -> "normal".
    # step 4: snapshot(i) = pd.read_csv(path, sep=sep, header=None,
    #         skiprows=header_lines, usecols=range(8)).
    #         Trap: every line ends with a separator, so pandas sees a 9th empty
    #         column. usecols=range(8) drops it.
    # step 5: t_hours = np.zeros(1): one snapshot.


def _seu_header(path):
    # step 1: read the first line; separator = "," if "," in it else "\t".
    #         Trap: one of the 20 files uses commas.
    # step 2: loop over lines with a counter; split each line on the separator.
    # step 3: when cells[:2] == ["Frequency", "Limit"], remember float(cells[2]).
    # step 4: when cells[0] == "Data": the samples start on the NEXT line, so
    #         return (limit, sep, line number counted from 1).
```

### CWRU

```python
def load_cwru(root=None):
    # step 1: regex ^(B|IR|OR|normal)[\d@]*_(\d)\.mat$ on each file name.
    #         "OR021@6_3.mat" -> prefix "OR", load 3.
    # step 2: class from the prefix: B ball, IR inner, OR outer, normal.
    # step 3: fs = 48000 for normal files, 12000 for the others (config.py,
    #         with the evidence next to it).
    # step 4: condition = f"{load}hp".


def _cwru_reader(path):
    # step 1: snapshot(i): mat = scipy.io.loadmat(path).
    # step 2: a file can hold MORE THAN ONE record. normal_2.mat holds record 99
    #         and a copy of record 98 (= normal_1's signal). Find every key
    #         ending in "_DE_time"; the record number is the 3 digits after the
    #         "X"; take the LARGEST number: that is the file's own record.
    # step 3: stack drive-end and fan-end as columns: np.column_stack([...ravel()...]).
    #         .ravel() because .mat arrays are (n, 1).
```

Check yourself: `tests/test_seu_cwru.py`.

---

## 6. `tools/sources.py`: look at what you loaded

```python
def describe(rec):
    # step 1: first = rec.snapshot(0). Reading the first and last snapshot is
    #         enough; reading everything would take minutes.
    # step 2: count NaN in the first and last snapshot.
    # step 3: a fingerprint of the signal: hashlib.sha1(first.tobytes()).hexdigest().
    # step 4: return a dict: unit_id, condition, class, fs, snapshots, hours,
    #         samples, channels, seconds (= samples / fs), missing, digest.


def duplicates(rows):
    # step 1: group unit ids by digest (a dict of lists).
    # step 2: keep the groups with more than one member.
    # step 3: why this exists: two files holding the same signal would leak
    #         between train and test. This is how the normal_1 / normal_2 trap
    #         is noticed.


def main():
    # step 1: for each source: skip with a message if its folder is missing.
    # step 2: describe every recording, print an aligned table.
    # step 3: print the duplicates.
```

Check yourself: `tests/test_sources_tool.py`, then `python -m tools.sources`:
expect 15, 4, 1, 20 and 40 recordings, and "identical signals: none".

---

## 7. `features/snapshot.py`: one snapshot to a few numbers

Input: `x` of shape (samples, channels), the rate `fs` in Hz, and `bands` as
(low Hz, high Hz) pairs. Output: one row of features per channel.

```python
def feature_names(bands):
    # the column names, in the same order snapshot_features returns them:
    # rms, peak, kurtosis, crest, one "band_lo_hi" per band, centroid_hz.


def fill_missing(x):
    # step 1: copy x as float (never change the caller's array).
    # step 2: for each channel: which samples are finite?
    # step 3: if any are missing: np.interp(all indices, good indices, good values)
    #         = a straight line between the neighbours.
    # step 4: think: a gap at the very end repeats the last good value (interp does that).


def snapshot_features(x, fs, bands):
    # step 1: refuse bands above fs/2 (Nyquist) with a ValueError. A band the
    #         signal cannot show would quietly measure nothing.
    # step 2: x = fill_missing(x).
    # step 3: subtract each channel's mean. A sensor's constant offset says
    #         nothing about the machine.
    # step 4: time features, per channel:
    #           mean_square = mean(x**2);  rms = sqrt(mean_square)
    #           peak = max(abs(x))
    #           kurtosis = mean(x**4) / mean_square**2   (1.5 for a sine, 3 for noise)
    #           crest = peak / rms
    # step 5: power spectrum:
    #           window = scipy.signal.get_window("hann", n)
    #           spectrum = rfft(x * window)  along the samples axis
    #           power = 2 * abs(spectrum)**2 / (n * sum(window**2))
    #         This scaling makes the powers ADD UP to the mean square, so the
    #         square root of a band's power sum is the rms inside that band.
    #         Why a window: without it a strong low tone leaks into every
    #         quiet high band.
    #         freq = np.fft.rfftfreq(n, d=1/fs): this is what keeps the bands in Hz.
    # step 6: for each band: rms of the band = sqrt(sum of power where lo <= freq < hi).
    # step 7: centroid = sum(freq * power) / sum(power), over the frequencies
    #         inside the overall band range only.
    # step 8: stack everything into (channels, features), in feature_names order.
```

Check yourself: `tests/test_snapshot_features.py`. Do the 8-sample example in
`results/2026-10-07_features/check.py` on paper first: rms of
`0,2,0,-2,0,2,0,-2` is sqrt(2).

---

## 8. `features/relative.py`: compare a bearing with itself

Arrays are (snapshots, channels, features).

```python
def relative(raw, n_healthy):
    # step 1: think first. The healthy reference is "the median of the first
    #         n_healthy snapshots". Life is unknown while predicting, so it is
    #         a COUNT of snapshots, never "the first 10% of life".
    # step 2: for snapshot i < n_healthy: only i+1 snapshots exist, so divide by
    #         np.median(raw[:i+1], axis=0). (A value from the first snapshot on,
    #         still nothing from the future.)
    # step 3: for snapshot i >= n_healthy: divide by np.median(raw[:n_healthy], axis=0)
    #         for all of them at once. The reference stops learning.
    # step 4: a run shorter than n_healthy must still work.
    # step 5: the proof of no hindsight: change the LATE snapshots and check
    #         the EARLY outputs do not move.


def worst_channel(rel):
    # one line: for each feature, the largest value over the sensors (axis=1).
    # think: damage shows in whichever direction it pushes; this also works
    # for a bearing with one sensor.
```

Check yourself: `tests/test_relative_features.py`. The two tests that matter
most are `test_the_past_does_not_change_when_the_future_does` and
`test_streaming_equals_batch`. To see they can fail, temporarily divide by the
median of the WHOLE run and watch them break.

---

## 9. `features/cache.py` and `tools/features.py`

```python
def path(source, unit_id):
    # config.PROCESSED_DIR / source / unit_id + ".npz"


def save(path, rec, raw, missing, bands):
    # step 1: os.makedirs(dirname, exist_ok=True).
    # step 2: np.savez with: raw, missing, t_hours, bands, names, channels, fs,
    #         failure_hours, and the identity strings.
    # step 3: failure_hours can be None; store NaN and convert back on load.
    # step 4: why store the bands: so a cache made with other bands can be refused.


def load(path, bands):
    # step 1: np.load; compare the stored bands with the ones asked for.
    # step 2: if they differ: raise ValueError telling the user to run --force.
    #         Quietly mixing features from two band sets is the worst outcome.
    # step 3: rebuild a Features dataclass (numpy strings -> str, arrays -> tuple/list).


def extract(rec, bands):    # in tools/features.py
    # step 1: for i in range(len(rec)): x = rec.snapshot(i), ONE at a time.
    # step 2: count np.isnan(x).sum() BEFORE features fill the gaps.
    # step 3: snapshot_features(x, rec.fs, bands) -> (channels, features).
    # step 4: np.stack the rows -> (snapshots, channels, features).


def main(argv=None):
    # step 1: argparse: a source name, and --force.
    # step 2: for each recording: if the .npz exists and not --force: say
    #         "already cached" and move on.
    # step 3: otherwise extract, save, print snapshots, missing readings, seconds.
```

Check yourself: `tests/test_features_tool.py`; then
`python -m tools.features xjtu` (about 70 s) and
`python results/2026-10-07_features/check.py`.

---

## 10. `rul/data.py`: the target and the bearings

```python
def share_of_life_left(t_hours, failure_hours):
    # s = (T_fail - t) / (T_fail - t0). 1 at the first snapshot, 0 at failure.
    # Worked check: failure at 4 h, now 3 h -> (4 - 3) / (4 - 0) = 0.25.


def load_units(source):
    # step 1: for each .npz in data/processed/<source>: cache.load(...).
    # step 2: x = worst_channel(relative(raw, config.HEALTHY_SNAPSHOTS)).
    # step 3: life_hours = failure - first time; s = share_of_life_left(...).
    # step 4: return a list of Unit(unit_id, condition, t_hours, life_hours, s, x, names).
    # think: this is the only place raw features become relative ones, so
    #        every model sees exactly the same inputs.
```

---

## 11. `rul/metrics.py`: how to score a bearing

All take one bearing's arrays. `s_true` and `s_pred` are shares of life left.

```python
def mae(s_true, s_pred):
    # mean of abs(error). Guessing 0.5 all the time gives about 0.25.


def near_failure_recall(s_true, s_pred, share):
    # step 1: near = s_true < share  (the last fifth of life).
    # step 2: of those snapshots, the fraction with s_pred < share.
    # think: predicting "failed" everywhere scores 1.0 here. Never quote this
    #        number without the MAE next to it.


def remaining_hours(elapsed_hours, s_pred, cap_hours):
    # step 1: if share s is left after t hours run, the whole life is t / (1 - s),
    #         so what remains is t * s / (1 - s).
    # step 2: s = 1 divides by zero, and s near 1 gives huge numbers: replace
    #         non-finite results by cap_hours, and cap everything at cap_hours.
    # step 3: use np.errstate to silence the warning you expect.


def remaining_time_error(t_hours, life_hours, s_pred, cap_hours):
    # step 1: elapsed = t_hours - t_hours[0];  true_left = life_hours - elapsed.
    # step 2: error = abs(remaining_hours(...) - true_left).
    # step 3: median in hours.
    # step 4: median of 100 * error / true_left, only where true_left > 0
    #         (at the failure itself nothing is left to take a percentage of).


def rank_within(s_true, s_pred):
    # step 1: scipy.stats.spearmanr(s_true, s_pred).statistic.
    # step 2: a constant prediction has no ranking (spearmanr gives nan): return 0.
    # think: this mostly measures that time passes. Report it, never lead with it.


def interval_coverage_and_width(s_true, low, high):
    # coverage = mean((low <= s_true) & (s_true <= high));  width = mean(high - low).
    # think: a range is only useful if it is both honest (coverage near 0.9)
    #        and narrower than the trivial range.


def triage_concordance(predictions, life_shares):
    # question: given two snapshots of two DIFFERENT bearings, is the one
    #           nearer failure predicted lower?
    # step 1: for each bearing read the prediction at the same SHARES of life:
    #         index = round(share * (n - 1)). A bearing with 2538 snapshots then
    #         counts no more than one with 42.
    # step 2: put all readings in three flat arrays: prediction, share, owner.
    # step 3: all pairs: a, b = np.triu_indices(len(pred), k=1).
    # step 4: keep pairs with different owners AND different shares.
    # step 5: for each pair, "right" if the later share has the lower
    #         prediction; use np.sign for -1/0/+1, and count a tie as 0.5.
    # step 6: the mean. 1 = always right, 0.5 = a coin flip.
```

Check yourself: `tests/test_rul_metrics.py`; the worked example is
`results/2026-10-08_baselines/worked_example.py` (MAE must come out 0.08).

---

## 12. `rul/baselines.py`: the lines a model must beat

Every baseline has `fit(train)` and `predict(model, t_hours, x)`. `predict`
gets times and features only, so it cannot know when the bearing fails.

```python
def weighted_quantile(values, weights, shares):
    # step 1: order = argsort(values).
    # step 2: running = cumsum(weights[order]) / total weight.
    # step 3: for each share: np.searchsorted(running, share) -> index of the
    #         first value where the running weight reaches the share.
    # step 4: clamp the index to the last value (rounding can overshoot).


def _pooled(train):
    # step 1: join s and x of all training bearings.
    # step 2: weight of one snapshot = 1 / (snapshots of its bearing), so every
    #         bearing weighs exactly 1. Otherwise the two 2500-snapshot bearings
    #         drown out the one with 42.


def fit_constant(train):   # model = the 5% and 95% points of the training targets
def predict_constant(model, t_hours, x):   # s = 0.5; range = those two points


def fit_elapsed(train):
    # model = median training life, plus the shortest and longest (5%/95%).
def predict_elapsed(model, t_hours, x):
    # s = 1 - elapsed / life, clipped to [0, 1]. Long life gives the upper
    # edge of the range, short life the lower.


def fit_rms(train, bins):
    # step 1: pooled relative rms of all training snapshots, with weights.
    # step 2: bin edges = weighted quantiles at 1/bins, 2/bins, ...
    # step 3: np.unique the edges, drop any equal to the maximum (no empty bin).
    # step 4: group each snapshot with np.searchsorted(edges, rms).
    # step 5: for each group: weighted quantiles of s at 5%, 50%, 95% -> a table.
def predict_rms(model, t_hours, x):
    # group of each new snapshot by the same searchsorted; answer = its table row.
    # think: it reads only the CURRENT rms. Reading the whole run's maximum
    #        would be hindsight.
```

Check yourself: `tests/test_rul_baselines.py`, above all
`test_streaming_predictions_equal_batch_predictions`.

---

## 13. `rul/evaluate.py` and `tools/rul.py`: scoring honestly

```python
def leave_one_bearing_out(units):
    # a list of (train, test) pairs: for each bearing, test = [it], train = the rest.


def leave_one_condition_out(units):
    # for each condition: test = all its bearings, train = the other conditions.
    # think: this is the harder question: a speed and load never seen.


def score(unit, prediction, cap_hours):
    # call each metric on this one bearing; return a dict of numbers.


def evaluate(units, folds, predictors):
    # step 1: for each predictor, for each fold: model = fit(train).
    # step 2: cap_hours = the longest training life (no claim beyond what was seen).
    # step 3: for each test bearing: predict, score, and keep the predicted s.
    # step 4: triage over ALL kept predictions of that predictor.
    # step 5: the golden rule: a bearing is NEVER predicted by a model that
    #         trained on it.


def summarise(result):
    # step 1: average each metric over BEARINGS, not over snapshots.
    # step 2: hours errors: the median over bearings.
    # step 3: count bearings with MAE below 0.250.


def main(argv=None):   # tools/rul.py
    # load_units("xjtu"); for each split print one table row per predictor,
    # then the MAE of each bearing.
```

Check yourself: `tests/test_rul_evaluate.py`, then `python -m tools.rul evaluate`.
Expect (8 Oct 2026): constant 0.252, elapsed time 0.317, rms only 0.200 with
one bearing left out.

---

## 14. `robot/`: one health-check sweep (milestone M1 of `sim.md`)

The idea in one line: move one joint at a constant speed, and the motor
torque is gravity plus friction, because nothing is accelerating. Take
gravity out and friction is left. Everything here is simulation.

```python
# robot/config.py
# step 1: one number per line, each with its reason. The friction numbers are
#         for joint 3; the other joints are multiplied by JOINT_SIZE.
# step 2: JOINT_SIZE = each joint's inertia divided by joint 3's. Get the
#         inertias by printing the mass-matrix diagonal at POSTURE once, then
#         type the rounded ratios in. think: why not the same friction on
#         every joint? Joint 5 has 1/50 of joint 3's inertia; 1.80 N m on it
#         is like a brake.
# step 3: SPEED_FRACS: 9 speeds each way, np.geomspace, the negative half
#         mirrored. Start ABOVE the fit limit (0.10 against 0.08): the joint
#         always runs a little slower than asked.


# robot/friction.py
def friction(v, wear, temp, joint):
    # step 1: wear raises the levels: coulomb = FC0 * (1 + gain * wear), and
    #         the same shape for static.
    # step 2: temperature is one multiplier: 1 - TEMP_COEF * (temp - reference).
    # step 3: dry friction falls from static to coulomb as speed rises:
    #         coulomb + (static - coulomb) * exp(-|v / VS| ** DELTA).
    # step 4: give it the sign of v with tanh(v / eps), NEVER np.sign(v).
    #         think: at rest sign() flips the whole torque every time step and
    #         the joint shakes. tanh passes through zero.
    # step 5: add viscous * v, multiply by JOINT_SIZE[joint] and the
    #         temperature multiplier.
    # step 6: read every number from config at call time (config.FC0, not a
    #         copy made at import), or a test cannot switch a setting.


# robot/fit.py
def fit_friction(v, tau, rated):
    # the model: tau = Fc * sign(v) + Fv * v. Two unknowns, a straight-line fit.
    # step 1: keep the points with |v| >= FIT_MIN_FRAC * rated.
    # step 2: fewer than 2 left -> raise ValueError. Never return a number
    #         that came from nothing.
    # step 3: design matrix with two columns, sign(v) and v; np.linalg.lstsq.
    # think: sign() is fine HERE. This is a fit to data, not physics.


# robot/world.py
def connect(gui=False):
    # step 1: p.connect(p.DIRECT), or p.GUI for the demo. Keep the client id
    #         and pass physicsClientId to every call after.
    # step 2: gravity, time step 1/1000, load kuka_iiwa/model.urdf from
    #         pybullet_data.getDataPath() with useFixedBase=True.
    # step 3: TRAP: every joint loads with a hidden motor holding it at speed
    #         0. Switch it off: setJointMotorControl2(..., VELOCITY_CONTROL,
    #         force=0). Without this your torques do nothing, and nothing warns.
    # step 4: TRAP: the file gives every joint a damping of 0.5. Set it to 0
    #         with changeDynamics, or the sweep reads it as friction.
    # step 5: read the joint limits from getJointInfo (items 8 and 9).


def joint_states(world):      # two arrays: angle and speed of every joint
def gravity_torque(world, q):
    # calculateInverseDynamics(q, zero speeds, zero accelerations): with
    # nothing moving, the only torque left is gravity.
    # TRAP: pass plain lists of floats, not numpy arrays.
def joint_inertia(world, q, joint):   # mass matrix [joint][joint]
def hold(world, joints):      # POSITION_CONTROL at the posture, force HOLD_FORCE_NM
def release(world, joint):    # VELOCITY_CONTROL with force 0: the motor is off


# robot/sweep.py
def start_angle(joint, v_target):
    # travel = v_target * (settle + record seconds); start half a travel
    # BEFORE the posture angle, so the joint ends half a travel after it.
    # (v_target carries the sign, so negative speeds start on the other side.)


def run_health_check(world, joint, wear, temperature_c, rng):
    # step 1: hold every other joint, release this one.
    # step 2: gain = VELOCITY_GAIN * this joint's inertia (once: it does not
    #         change along the joint's own travel).
    # step 3: for each target speed:
    #         a. reset every joint (others to the posture, this one to its
    #            start angle, already moving at the target speed).
    #         b. for each time step:
    #            - read angles and speeds
    #            - gravity at THIS step's angles (not once per sweep)
    #            - command = gravity + gain * (target - speed)
    #            - apply command - friction(speed, wear[joint], ...)
    #            - step the simulation
    #            - after the settle time: add up (command - gravity) and speed
    #         c. one row: target speed, MEAN measured speed, mean torque + noise
    #            from rng, temperature, posture.
    # think: why is command - gravity the friction? At constant speed the
    #        joint's own torque balance is command - friction - gravity = 0.
    # think: this is the ONLY function that may read wear. It plays the
    #        physical joint. wear must never be in what it returns.
    # think: rng comes in as an argument. A generator created at the top of a
    #        file gives different numbers depending on what ran before.
```

Check yourself: `tests/test_robot_friction.py`, `test_robot_fit.py`,
`test_robot_world.py`, `test_robot_sweep.py`. The sharpest one is
`test_with_no_friction_the_sweep_reads_zero`: if gravity, the hidden motors
or the file's damping are wrong, it fails. Then run
`python results/2026-10-09_robot_sweep/worked_example.py` and check one row
with a calculator: at 1.0325 rad/s, 1.80 + 0.55 x 1.0325 = 2.3679 N m.

---

## 15. `robot/`: the day loop and its files (milestone M2 of `sim.md`)

Three things exist in the simulation, and only one of them is data. `wear` is
the hidden truth. `duty` is the day's workload. The `sweep` is what a sensor
sees. The whole design of this part is keeping the first out of the third.

```python
# robot/guard.py
FORBIDDEN = {...}     # every name the answer key could hide under
def assert_no_leakage(columns):
    # step 1: bad = FORBIDDEN & set(columns).
    # step 2: if bad: raise AssertionError naming the columns.
    # TRAP: do not write "assert not bad". python -O deletes assert lines,
    #       and the guard would silently stop guarding.


# robot/schedule.py
def planned_duty(scenario, day):
    # step 1: unknown scenario -> ValueError that lists the known ones.
    # step 2: level = RAMP_DUTY from the scenario's ramp day on, else BASE_DUTY.
    # step 3: times WEEK_PATTERN[day % 7], times the spell of the 28-day
    #         block the day falls in.
    # think: NO random numbers here. The plan is what the model is allowed to
    #        see, so it must be the same every time it is asked.
    # think: why must duty vary? If every day were 0.6, "wear per unit of
    #        work" and "wear per day" would be the same number and no model
    #        could tell which one it had learned.


def actual_duty(scenario, day, rng):
    # planned * lognormal noise drawn from rng.
    # TRAP: exp(normal(0, s)) averages exp(s^2 / 2), not 1. With s = 0.18 the
    #       plan would be 1.6% too low every day. Use mean -s^2 / 2.


# robot/thermal.py
def next_temperature(temp, duty, speed_proxy):
    # step 1: settled = ambient + rise * duty * speed_proxy.
    # step 2: return temp + alpha * (settled - temp).
    # think: this is a first-order lag, the same one line as the old
    #        simulator's thermal model, stepped in days instead of seconds.


# robot/simulate.py
def check_events(events, n_days, joints):
    # refuse an unknown event name, a day outside the run, a joint that is not
    # simulated. think: an event that can never happen would otherwise be
    # ignored without a word.


def simulate(scenario, n_days, seed, out_dir, joints=None, events=()):
    # step 1: check the inputs BEFORE any work (days, scenario, events).
    # step 2: two generators from the one seed: default_rng([seed, 0]) for the
    #         work, default_rng([seed, 1]) for the sensor. think: with one
    #         shared generator, measuring fewer joints would change the next
    #         day's workload.
    # step 3: wear = zeros, temperature = ambient. Then for each day:
    #         a. planned = planned_duty(...); worked = actual_duty(..., duty_rng)
    #         b. events of today (a re-grease: wear[joint] *= 0.3)
    #         c. wear += K_WEAR * RATE * worked       <- the ACTUAL work
    #         d. temperature = next_temperature(temperature, worked, WORK_SPEED)
    #         e. for each joint: run_health_check(...) and add day, payload
    #            and the PLANNED duty to every row; note (day, joint, wear)
    #            in a SEPARATE list
    #         Close the PyBullet world in a finally block.
    # step 4: assert_no_leakage(sweeps.columns) before any file is written.
    # step 5: service_day of a joint = the FIRST day its wear is at or past
    #         FAIL_W; empty if it never is.
    # step 6: write the five files. sweeps.parquet gets exactly the contract's
    #         columns, in order.
    # think: which duty goes where? The joints are worn by what really
    #        happened. The model is told what was planned. Mixing them up is
    #        a leak in one direction and wrong physics in the other.


# tools/robot.py
def parse(argv):   # demo, --scenario (choices from RAMP_DAY), --days 400, --seed 0
def main(argv=None):
    # out_dir = SIMULATION_DIR / scenario; simulate; print where the files are
    # and which one is the answer key.
```

Check yourself: `tests/test_robot_guard.py`, `test_robot_schedule.py`,
`test_robot_thermal.py`, `test_robot_simulate.py`, `test_robot_tool.py`. The
simulate tests shorten the sweeps and speed the wear up about 100 times, so a
whole life takes 6 days and half a second. Then run
`python results/2026-10-12_robot_dayloop/worked_example.py` and check day 0
with a calculator: wear added = 1.24 x 0.6763 / 480 = 0.001747.

---

## 16. `robot/`: many runs (milestone M3 of `sim.md`)

One trajectory is an anecdote. An evaluation needs many joints that wear at
different, unknown rates.

```python
# robot/simulate.py
def wear_rates(seed):
    # step 1: a THIRD generator, default_rng([seed, 2]). think: the first two
    #         are the work and the sensor. A new source of randomness gets a
    #         new stream, or it shifts every number drawn after it.
    # step 2: one factor per joint: lognormal with spread RATE_SPREAD and
    #         mean 1 (the same -s^2 / 2 trick as the duty noise).
    # step 3: return RATE * factors.
    # think: why per joint AND per run? If joint 5 always wore 1.6 times as
    #        fast as joint 3, a model could learn the joint number instead of
    #        reading the sweeps.


def simulate(...):
    # one changed line: wear += K_WEAR * wear_rates(seed) * worked.
    # think: the seed now decides everything that differs between two runs.
    #        That is what lets "run k" mean "the single run of seed + k".


# tools/robot.py
def parse(argv):
    # add --runs (default None). Refuse --runs 0 with parser.error.
def main(argv=None):
    # no --runs: one run into <scenario>/           (as before)
    # --runs N:  run k into <scenario>/run_<k>/ with seed + k
```

Check yourself: `tests/test_robot_simulate.py` (the `wear_rates` tests and
`test_isolation_in_the_saved_dataset`) and `tests/test_robot_tool.py`. The
sharpest one is `test_run_k_is_the_single_run_of_seed_plus_k`: it compares
whole files, byte for byte. Then run
`python results/2026-10-12_robot_runs/worked_example.py` and check a service
day with a calculator.

---

## 17. `robot/`: the realism switches (milestone M4 of `sim.md`)

A clean simulation flatters every method. Each switch adds one way in which a
real plant is less tidy. Each is a `True`/`False` in `robot/config.py`, off
until approved, and with all of them off the files must not change by a byte.

```python
# robot/simulate.py
def wear_growth(wear, rates, worked, rng):
    # step 1: growth = K_WEAR * rates * worked          (the clean rule)
    # step 2: if WEAR_NOISE: times a lognormal factor per joint, mean 1.
    #         TRAP: draw from rng ONLY inside the "if". A draw outside it
    #         moves the stream when the switch is off, and the old files no
    #         longer reproduce.
    # step 3: if WEAR_ACCEL: times 1 + gain * max(0, wear - 0.6).
    #         think: max(0, ...) matters. Without it a young joint would wear
    #         SLOWER than the clean rule.


def link_mass_factors(seed):
    # one number per link, uniform between 0.97 and 1.03, from its own stream.


# robot/world.py
def connect(gui=False, mass_factors=None):
    # step 1: load the arm as before.
    # step 2: if mass_factors is given: open a SECOND connection and load a
    #         second, untouched arm there. That one is "the model".
    # step 3: on the first arm, multiply each link's mass and inertia by its
    #         factor (getDynamicsInfo, then changeDynamics).
    # step 4: gravity_torque and joint_inertia ask the MODEL arm; the motor
    #         commands and stepSimulation go to the arm that moves.
    # think: a controller only ever has a model. With the switch off the two
    #        are the same arm, which is why gravity cancelled to 0.000007.


# robot/sweep.py
def sensor_faults(rows, rng):
    # step 1: with a small chance, return []: the whole sweep is missing.
    # step 2: for each row: with a smaller chance add or subtract OUTLIER_NM
    #         (sized to the joint), then round to the sensor's step.
    # step 3: build NEW rows; never change the ones you were given.
    # think: who calls this? simulate(), after run_health_check, with a
    #        stream of its own. The sweep itself stays clean, so the same
    #        reading can be compared with and without faults.
```

Check yourself: `tests/test_robot_switches.py`. Two tests are the idea of the
whole part: `test_with_the_switches_off_no_random_number_is_used`, and
`test_the_fit_does_not_take_a_gravity_error_for_coulomb_friction`. Work the
second one out on paper before running it: a gravity error pushes the same
way whichever way the joint turns, and Coulomb friction is the part that
changes sign.

---

## 18. `robot/`: the live demo (milestone M5 of `sim.md`)

```python
# robot/sweep.py
def run_health_check(..., pause=0.0):
    # one added line after stepSimulation: if pause: time.sleep(pause).
    # think: the pause is real time, the physics runs in simulated time.
    #        Waiting changes what you see, not what is measured. The test
    #        checks exactly that: the rows are equal with and without it.


# robot/world.py
def connect(gui=False, ...):
    # p.connect(p.GUI) instead of p.DIRECT; hide the side panels; point the
    # camera at the arm (resetDebugVisualizerCamera).
def is_open(world):      # p.isConnected: False once the window is closed
def show_text(world, text):   # p.addUserDebugText above the arm
def disconnect(world):
    # TRAP: if a person already closed the window, p.disconnect raises.
    #       Ask is_open first.


# tools/robot.py
def live_sweep(joint, wear, seed=0, gui=True, keep_open=True):
    # step 1: the baseline. A sweep of the NEW joint in a world without a
    #         window; keep its fitted Fc.
    # step 2: a world with the window (if gui); sweep with the wear given,
    #         with pause = DEMO_SLOWDOWN * TIMESTEP.
    # step 3: health index = (Fc / Fc new - 1) / WEAR_GAIN_FC. Print it next
    #         to the service threshold, so the number means something.
    # step 4: write it in the window; wait while is_open(world).
    # think: why can a test not use gui=True? It would need a screen and a
    #        person. So everything worth testing must also run with gui=False.


def main(argv=None):
    # --gui: live_sweep, then return. No dataset is written.
```

Check yourself: the `live_sweep` and `--gui` tests in
`tests/test_robot_tool.py`, and
`test_slowing_the_sweep_down_for_the_eye_changes_no_reading` in
`tests/test_robot_sweep.py`. Then run the real thing and look:
`python -m tools.robot demo --gui --joint 3 --wear 0.5`.

---

## 19. `robot/health.py` and `tools/dashboard.py`: reading the sweeps, and showing them

```python
# robot/health.py
def daily_friction(sweeps, joint):
    # step 1: keep the rows of this joint, sorted by day.
    # step 2: np.unique(day, return_index=True) gives each day and where its
    #         rows start. Fit each day's rows with fit_friction.
    # step 3: one row per day THAT HAS A SWEEP. A missing day is a missing
    #         row, never a zero.


def health_index(fc, temperature_c=None):
    # step 1: with temperatures given, divide fc by the warmth factor
    #         1 - TEMP_COEF * (T - 35): that puts every day at 35 C.
    # step 2: the reference. From day 7 on: the mean of the first 7 days.
    #         INSIDE the first 7 days: the mean of the days so far
    #         (cumsum / 1, 2, 3, ...).
    # step 3: index = (fc / reference - 1) / WEAR_GAIN_FC.
    # think: why not simply fc[:7].mean() for every day? Then the value of
    #        day 2 would use days 3 to 6, which had not happened yet. The
    #        test cuts the series at every length and demands the same values.
    # think: this is the same rule as features/relative.py for the bearings.


# tools/dashboard.py
def run_folders(scenario_dir):
    # TRAP: sorted() on names puts run_10 before run_2. Sort by int(name[4:]).


def per_day(days, values, n_days, rounded):
    # a list of n_days entries, None where a day has no sweep.
    # TRAP: NaN is not valid JSON. A browser refuses the whole page. Use None.


def load_run(folder, include_truth):
    # for each joint: daily_friction, the two indexes, one whole sweep every
    # SWEEP_EVERY days. Round everything: full precision triples the file.
    # ground_truth.csv is opened ONLY when include_truth is on.


def render(payload):
    # template text with the JSON put in.
    # TRAP: the JSON sits inside a script block. If any text in it contains
    #       the characters that close a script block, the page breaks (or
    #       worse, runs someone's text as code). Write "<\/" for "</".


def main(argv=None):   # --scenario, --no-truth; writes results/robot/dashboard_<scenario>.html
```

The page itself is `tools/dashboard_template.html`: plain HTML, CSS and
JavaScript, no library. Three ideas run through it. Colours are named by
role at the top and every chart uses the names. Every label is set with
`textContent`, never by gluing text into HTML. And the page never asks the
internet for anything, which one test checks by searching the file.

Check yourself: `tests/test_robot_health.py`, `tests/test_robot_dashboard.py`,
then `python results/2026-10-12_robot_dashboard/check.py`, which opens the
page in Chrome and prods it.

---

## What is not built yet

The first RUL model (it has to beat 0.200 and 0.203), the paired bootstrap of
the adoption rule, the faults part, the robot forecast (the simulator that
feeds it is complete), and the final test.
