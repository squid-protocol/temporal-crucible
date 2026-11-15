# Blind test of the check, run 1 — result

**2026-11-15.** Amendment 5 section 9, as corrected by its erratum, and `docs/process/comparison_scorer_spec.md`
section 8.

**How it was done.** A separate session (the fault-writer) made 16 numbered copies of decoy study P's reference
side: 8 clean, 8 each carrying one fault of the eight kinds in the specification's table, the assignment drawn
with `secrets.SystemRandom`. It wrote the key — each copy's kind, the exact change, and the layers expected to
fire with the seal withheld — **before anything was run**, locked it, and recorded its SHA-256
(`fee68577…`). The orchestrating session then ran `tools/compare/blind_runner.py` on all 16 copies (10:46 to
11:06 AM Eastern) and **committed the verdicts at 11:07:27 AM (`4a9d146`) before opening the key.** The key's
hash was checked against the recorded one at opening.

## Result: PASS

| copy | the fault (from the key) | layers that fired | expected, seal withheld |
|---|---|---|---|
| 01 | clean | none | none |
| 02 | two pool commits swapped | seal, input check, cell map R | input check, cell map R |
| 03 | clean | none | none |
| 04 | the silent rule put back to its `edc5c53` form | seal, input check, cell map W/D, cell map R | cell map W/D, cell map R |
| 05 | one scan value of the risk score | seal, input check, cell map W/D, cell map R | input check, cell map W/D |
| 06 | the control's checks moved before its draws | seal, cell map W/D, cell map R | cell map R |
| 07 | clean | none | none |
| 08 | clean | none | none |
| 09 | one path removed from the primary outcome | seal, placebo, input check, cell map W/D, cell map R | placebo, input check, cell map W/D |
| 10 | clean | none | none |
| 11 | clean | none | none |
| 12 | two repos swapped in the marginals file | seal, cell map W/D, cell map R | cell map R |
| 13 | one scan value of a confirmatory count predictor | seal, placebo, input check, cell map W/D, cell map R | placebo, input check, cell map W/D, cell map R |
| 14 | the caliper in the statistics module | seal, placebo, cell map W/D, cell map R | placebo, cell map W/D, cell map R |
| 15 | clean | none | none |
| 16 | clean | none | none |

- **Every faulty copy was flagged**, with the seal and with the seal's verdict withheld, by at least the layers
  the fault-writer expected.
- **No clean copy was flagged by any layer.**
- The placebo stayed silent for the risk-score change (copy 05), as the review of the specification predicted
  and the fault-writer had arranged to confirm.
- Layers fired beyond the expected ones in four copies (the control reorder and the repo swap also moved W/D
  cells; the silent-rule and risk-score faults also reached the input check or R cells). Each is explained by
  what the fault changes; none is a false alarm.

## What it shows, and what it does not

It shows that each of these eight kinds of fault, introduced on the reference side, is caught by the
comparison layers alone, without the seal, and that the check raises nothing on unaltered copies. Eight faults
and eight clean copies give no detection or false-alarm **rate**. The faults were chosen from the
specification's table, which was written knowing the layers; a fault of a kind nobody thought of is the case
this test cannot speak to.

Files: `verdicts.json` and `run.log` (committed before the key was opened), `KEY.sha256` (committed with them),
`KEY.json` (committed after).
