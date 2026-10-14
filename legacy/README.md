# legacy/: the earlier robot simulator, kept for later

`robot_simulator_8/` is the PyQt + PyBullet robot simulator from the earlier
project. It is parked here so it stays with this project. Nothing in robot-pdm
imports it, and it is not part of the results.

## Where it came from

- Source: `~/Documents/FactoryAI/Mechanical/robot_simulator_8`, git commit
  `edce219` (6 Oct 2026, GitHub `johnvu-99/robot-PdM`). Copied on 7 Oct 2026.
- 53 Python files (10,839 lines) plus the two requirements files. Every file
  is byte-for-byte equal to the source (SHA-256, 55 of 55).
- Which files: everything `main.py` imports, directly or through another file.
  No file was edited.

| Folder | Files | What |
|---|---|---|
| `simulator/` | 11 | physics loop, robot loading, joint control, fault injection, thermal model |
| `ui/` | 13 | the PyQt window and its panels |
| `monitoring/` | 7 | telemetry, features, anomaly detector for the simulated joints |
| `predictive/` | 7 | health score, maintenance estimate, event log, old bearing RUL model |
| `datasets/` | 8 | old bearing and gearbox adapters |
| `storage/`, `rendering/` | 5 | CSV logging, model files, camera image |
| `config.py`, `main.py` | 2 | settings, entry point |

11 of the 53 files (1,587 lines: all of `datasets/`, and `rul_model.py`,
`dataset_jobs.py`, `fault_validation.py` in `predictive/`) are old bearing
code. They are here only because the window's RUL tab imports them at
start-up, so the simulator does not start without them.

## How to run it

It needs PyQt5 and pyqtgraph, which the `pdm` environment does not have. Use
the old environment:

```
conda activate mechanical
cd legacy/robot_simulator_8
python main.py
```

It creates `data/` and `models/` inside its own folder when you log or save.

## What was checked

On 7 Oct 2026 the copy was started from this folder without a screen, the
Start command was sent, and it ran for 5 s:

| Check | Result |
|---|---|
| modules loaded from this folder | 52 of 52, none from FactoryAI |
| robot | `kuka_iiwa/model.urdf`, 7 axes |
| physics rate | 238.6 Hz (target 240) |
| speed against real time | 0.99 |
| telemetry snapshots received | 64 |

Not checked: the window on a real screen, the buttons, fault injection, CSV
logging, the RUL tab.

## Limits

- No tests cover the simulator. The old project's tests cover its dataset and
  bearing code and were not copied.
- The RUL tab will not find data by default: it looks in
  `legacy/robot_simulator_8/data/external/`, and it expects PHM 2012, which
  this project does not have.
- The joint maintenance estimate in this simulator is a straight-line fit of
  the health score over the last 60 s (`predictive/health_model.py`, `_trend`).
  It was never validated against a known answer.
- It does not follow the rules in this project's `CLAUDE.md`: it uses PyQt,
  and its maintenance estimate is not the friction-and-schedule forecast
  described there.

## Left in FactoryAI

The tests, `service/` and `tools/` (web dashboard and command-line tools),
`results/`, `models/` (bearing models only), the documents
(`CODE_GUIDE_MECHANICAL.md`, `README.md`, `PARTNER_DATA_SPEC.md`), and 8
Python files in `datasets/` and `predictive/` that the simulator never imports.
