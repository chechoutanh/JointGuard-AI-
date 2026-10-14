"""Development evaluation on XJTU-SY: every predictor, both splits, every metric.

    python -m tools.rul evaluate

Needs the cached features: python -m tools.features xjtu
"""

import argparse

from rul.data import load_units
from rul.evaluate import evaluate, leave_one_bearing_out, leave_one_condition_out, summarise


def print_split(title, units, folds):
    result = evaluate(units, folds)
    names = list(result)
    print(f"\n{title}: {len(units)} bearings, {len(folds)} folds")
    print(f"  {'predictor':13s} {'MAE':>6s} {'beat 0.250':>10s} {'near-fail recall':>16s} {'hours err':>9s} "
          f"{'% of left':>9s} {'rank within':>11s} {'triage':>6s} {'coverage':>8s} {'width':>6s}")
    for name in names:
        s = summarise(result[name])
        beat = f"{s['beat_guessing']} of {s['bearings']}"
        print(f"  {name:13s} {s['mae']:6.3f} {beat:>10s} {s['recall']:16.2f} "
              f"{s['hours_error']:9.2f} {s['percent_error']:8.0f}% {s['rank']:11.2f} {s['triage']:6.2f} "
              f"{s['coverage']:8.2f} {s['width']:6.2f}")

    print("\n  MAE of each bearing")
    print(f"  {'bearing':12s} {'condition':12s} {'life h':>7s} " + " ".join(f"{name:>13s}" for name in names))
    for i, row in enumerate(result[names[0]]["bearings"]):
        print(f"  {row['unit_id']:12s} {row['condition']:12s} {row['life_hours']:7.2f} "
              + " ".join(f"{result[name]['bearings'][i]['mae']:13.3f}" for name in names))


def main(argv=None):
    parser = argparse.ArgumentParser(description="RUL evaluation on XJTU-SY.")
    parser.add_argument("command", choices=["evaluate"])
    parser.parse_args(argv)

    units = load_units("xjtu")
    print_split("leave one bearing out", units, leave_one_bearing_out(units))
    print_split("leave one condition out", units, leave_one_condition_out(units))


if __name__ == "__main__":
    main()
