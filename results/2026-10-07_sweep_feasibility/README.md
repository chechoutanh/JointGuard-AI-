# Can the health-check sweep run in plain PyBullet, without the old simulator?

Script: `check.py` (one file, headless, about 1 minute). Raw output:
`output.txt`. Explained in `docs/GUIDE.md`, section 3.

This is a feasibility check for `ROBOT_SIM_DATA_SPEC.md`. It is not the
`robot/` package, and it saves no dataset.

| Question | Result |
|---|---|
| Does the sweep read zero when no friction is injected? | Only after the URDF joint damping is set to 0. As loaded, it reads Fv = +0.53 N m s/rad. |
| Does the fit recover the injected friction on all 7 joints? | Yes, within 0.3%, with friction sized to each joint and gains through the full mass matrix. |
| Same settings, gains from the diagonal only (as the spec says)? | 6 of 7 joints; the held joints run away to 100 rad/s in one sweep. |
| One friction value for every joint? | 4 of 7 joints; worst error 126%. |
| Wear on joint 3 only: other joints' health index? | 0.4999 for joint 3, at most 0.0001 in size elsewhere. |
| Time | 0.17 s per sweep; 7 joints x 365 days in 7 minutes. |

**Verdict: kept.** The spec's method works without the old simulator. Three
settings must differ from what the spec says; they are listed in the guide.

Everything here is simulation. The friction is injected by the same script
that then measures it, so the 0.3% is a check of the method's arithmetic, not
an accuracy claim.
