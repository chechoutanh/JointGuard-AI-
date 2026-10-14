# Robot simulation, milestone M5: the live demo

Build brief: `sim.md`, milestone M5. Explained in `docs/GUIDE.md`, section 10.

```
python -m tools.robot demo --gui [--joint 3] [--wear 0.5] [--seed 0]
```

It opens a PyBullet window, sweeps one joint whose wear is set by hand, prints the health index it reads back, and writes it above the arm. Close the window to end. Nothing is written to disk.

| File | What it is |
|---|---|
| `check.py`, `output.txt` | The demo's number on every joint at five wear levels, run without the window. About 10 s. |
| `window_run_output.txt` | What the demo printed when it was run once with the real window (joint 3, wear 0.5). |
| `results/robot/demo_view.png` | One frame of the window: the arm in its health-check posture. |

## Does M5 pass?

| The brief's "done when" | Result |
|---|---|
| `python -m tools.robot demo --gui` opens the PyBullet GUI | Yes: the window opened on this Mac and showed the arm (`demo_view.png`). |
| Runs one live sweep | Yes: 18 speeds, 5 times slower than real time, 29 s in all. |
| Prints that joint's health index | Yes: 0.51 for a wear of 0.5. The window run printed the same numbers as the run without a window. |

## The number it prints

Health index for the wear given, one sweep against one baseline sweep of the new joint (`output.txt`):

| Joint | wear 0.0 | wear 0.2 | wear 0.5 | wear 0.8 | wear 1.0 |
|---|---|---|---|---|---|
| 0 | 0.003 | 0.205 | 0.507 | 0.810 | 1.011 |
| 1 | 0.003 | 0.203 | 0.503 | 0.803 | 1.003 |
| 2 | -0.005 | 0.195 | 0.496 | 0.797 | 0.998 |
| 3 | -0.010 | 0.188 | 0.484 | 0.781 | 0.979 |
| 4 | -0.008 | 0.191 | 0.489 | 0.787 | 0.986 |
| 5 | -0.002 | 0.198 | 0.497 | 0.797 | 0.997 |

The largest difference from the wear given is 0.021. Each row is shifted as a whole, because its five numbers share one baseline sweep and that sweep's noise.

## Not checked

- **Closing the window by hand.** The check run closed the window from the program. That the command ends when a person closes the window was not tried.
- **The line of text above the arm.** It is drawn by PyBullet's window and does not appear in a saved frame, so it was not seen.
- **Other computers.** The window was opened on one Mac only.

**Verdict: kept.** M5 passes, with the three points above left for a person to look at.

Everything here is simulation with illustrative parameters. The demo sets a wear by hand and reads it back with the same code, so the agreement is by construction.
