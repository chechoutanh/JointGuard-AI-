"""Every tunable number of the robot simulation, with its reason.

Everything here is simulation with illustrative parameters. None of these
numbers was measured on a real robot.
"""

import os

import numpy as np

# Where a simulated dataset is written: data/simulation/<scenario>/
SIMULATION_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "simulation")

# Where the collection screen writes: data/collected/<name>/<scenario>/run_<k>/. A folder of its own, so
# that nothing collected by hand can land on the dataset the results were made from.
COLLECTED_DIR = os.path.join(os.path.dirname(SIMULATION_DIR), "collected")

# ---------------------------------------------------------------------------
# The arm
# ---------------------------------------------------------------------------

TIMESTEP = 1 / 1000        # s. At 1/240 torque control is unstable on the wrist joints
GRAVITY = 9.81             # m/s^2

# Joints 0 to 5 wear and are swept. Joint 6, the tool flange, is only held.
N_JOINTS = 6

# The angles (rad) the arm is held at during a health check, one per joint of
# the arm. Bent on purpose: gravity pulls 33 N m on joint 1 and 14 N m on
# joint 3 here, so a mistake in taking gravity out shows up at once.
POSTURE = (0.0, 0.5, 0.0, -1.2, 0.0, 0.8, 0.0)

# Rated speed of each joint, rad/s. Illustrative: slower at the shoulder,
# faster at the wrist. Not read from the robot file, which says 10 rad/s for
# every joint, and not taken from a data sheet.
RATED_RAD_S = np.array([1.5, 1.5, 1.7, 1.3, 2.3, 2.3, 2.3])

# Size of each joint relative to joint 3: its inertia at POSTURE with the other
# joints held (1.542, 2.524, 0.491, 0.526, 0.0167, 0.0108, 0.0006 kg m^2),
# divided by joint 3's. Friction and sensor noise are multiplied by it. With
# one friction value for every joint, a wrist joint runs up to 83% slower than
# asked and only 10 of its 18 speed points can be fitted
# (results/2026-10-09_robot_sweep).
JOINT_SIZE = np.array([2.93, 4.80, 0.93, 1.00, 0.032, 0.021, 0.0011])

# ---------------------------------------------------------------------------
# Friction of joint 3 when new, at TEMP_REF_C. Other joints: times JOINT_SIZE.
# ---------------------------------------------------------------------------

FC0 = 1.80                 # N m. Coulomb: the constant part once the joint moves
FS0 = 2.90                 # N m. Static: the higher value just as it starts to move
FV0 = 0.55                 # N m s/rad. Viscous: the part that grows with speed
VS = 0.05                  # rad/s. Stribeck speed: how fast the static bump dies away
DELTA = 1.5                # shape of that decay
TANH_EPS = 0.01            # rad/s. tanh(v / eps) replaces sign(v), so friction has no jump at rest

WEAR_GAIN_FC = 1.50        # Coulomb = FC0 * (1 + 1.50 * wear): the signal the health index reads
WEAR_GAIN_FS = 1.20        # static grows a little slower than Coulomb
WEAR_GAIN_FV = 0.90        # viscous growth, used only when WEAR_AFFECTS_FV is on
WEAR_AFFECTS_FV = False    # realism switch, off until approved

TEMP_REF_C = 35.0          # deg C at which the numbers above hold
TEMP_COEF = 0.008          # friction falls 0.8% per deg C above the reference (warm grease is thinner)

# ---------------------------------------------------------------------------
# Wear: the hidden state. Each day it grows by K_WEAR * the joint's rate in
# this run * duty.
# ---------------------------------------------------------------------------

FAIL_W = 0.80              # true wear at which the joint needs service
K_WEAR = 1 / 480           # wear per unit of duty per day: at duty 0.6 a joint of rate 1 needs service after 640 days

# How fast each joint wears relative to the others. Spread out so that the six
# joints need service at different times (day 400 to day 914 at base duty).
RATE = np.linspace(0.7, 1.6, N_JOINTS)

# No two robots wear alike. In each run every joint's rate is RATE times a
# factor of its own, lognormal with this spread (about 15%) and mean 1. A
# forecast then cannot know a joint's rate in advance; it has to read it from
# the sweeps. Illustrative; the brief asks for the factors, not for a size.
RATE_SPREAD = 0.15

REGREASE_KEEP = 0.3        # a re-grease leaves this share of the joint's wear

# ---------------------------------------------------------------------------
# The production schedule. Duty is the day's workload: 1 is a full day.
# Planned duty = level * day of the week * spell.
# ---------------------------------------------------------------------------

BASE_DUTY = 0.6            # level before the ramp
RAMP_DUTY = 1.2            # level from the ramp day on: the plant doubles its output

# Day the level jumps. At base duty the joints reach FAIL_W between day 400
# and day 914. ramp_early jumps before all of them, so the jump changes every
# service day. ramp_late jumps after all of them, also for a joint that wears
# 40% slower than its rate, so the jump changes none.
RAMP_DAY = {"ramp_early": 200, "ramp_late": 1500}

# Duty must vary, or "wear per unit of work" cannot be told from "wear per
# day". Both patterns average 1, so the level is also the long-run mean.
WEEK_PATTERN = (1.12, 1.12, 1.12, 1.12, 1.12, 0.90, 0.50)     # day 0 is a Monday; Sunday is half a day
SPELL_DAYS = 28                                               # four whole weeks
SPELL_PATTERN = (1.0, 1.3, 0.8, 1.1, 0.7, 1.1)                # normal, busy, quiet, ...: repeats every 168 days

# What happens differs from the plan: actual = planned * lognormal noise with
# this spread (about 18% from day to day) and mean 1, so the plan is right on
# average.
DUTY_NOISE_SIGMA = 0.18

PAYLOAD_KG = 0.0           # recorded with every sweep; not varied

# ---------------------------------------------------------------------------
# Temperature of each joint at its daily health check
# ---------------------------------------------------------------------------

AMBIENT_C = 26.0           # deg C of the hall: where a joint settles with no work
TEMP_RISE_C = 15.0         # deg C above ambient per unit of duty: the fastest joints sit at 26 + 15 * 0.6 = 35 = TEMP_REF_C at base duty
THERMAL_ALPHA = 0.7        # share of the way to its settling temperature a joint covers in one day

# How fast each joint moves in the work cycle, relative to the wrist. A joint
# that moves more heats more. Illustrative.
WORK_SPEED = np.array([0.6, 0.6, 0.7, 0.7, 1.0, 1.0])

# ---------------------------------------------------------------------------
# Realism switches. All off until approved: with all of them off the
# simulation is the clean one of milestones M1 to M3. (A sixth switch,
# WEAR_AFFECTS_FV, sits with the friction numbers above.)
# ---------------------------------------------------------------------------

WEAR_NOISE = False         # the wear a day adds varies: times a factor of its own for each joint and day
WEAR_NOISE_SIGMA = 0.15    # spread of that factor (about 15%, lognormal, mean 1)

WEAR_ACCEL = False         # wear speeds up late in life
WEAR_ACCEL_FROM = 0.6      # from this wear on, a day adds more than its share ...
WEAR_ACCEL_GAIN = 1.5      # ... by a factor 1 + 1.5 * (wear - 0.6): 1.3 at the service threshold

MODEL_MISMATCH = False     # the arm's links do not weigh what the model thinks, so gravity is not taken out exactly
MASS_ERROR = 0.03          # each link is up to 3% heavier or lighter than in the model, drawn for each run

SENSOR_FAULTS = False      # the torque sensor fails in three ways:
MISSED_SWEEP_SHARE = 0.02  # 2 in 100 sweeps of a joint are missing: no rows for that joint that day
OUTLIER_SHARE = 0.005      # 1 in 200 readings is wild ...
OUTLIER_NM = 0.2           # ... off by this much either way on joint 3 (10 times NOISE_NM). Other joints: times JOINT_SIZE
QUANT_NM = 0.01            # every reading is rounded to this step on joint 3 (half of NOISE_NM). Other joints: times JOINT_SIZE

# ---------------------------------------------------------------------------
# The health-check sweep
# ---------------------------------------------------------------------------

# Time at each speed: settle (thrown away), then record (averaged). The brief
# gives 0.5 s + 0.5 s. With 0.1 s + 0.1 s the fitted friction changes by less
# than 0.0001% (results/2026-10-12_robot_dayloop/sweep_length_output.txt) and a
# day takes 0.3 s of computer time instead of 1.5 s. That is what makes runs
# long enough for every joint to reach service affordable. 0.1 s is 60 times
# the speed loop's own response time (1 / VELOCITY_GAIN).
SETTLE_S = 0.1
RECORD_S = 0.1

# The fit uses speeds of at least 0.08 of rated speed. Far below that the tanh
# smoothing, not the friction, sets the torque.
FIT_MIN_FRAC = 0.08

# Target speeds as a share of rated speed: 9 each way, evenly spaced in ratio.
# They start at 0.10, not at the fit limit of 0.08, because the speed loop
# always runs slower than asked: 5% on a new joint, 13% on a worn and cold one.
# A target of 0.08 is measured at 0.075 or less, and the fit would throw that
# point away on every sweep (16 of 18 points used instead of 18).
SPEED_FRACS = np.concatenate([-np.geomspace(0.10, 0.80, 9)[::-1], np.geomspace(0.10, 0.80, 9)])

# Speed loop of the swept joint: torque = gravity + gain * joint inertia *
# (target speed - speed), gain in 1/s. Each time step it removes
# gain * TIMESTEP = 0.6 of the speed error. Above 2 the loop is unstable.
VELOCITY_GAIN = 600.0

# The held joints are locked by the engine's position motor with up to this
# torque (N m): 6 times the largest gravity torque met in a sweep (46 N m).
HOLD_FORCE_NM = 300.0

# Sensor noise on each recorded torque of joint 3, N m (1.1% of FC0). Other
# joints: times JOINT_SIZE, as a torque sensor is sized to its joint.
NOISE_NM = 0.02

# The health index compares a joint with its own first days: the reference is
# the mean fitted Coulomb friction of this many days. A week covers one full
# weekly pattern of work and temperature. Wear in that week is about 0.005.
BASELINE_DAYS = 7

# The camera of the window and of the collection screen: where it looks (m),
# from how far (m), turned and tilted by how much (deg). Chosen by eye so that
# the whole arm is in view at the health-check posture.
CAMERA_TARGET = (0.2, 0.0, 0.35)
CAMERA_DISTANCE = 1.1
CAMERA_YAW = 50
CAMERA_PITCH = -20

# The live demo shows a sweep this many times slower than real time, so that
# each of the 18 speeds is on screen for 1 s instead of 0.2 s. The readings
# are the same: only the pause between time steps changes.
DEMO_SLOWDOWN = 5
