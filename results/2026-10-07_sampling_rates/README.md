# Sampling rates of KAIST and of the CWRU normal files

Script: `check.py`. Raw output: `output.txt`. Explained in `docs/GUIDE.md`, section 2.

| Files | Rate adopted | Evidence |
|---|---|---|
| KAIST, all 129 | 25,600 Hz | Mendeley page: 25.6 kHz, 78.125 s per file. Shaft line at 29.9 Hz = 1.01x the documented speed in 8 of 8 signals checked. At 6666.7 Hz it would sit at 7.8 Hz. |
| CWRU, 36 fault files | 12,000 Hz | Documented set ("12k drive end"); shaft line at 1x in 36 of 36. |
| CWRU, 4 normal files | 48,000 Hz | At 48 kHz they show the same lines as the fault files and last 10.1 s like them. At 12 kHz they show lines that 0 to 8% of fault files have. |

**Verdict: kept.** `config.KAIST_FS = 25600`, `config.CWRU_FS_NORMAL = 48000`,
`config.CWRU_FS_FAULT = 12000`.

The earlier project (FactoryAI) used 6666.7 Hz for KAIST. That was wrong by a
factor of 3.84.

This script was written after a first look at the spectra. A first attempt
that looked only for hum at 60 and 180 Hz pointed to 12 kHz for the normal
files; it was wrong because this rig's electrical lines sit at 120, 240, 360
and 720 Hz, which the fault files show.
