# Features: worked example and sanity check

Script: `check.py`. Raw output: `output.txt`. Log of the extraction itself:
`extract_output.txt`. Explained in `docs/GUIDE.md`, section 4.

| Check | Result |
|---|---|
| Worked example (6 made-up snapshots of 8 samples) | every number matches the hand calculation |
| XJTU-SY extraction | 15 bearings, 9216 snapshots, 69 s, 0 missing readings, 1.6 MB cached |
| Relative rms of the last snapshot above 1 | 15 of 15 bearings (4.78 to 22.79, median 13.90) |
| Mean relative rms over the first 10 snapshots | 0.985 to 1.042 for 14 bearings; 1.453 for Bearing3_5 |

**Verdict: kept.** The expectation written in the script before the run is
met. This checks the pipeline; it says nothing yet about predicting remaining
life.

Bearing3_5 was not steady during its healthy start, so its reference is
doubtful (`docs/LIMITS.md`). It is kept in the data.

Only XJTU-SY, the development set, was extracted. IMS and KAIST were not
touched.
