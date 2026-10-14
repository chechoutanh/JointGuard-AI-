# Do the five adapters load the real data?

Command: `python -m tools.sources`. Raw output: `output.txt`. Explained in
`docs/GUIDE.md`, section 1.

| Source | Recordings | Snapshots | Rate | One snapshot | Missing readings (first + last snapshot) |
|---|---|---|---|---|---|
| XJTU-SY | 15 bearings | 9216 | 25,600 Hz | 32,768 samples x 2 channels, 1.28 s | 0 |
| IMS | 4 bearings in 3 runs | 11,620 | 20,000 Hz | 20,480 x 1 or 2, 1.02 s | 0 |
| KAIST | 1 bearing | 129 | 25,600 Hz | 256,000 x 2, 10 s | 80 |
| SEU | 20 files | 20 | 5,120 Hz | 1,048,560 x 8, 204.8 s | 0 |
| CWRU | 40 files | 40 | 12,000 / 48,000 Hz | 121,265 to 485,643 x 2, 5.1 to 10.2 s | 0 |

**Verdict: kept.** All five load, in 8 s, and no two recordings hold the same
signal. 25 tests on synthetic files pass.

Nothing here is a result about bearings or faults: only the first and last
snapshot of each recording were read, and no feature was computed.
