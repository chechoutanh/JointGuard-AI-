# Datasets

None of the raw data is committed. `.gitignore` excludes `data/external/`.
Each dataset belongs to the institution that published it; this file records
where it comes from, what to cite, and where it sits on disk.

None of these datasets is robot telemetry. They come from bearing and gearbox
test rigs.

| Source | Role | Folder in `data/external/` | Files | Size |
|---|---|---|---|---|
| XJTU-SY | RUL development | `XJTU-SY_Bearing_Datasets/` | 9216 CSV, 15 bearings | 11 GB |
| IMS (NASA) | RUL final test | `IMS/archives/`, `IMS/unpacked/` | 3 `.rar`; all three tests unpacked (9464 files) | 1.0 GB + 6.1 GB unpacked |
| KAIST | RUL final test | `KAIST/run_to_failure/` | 129 CSV | 17 GB |
| SEU | fault classes and anomaly | `Mechanical-datasets/gearbox/` | 20 CSV | 1.5 GB |
| CWRU | fault classes | `Mechanical-datasets/dataset/` | 40 `.mat` | 134 MB |

## Licence status

Only KAIST's licence has been checked. Until the others are, `data/processed/`
is also gitignored and no derived features or trained models are committed.

| Source | What is known | Checked |
|---|---|---|
| XJTU-SY | no licence file ships with the data; the authors ask for the citation below | no |
| IMS | NASA asks that the repository and the donor are acknowledged | no |
| KAIST | CC BY 4.0, as stated by the Mendeley Data record of version 6 | yes, 7 Oct 2026 |
| SEU | the GitHub repository has no licence file | no |
| CWRU | CWRU asks that the Bearing Data Center is acknowledged as the source | no |

## XJTU-SY

- **Source:** https://github.com/WangBiaoXJTU/xjtu-sy-bearing-datasets (the
  repository links to download mirrors; the data is not in the repository).
- **Publisher:** Institute of Design Science and Basic Components, Xi'an
  Jiaotong University, with Changxing Sumyoung Technology Co., Ltd.
- **Contents:** 15 bearings run to failure under three conditions. One 1.28 s
  snapshot per minute at 25.6 kHz, two channels (horizontal, vertical).
- **Cite:** B. Wang, Y. Lei, N. Li and N. Li, "A Hybrid Prognostics Approach
  for Estimating Remaining Useful Life of Rolling Element Bearings," *IEEE
  Transactions on Reliability*, vol. 69, no. 1, pp. 401-412, 2020.
- **Layout:** `<condition>/<bearing>/<n>.csv`, one file per snapshot.

Snapshots per bearing, counted on 7 Oct 2026. One snapshot per minute, so the
count is also the life in minutes.

| Condition | Bearing 1 | Bearing 2 | Bearing 3 | Bearing 4 | Bearing 5 |
|---|---|---|---|---|---|
| `35Hz12kN` (Bearing1_x) | 123 | 161 | 158 | 122 | 52 |
| `37.5Hz11kN` (Bearing2_x) | 491 | 161 | 533 | 42 | 339 |
| `40Hz10kN` (Bearing3_x) | 2538 | 2496 | 371 | 1515 | 114 |

Lives differ by a factor of 60 (42 to 2538 minutes).

## IMS (NASA)

- **Source:** NASA Prognostics Data Repository,
  https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/
  (direct file: `https://phm-datasets.s3.amazonaws.com/NASA/4.+Bearings.zip`).
- **Publisher:** Center for Intelligent Maintenance Systems (IMS), University
  of Cincinnati, with Rexnord Corp.
- **Contents:** three tests, four bearings on one shaft at 2000 rpm, 6000 lb
  radial load. 1 s snapshots (20,480 samples at 20 kHz) every 10 minutes. Only
  the four bearings that failed are used: test 1 bearings 3 and 4, test 2
  bearing 1, test 3 bearing 3.
- **Cite:** H. Qiu, J. Lee, J. Lin, "Wavelet filter-based weak signature
  detection method and its application on roller bearing prognostics,"
  *Journal of Sound and Vibration* 289 (2006) 1066-1090.
- **Layout:** `IMS/archives/1st_test.rar`, `2nd_test.rar`, `3rd_test.rar`, plus
  the readme PDF. Unpacked files go to `IMS/unpacked/<folder inside the
  archive>/`. One text file per snapshot, named by its time
  (`2004.02.12.10.32.39`), 20,480 rows, tab separated, one column per channel.

| Test | Folder inside the archive | Snapshots | Channels | Unpacked size | Failed bearing: columns (first is 1) |
|---|---|---|---|---|---|
| 1 | `1st_test/` | 2156 | 8 (two per bearing) | 2363 MB | bearing 3: 5 and 6, inner race; bearing 4: 7 and 8, roller |
| 2 | `2nd_test/` | 984 | 4 (one per bearing) | 519 MB | bearing 1: 1, outer race |
| 3 | `4th_test/txt/` | 6324 | 4 (one per bearing) | 3340 MB | bearing 3: 3, outer race |

The third archive really does unpack to a folder called `4th_test`. The
column numbers and the failed bearings were checked against the readme PDF on
7 Oct 2026. The readme also says: "Each file consists of 20,480 points with
the sampling rate set at 20 kHz", and calls each file a 1-second snapshot.
Both cannot be exact; see `docs/LIMITS.md`.

**Test 3: the readme and the archive disagree about the end.** The readme
says test 3 ran from 4 Mar 2004 09:27:46 to 4 Apr 2004 19:01:57 with 4,448
files, and that the outer race of bearing 3 failed at the end. The archive
holds 6,324 files, to 18 Apr 2004 02:42:55. Exactly 4,448 of them are dated
up to 4 Apr 19:01:57, and the next file follows 10 minutes later with no
gap. So the readme describes the first 70% of what is in the archive. The
adapter takes the last file (18 Apr) as the failure. See `docs/LIMITS.md`.

**State on 7 Oct 2026:** all three tests are unpacked (9464 files, 6222 MB).
Every file has the size the archive lists (2156 of 2156, 984 of 984 and 6324
of 6324), and a sample of 40 files per test has 20,480 rows and the expected
8 or 4 columns. Unpacking test 3 left 590 MB free on the system disk; the
user chose this knowing the number. `unpacked/` can always be rebuilt from
`archives/` (`bsdtar -xf archives/<test>.rar -C unpacked`); the archives
cannot. If the disk runs short, `unpacked/` is the folder to give back first.

**Snapshot times, read from the file names.** The step is not always 10
minutes, so the time of each snapshot must come from its name.

| Test | First | Last | Calendar span | Steps of about 10 min | Shorter than 9 min | Longer than 11 min | Total of the long gaps |
|---|---|---|---|---|---|---|---|
| 1 | 22 Oct 2003 12:06 | 25 Nov 2003 23:39 | 827.6 h | 1964 | 167 | 24 | 486.3 h |
| 2 | 12 Feb 2004 10:32 | 19 Feb 2004 06:22 | 163.8 h | 983 | 0 | 0 | 0 h |
| 3 | 4 Mar 2004 09:27 | 18 Apr 2004 02:42 | 1073.3 h | 6315 | 4 | 4 | 20.5 h |

Test 1 stopped for long periods (the longest gaps are 148, 97 and 91 hours):
59% of its calendar span is gaps. Whether those gaps count as bearing life
changes the RUL target for its two bearings, so the choice must be made and
written down before the final test, not after seeing a result.

## KAIST

- **Source:** Mendeley Data, https://data.mendeley.com/datasets/5hcdd3tdvb/6
  (DOI 10.17632/5hcdd3tdvb.6).
- **Publisher:** Human Lab., Center for Noise and Vibration Control Plus, Dept.
  of Mechanical Engineering, KAIST.
- **Contents:** one NSK 6205 ball bearing run to natural failure at 1770 to
  1780 rpm, 128 working hours. One record per hour, 78.125 s long at 25.6 kHz
  (2,000,001 rows, no header: vibration x, vibration y, bearing temperature,
  room temperature). The rate is not in the files; it comes from the Mendeley
  page and was checked against the signal (`docs/GUIDE.md`, section 2). The
  earlier project read these files as 5 minutes at 6666.7 Hz, which was wrong.
  Some readings are missing and stored as `NaN`.
- **Cite:** W. Jung, S.-H. Yun, Y.-H. Park, "Vibration, and temperature
  run-to-failure dataset of ball bearing for prognostics," *Data in Brief*
  (2024).
- **Layout:** `KAIST/run_to_failure/LogFile_<date>-<time>.csv`. Only the first
  10 s of each file are read.

## SEU

- **Source:** https://github.com/cathysiyu/Mechanical-datasets, commit
  `9732a28` (16 Jan 2018).
- **Publisher:** Southeast University, China.
- **Contents:** `gearbox/gearset` and `gearbox/bearingset`, 10 CSV files each
  (5 classes, conditions `20_0` and `30_2`). 8 channels: motor vibration,
  planetary gearbox vibration x/y/z, motor torque, parallel gearbox vibration
  x/y/z. 5120 Hz, read from each file's header (frequency limit 2000 Hz
  times 2.56). 16 header lines; 19 files are tab separated and
  `bearingset/ball_20_0.csv` is comma separated. Each header states 4,194,304
  rows but each file holds 1,048,560 (204.8 s): a quarter of the recording.
- **Cite:** S. Shao, S. McAleer, R. Yan and P. Baldi, "Highly Accurate Machine
  Fault Diagnosis Using Deep Transfer Learning," *IEEE Transactions on
  Industrial Informatics*, vol. 15, no. 4, pp. 2446-2455, 2019.

## CWRU

- **Source:** https://engineering.case.edu/bearingdatacenter. The files here
  are the subset distributed inside the SEU repository above.
- **Publisher:** Case Western Reserve University Bearing Data Center.
- **Contents:** 40 `.mat` files: `normal_<load>`, `B` (ball), `IR` (inner
  race) and `OR` (outer race) at fault diameters 0.007, 0.014 and 0.021 inch,
  loads 0 to 3 hp. The fault files are records 105 to 237, the "12k drive end"
  set: the damaged bearing is the drive-end one, sampled at 12 kHz, about 10 s
  each. Every file holds a drive-end and a fan-end sensor; the fan-end sensor
  is the one the SEU paper used. The normal files (records 97 to 100) are
  48 kHz (`docs/GUIDE.md`, section 2). No rate is stored in the files.
- **Trap:** `normal_2.mat` holds record 99 and also a copy of record 98, which
  is `normal_1`'s signal. `normal_1` and `normal_2` store no shaft speed.

## How the data got here

On 7 Oct 2026 the four folders were cloned from the earlier project
(`~/Documents/FactoryAI/Mechanical/robot_simulator_8/data/external/`) with APFS
clones. A clone is a second name for the same disk blocks: it took no extra
space, and changing or deleting a file in one folder does not affect the other.

It is still one physical copy on one disk. There is no backup. Deleting the
data from one project frees no space until it is deleted from both.

Left behind in FactoryAI: PHM 2012 (out of scope), the empty `partner/` folder,
and the `.git` folder of the SEU repository (505 MB of history; the commit is
recorded above).

Check after cloning, old folder against new:

| Source folder | Files | Bytes | Names, sizes and dates equal | SHA-256 sample |
|---|---|---|---|---|
| `XJTU-SY_Bearing_Datasets` | 9217 | 12.22 GB | yes | 25 of 25 match |
| `IMS` | 4 | 1.06 GB | yes | 4 of 4 match |
| `KAIST` | 129 | 18.53 GB | yes | 3 of 3 match |
| `Mechanical-datasets` | 65 | 1.74 GB | yes | 25 of 25 match |

Bytes are decimal gigabytes; the sizes in the first table are what `du -h`
reports. Free disk space was 2758 MB before cloning and 2754 MB after.
