# The founding claim, re-run on curl with an audited label (2026-11-13)

**Claim:** a file's count of prior fix commits orders its next-window fixes better than LOC does. Established
on curl + nDPI at p<1e-4; curl's half is re-run here on a label whose precision is now measured.

Design is HR-1's, unchanged (`docs/hist_replication.md`): cut at the 80th percentile of commit time
(2024-03-27), outcome = any fix commit in the following 24 months, predictor = prior fix count, baseline =
`total_loc` at the nearest scanned snapshot, bots and merges excluded. 1,020 files. New layers built for this:
a 105-snapshot quarterly walk (1999-2026, 0 failed) and a 40,187-commit history.

**Label transfer verified first:** 99% of curl's LAWS `fix` set appears in xc's events, and 99% of the v3c
set in xc's cleaned events — so the audited 0.63 / 0.80 precisions apply to the label actually used.

## Result

| label | precision | positives | AUC(LOC) | AUC(recidivism) | **lift** | 95% CI |
|---|---|---|---|---|---|---|
| raw | 0.63 (under gate) | 414 | 0.612 | 0.945 | **+0.333** | [+0.300, +0.371] |
| **v3c** | **0.80** | 216 | 0.830 | 0.901 | **+0.071** | **[+0.040, +0.104]** |

Effort-aware, at a 20%-of-lines review budget: LOC catches 4.6% of the fixes, recidivism **11.6%** — about
2.5x better.

## Reading

**The claim survives on curl.** On an audited 0.80 label the lift is +0.071 with an interval that excludes
zero. Prior fixes really do order curl's future fixes better than size does.

**It was inflated about 4.7x by label noise.** +0.333 → +0.071. As everywhere else, `AUC(LOC)` *rises* when
the label is cleaned (0.612 → 0.830): size predicts real fixes far better than it predicts housekeeping, and
the raw label's enormous lift was substantially recidivism predicting repeat cosmetic churn.

**This is the first place the cleaning did not kill the effect**, and that is the finding. On the CGR eight
the same cleaning took pooled lift from +0.082 to +0.009 with the interval crossing zero. On curl it takes
+0.333 to +0.071 with the interval still clear of zero. **So the collapse is not universal — it is
cohort-dependent, and curl is genuinely different from the eight.**

## What this does not settle

- **One repo.** The founding claim was curl **and** nDPI. nDPI's label is still 0.68, under the gate, and it
  has no walk, so its half cannot be re-run yet. "Replicated on two repos" currently stands on one.
- **Recall is still unmeasured.** v3c's precision is 0.80; what fraction of real fixes it *discards* is
  unknown, and rule C drops fixes whose subject lacks a fix word. If those discards correlate with
  recidivism, bias survives the cleaning. That measurement is the next one.
- **Effect size is now modest.** +0.071 AUC is a real but small edge over a line count, not the dominant
  signal the raw number implied. Any product claim should quote this number, not the old one.
