# The dashboard of the simulated robot

Not a milestone of `sim.md` (that brief ends at M5): the user asked for it on 12 Oct 2026. Explained in `docs/GUIDE.md`, section 11.

```
python -m tools.dashboard [--scenario ramp_early] [--no-truth]
```

It reads `data/simulation/<scenario>/run_<k>/` and writes `results/robot/dashboard_<scenario>.html`: one file that opens in any browser without internet or a server. `--no-truth` leaves the hidden wear out of the file altogether.

| File | What it is |
|---|---|
| `check.py`, `output.txt` | Builds both pages, opens one in headless Chrome, and prods every control. About 1 minute. |
| `results/robot/dashboard_ramp_early.html`, `dashboard_ramp_late.html` | The two pages (1.9 MB and 3.3 MB). |
| `results/robot/dashboard_ramp_early_light.png`, `..._dark.png` | Pictures of the page, joint 4 chosen and the answer key shown. |

## What the page shows

- **Filters, one row:** robot (0 to 4), joint for the detail charts, a day slider ("show the robot as of day ..."), and a switch for the answer key.
- **Six tiles:** each joint's health index on the chosen day, as a share of the service threshold, with "Service due since day ..." once it is reached.
- **Health index of every joint** over the whole run, with the threshold and the day the planned workload doubles. Days after the chosen day are faded.
- **One joint:** its index with and without the temperature taken out, and with the answer key on, the hidden wear and the true service day.
- **One sweep** of that joint (friction torque against speed) next to the sweep of the new joint.
- **Workload** (planned and actually done) and **temperature**, as 7-day means.

A view can be opened directly: `dashboard_ramp_early.html?run=2&joint=4&day=600&truth=1&theme=dark`.

## Does it work?

Checked in headless Chrome 154 at 1280 px (`output.txt`):

| Check | Result |
|---|---|
| The page loads and finishes drawing | yes, no script error |
| Pointer over the overview chart | one tooltip with the day and all six joints; it goes when the pointer leaves |
| Keyboard: focus, then the right arrow | tooltip moves from day 341 to day 342 |
| Click on the chart | the chosen day changes to day 212 and the tiles follow (0 joints due instead of 1) |
| Click on a tile | the detail charts switch to that joint |
| Answer key switch | the detail chart gains the hidden-wear line; the tiles show wear and service day |
| Pointer near a dot of the sweep | tooltip with torque and speed of that dot |
| Other robot, day 0 | six tiles; the first reads 0.00 |
| Table view of the overview | 122 rows, every 7th day |
| Six joint colours, colour-blind check | pass in light and dark; three are below 3:1 contrast on the light background, which is why every chart also has a table |

## One thing the page gets slightly wrong

The tiles flag "service due" on the first day the health index reaches 0.8. That is later than the true service day: 4.0 days on average in the early ramp (1 to 9) and 7.5 days in the late ramp (-6 to 16), over 30 joints each. The index compares a joint with its own first week, when it already has a little wear, so it reads slightly low.

## Not checked

- **By a person.** Everything above was done by a script and by looking at two pictures. Nobody has used the page.
- **Other browsers and small screens.** Chrome at 1280 px only. Safari, Firefox and a phone were not tried.
- **Touch.** The charts answer to a mouse and to the keyboard.

**Verdict: kept.**

Everything here is simulation with illustrative parameters. The page shows a wear that was set by hand and read back by the same code. It has no forecast, because none is built.
