# The three baselines on XJTU-SY

Command: `python -m tools.rul evaluate`. Raw output: `output.txt`. Explained in
`docs/GUIDE.md`, section 5.

These are the reference lines that every later results table must carry. There
is no model here yet.

## Expectations, written before the first run (8 Oct 2026)

1. **Constant 0.5:** MAE just above 0.250 (0.250 exactly only for an endless
   number of snapshots), so it beats 0.250 on 0 of 15 bearings. Near-failure
   recall 0, rank 0, triage 0.50. Its interval is the trivial one: coverage
   about 0.90 at a width of about 0.90.
2. **Elapsed time:** worse than the constant in both splits. Lives differ by a
   factor of 60 (0.68 to 42.3 h), so "it will live as long as the median
   bearing" is badly wrong for most. Rank within a bearing still high, because
   the clock only runs one way: that is why rank within is not the headline.
3. **Rms only:** better than the constant when leaving one bearing out, and
   weaker when leaving a whole condition out. Some near-failure recall, and a
   triage score above 0.50.

## Results

Leave one bearing out (15 folds):

| Predictor | MAE | Beat 0.250 | Near-failure recall | % of hours left | Rank within | Triage | Coverage | Width |
|---|---|---|---|---|---|---|---|---|
| constant 0.5 | 0.252 | 0 of 15 | 0.00 | 83% | 0.00 | 0.50 | 0.90 | 0.90 |
| elapsed time | 0.317 | 3 of 15 | 0.47 | 112% | 0.86 | 0.66 | 0.87 | 0.73 |
| rms only | 0.200 | 10 of 15 | 0.37 | 71% | 0.70 | 0.68 | 0.86 | 0.69 |

Leave one condition out (3 folds):

| Predictor | MAE | Beat 0.250 | Near-failure recall | % of hours left | Rank within | Triage | Coverage | Width |
|---|---|---|---|---|---|---|---|---|
| constant 0.5 | 0.252 | 0 of 15 | 0.00 | 83% | 0.00 | 0.50 | 0.90 | 0.90 |
| elapsed time | 0.329 | 2 of 15 | 0.53 | 100% | 0.86 | 0.65 | 0.74 | 0.62 |
| rms only | 0.203 | 10 of 15 | 0.43 | 66% | 0.72 | 0.70 | 0.83 | 0.67 |

## Expectations against results

1. Constant: met.
2. Elapsed time: met. One thing I did not foresee: its near-failure recall
   (0.47) is above rms only's (0.37), because it says "failed" too early for
   every bearing that outlives the median.
3. Rms only: half met. It beats the constant with one bearing left out
   (0.200, 10 of 15). It is **not** weaker with a condition left out (0.203,
   the same 10 of 15). That expectation was wrong.

## Verdict

**Kept, as the reference rows.** Rms only is a weak predictor: 21% better than
knowing nothing, worse than knowing nothing on 5 of 15 bearings, hours off by
71% of the true hours left, and 90% ranges that hold 86%.

`worked_example.py` runs one made-up bearing through every metric; its output
matches the hand calculation in the guide.
