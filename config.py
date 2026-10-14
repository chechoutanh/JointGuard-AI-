"""Every tunable setting, with the reason next to it."""

import os

ROOT = os.path.dirname(os.path.abspath(__file__))
EXTERNAL_DIR = os.path.join(ROOT, "data", "external")
PROCESSED_DIR = os.path.join(ROOT, "data", "processed")

XJTU_DIR = os.path.join(EXTERNAL_DIR, "XJTU-SY_Bearing_Datasets")
IMS_DIR = os.path.join(EXTERNAL_DIR, "IMS", "unpacked")
KAIST_DIR = os.path.join(EXTERNAL_DIR, "KAIST", "run_to_failure")
SEU_DIR = os.path.join(EXTERNAL_DIR, "Mechanical-datasets", "gearbox")
CWRU_DIR = os.path.join(EXTERNAL_DIR, "Mechanical-datasets", "dataset")

# ---------------------------------------------------------------------------
# Sampling rates
#
# Only the SEU files store their rate. The other files hold samples and nothing
# else, so these rates come from each dataset's documentation. Where the
# documentation was in doubt the rate was checked against the signal itself
# (results/2026-10-07_sampling_rates).
# ---------------------------------------------------------------------------

# XJTU-SY: 25.6 kHz in the dataset paper. Each file has 32768 rows, which is the
# documented 1.28 s at that rate. One snapshot per minute.
XJTU_FS = 25600.0
XJTU_STEP_MINUTES = 1.0

# IMS: the readme says 20 kHz and 1 s per file, but each file has 20480 rows.
# One of the two numbers is rounded, so the true rate is 20.0 or 20.48 kHz
# (2.4% apart). The readme's 20 kHz is used. See docs/LIMITS.md.
IMS_FS = 20000.0

# IMS snapshot times come from the file names. Test 1 stopped for long periods
# (59% of its calendar span). A stopped rig does not wear the bearing, so a step
# longer than this counts as this long. None means plain calendar time.
# Chosen on physical grounds before looking at any IMS signal.
IMS_MAX_STEP_MINUTES = 10.0

# KAIST: the Mendeley Data page (version 6) says 25.6 kHz and 78.125 s per file,
# which is exactly the 2,000,000 rows of each file. The shaft-speed line sits at
# 29.9 Hz under this rate, as documented (1770 to 1780 rpm).
KAIST_FS = 25600.0
# Each file holds 78 s; reading all 129 would be 17 GB of text. The first 10 s
# are 256,000 samples, enough for a spectrum with 0.1 Hz resolution.
KAIST_SNAPSHOT_SECONDS = 10.0

# SEU: the file header gives the analyser's frequency limit (2000 Hz). Such
# analysers sample at 2.56 times that limit: 5120 Hz. Cross-check from the same
# header: 1600 spectral lines x 2.56 = 4096 samples per block, and
# 1024 blocks x 4096 = 4,194,304, the "Total Data Rows" the header states.
SEU_FS_PER_FREQUENCY_LIMIT = 2.56

# CWRU: the fault files here are the "12k drive end" set (records 105 to 237).
# The normal files (records 97 to 100) are 48 kHz: read at 48 kHz they show the
# same spectral lines as all 36 fault files (1x, 2x, 4x, 4.94x, 5.4x, 6.4x shaft
# speed; 120, 240, 360, 720 Hz) and last 10.1 s like them. Read at 12 kHz they
# would show lines that no fault file has, and last 40 s.
CWRU_FS_FAULT = 12000.0
CWRU_FS_NORMAL = 48000.0

# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------

# Frequency bands in Hz, shared by the three run-to-failure sources so that a
# feature means the same thing in each. The lowest Nyquist frequency among them
# is 10 kHz (IMS, sampled at 20 kHz); the top edge stays at 8 kHz, below it and
# clear of the roll-off near it. 10 Hz at the bottom leaves out sensor drift.
# Bearing defect lines and their first multiples sit below 500 Hz; the impacts
# they cause ring the structure in the kHz bands. One band per octave above
# 500 Hz. Not tuned on any result.
RUL_BANDS_HZ = ((10, 500), (500, 1000), (1000, 2000), (2000, 4000), (4000, 8000))
BANDS_HZ = {"xjtu": RUL_BANDS_HZ, "ims": RUL_BANDS_HZ, "kaist": RUL_BANDS_HZ}

# The healthy reference of a unit is the median of its first snapshots. Total
# life is unknown while predicting, so this is a count, never a share of life.
# 10 is a first choice, not a tuned one: a median of 10 shrugs off a few odd
# snapshots, but for the shortest XJTU-SY bearing (42 snapshots) it is already
# 24% of its life. See docs/LIMITS.md.
HEALTHY_SNAPSHOTS = 10

# ---------------------------------------------------------------------------
# RUL evaluation
# ---------------------------------------------------------------------------

# "Near failure" is the last fifth of a bearing's life: late enough that
# maintenance is urgent, long enough to hold several snapshots of even the
# shortest bearing (42 snapshots, so 8).
NEAR_FAILURE_SHARE = 0.2

# A prediction comes with a range meant to hold the truth 90% of the time.
INTERVAL_SHARES = (0.05, 0.95)

# The triage score compares snapshots of different bearings. Each bearing is
# read at these shares of its life, so a bearing with 2538 snapshots counts no
# more than one with 42.
TRIAGE_LIFE_SHARES = (0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95)

# The rms-only baseline sorts training snapshots into this many groups of equal
# weight by vibration level. With 14 training bearings, 10 groups leave each
# with the weight of 1.4 bearings. A first choice, not tuned.
RMS_MODEL_BINS = 10
