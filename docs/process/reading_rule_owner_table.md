# The corrected reading rule — the table for the owner

Generated from `tools/compare/reading.py` (equal, on every input tried, to the second build `reading_b.py` and to the
reviewer's own transcription of the reference: 327,680 inputs, 0 differences). The coded reading is the confirmatory
one; the corrected reading is printed beside it (Amendment 5 section 2). The exhaustive table of every input is
`docs/process/reading_rule_table.md`; this one shows each correction on its own.

Tests are listed in Holm order (smallest p first). "Holm sentence" = "not detected (Holm: an earlier test in the family failed)".

## 1. Change 1 (defect 42): a contradicted test no longer stops the step-down

Each test's two statistics read the same here, so change 2 does not act. Control supported, gate passed.

| primary, in Holm order | coded | corrected | differs |
|---|---|---|---|
| supported · supported · supported | supported, defect-specific · supported, defect-specific · supported, defect-specific | supported, defect-specific · supported, defect-specific · supported, defect-specific |  |
| supported · supported · contradicted | supported, defect-specific · supported, defect-specific · contradicted | supported, defect-specific · supported, defect-specific · contradicted |  |
| supported · supported · not detected | supported, defect-specific · supported, defect-specific · not detected | supported, defect-specific · supported, defect-specific · not detected |  |
| supported · supported · not fitted | supported, defect-specific · supported, defect-specific · not fitted | supported, defect-specific · supported, defect-specific · not fitted |  |
| supported · contradicted · supported | supported, defect-specific · contradicted · Holm sentence | supported, defect-specific · contradicted · supported, defect-specific | **yes** |
| supported · contradicted · contradicted | supported, defect-specific · contradicted · contradicted | supported, defect-specific · contradicted · contradicted |  |
| supported · contradicted · not detected | supported, defect-specific · contradicted · not detected | supported, defect-specific · contradicted · not detected |  |
| supported · contradicted · not fitted | supported, defect-specific · contradicted · not fitted | supported, defect-specific · contradicted · not fitted |  |
| supported · not detected · supported | supported, defect-specific · not detected · Holm sentence | supported, defect-specific · not detected · Holm sentence |  |
| supported · not detected · contradicted | supported, defect-specific · not detected · contradicted | supported, defect-specific · not detected · contradicted |  |
| supported · not detected · not detected | supported, defect-specific · not detected · not detected | supported, defect-specific · not detected · not detected |  |
| supported · not detected · not fitted | supported, defect-specific · not detected · not fitted | supported, defect-specific · not detected · not fitted |  |
| supported · not fitted · supported | supported, defect-specific · not fitted · Holm sentence | supported, defect-specific · not fitted · Holm sentence |  |
| supported · not fitted · contradicted | supported, defect-specific · not fitted · contradicted | supported, defect-specific · not fitted · contradicted |  |
| supported · not fitted · not detected | supported, defect-specific · not fitted · not detected | supported, defect-specific · not fitted · not detected |  |
| supported · not fitted · not fitted | supported, defect-specific · not fitted · not fitted | supported, defect-specific · not fitted · not fitted |  |
| contradicted · supported · supported | contradicted · Holm sentence · Holm sentence | contradicted · supported, defect-specific · supported, defect-specific | **yes** |
| contradicted · supported · contradicted | contradicted · Holm sentence · contradicted | contradicted · supported, defect-specific · contradicted | **yes** |
| contradicted · supported · not detected | contradicted · Holm sentence · not detected | contradicted · supported, defect-specific · not detected | **yes** |
| contradicted · supported · not fitted | contradicted · Holm sentence · not fitted | contradicted · supported, defect-specific · not fitted | **yes** |
| contradicted · contradicted · supported | contradicted · contradicted · Holm sentence | contradicted · contradicted · supported, defect-specific | **yes** |
| contradicted · contradicted · contradicted | contradicted · contradicted · contradicted | contradicted · contradicted · contradicted |  |
| contradicted · contradicted · not detected | contradicted · contradicted · not detected | contradicted · contradicted · not detected |  |
| contradicted · contradicted · not fitted | contradicted · contradicted · not fitted | contradicted · contradicted · not fitted |  |
| contradicted · not detected · supported | contradicted · not detected · Holm sentence | contradicted · not detected · Holm sentence |  |
| contradicted · not detected · contradicted | contradicted · not detected · contradicted | contradicted · not detected · contradicted |  |
| contradicted · not detected · not detected | contradicted · not detected · not detected | contradicted · not detected · not detected |  |
| contradicted · not detected · not fitted | contradicted · not detected · not fitted | contradicted · not detected · not fitted |  |
| contradicted · not fitted · supported | contradicted · not fitted · Holm sentence | contradicted · not fitted · Holm sentence |  |
| contradicted · not fitted · contradicted | contradicted · not fitted · contradicted | contradicted · not fitted · contradicted |  |
| contradicted · not fitted · not detected | contradicted · not fitted · not detected | contradicted · not fitted · not detected |  |
| contradicted · not fitted · not fitted | contradicted · not fitted · not fitted | contradicted · not fitted · not fitted |  |
| not detected · supported · supported | not detected · Holm sentence · Holm sentence | not detected · Holm sentence · Holm sentence |  |
| not detected · supported · contradicted | not detected · Holm sentence · contradicted | not detected · Holm sentence · contradicted |  |
| not detected · supported · not detected | not detected · Holm sentence · not detected | not detected · Holm sentence · not detected |  |
| not detected · supported · not fitted | not detected · Holm sentence · not fitted | not detected · Holm sentence · not fitted |  |
| not detected · contradicted · supported | not detected · contradicted · Holm sentence | not detected · contradicted · Holm sentence |  |
| not detected · contradicted · contradicted | not detected · contradicted · contradicted | not detected · contradicted · contradicted |  |
| not detected · contradicted · not detected | not detected · contradicted · not detected | not detected · contradicted · not detected |  |
| not detected · contradicted · not fitted | not detected · contradicted · not fitted | not detected · contradicted · not fitted |  |
| not detected · not detected · supported | not detected · not detected · Holm sentence | not detected · not detected · Holm sentence |  |
| not detected · not detected · contradicted | not detected · not detected · contradicted | not detected · not detected · contradicted |  |
| not detected · not detected · not detected | not detected · not detected · not detected | not detected · not detected · not detected |  |
| not detected · not detected · not fitted | not detected · not detected · not fitted | not detected · not detected · not fitted |  |
| not detected · not fitted · supported | not detected · not fitted · Holm sentence | not detected · not fitted · Holm sentence |  |
| not detected · not fitted · contradicted | not detected · not fitted · contradicted | not detected · not fitted · contradicted |  |
| not detected · not fitted · not detected | not detected · not fitted · not detected | not detected · not fitted · not detected |  |
| not detected · not fitted · not fitted | not detected · not fitted · not fitted | not detected · not fitted · not fitted |  |
| not fitted · supported · supported | not fitted · Holm sentence · Holm sentence | not fitted · Holm sentence · Holm sentence |  |
| not fitted · supported · contradicted | not fitted · Holm sentence · contradicted | not fitted · Holm sentence · contradicted |  |
| not fitted · supported · not detected | not fitted · Holm sentence · not detected | not fitted · Holm sentence · not detected |  |
| not fitted · supported · not fitted | not fitted · Holm sentence · not fitted | not fitted · Holm sentence · not fitted |  |
| not fitted · contradicted · supported | not fitted · contradicted · Holm sentence | not fitted · contradicted · Holm sentence |  |
| not fitted · contradicted · contradicted | not fitted · contradicted · contradicted | not fitted · contradicted · contradicted |  |
| not fitted · contradicted · not detected | not fitted · contradicted · not detected | not fitted · contradicted · not detected |  |
| not fitted · contradicted · not fitted | not fitted · contradicted · not fitted | not fitted · contradicted · not fitted |  |
| not fitted · not detected · supported | not fitted · not detected · Holm sentence | not fitted · not detected · Holm sentence |  |
| not fitted · not detected · contradicted | not fitted · not detected · contradicted | not fitted · not detected · contradicted |  |
| not fitted · not detected · not detected | not fitted · not detected · not detected | not fitted · not detected · not detected |  |
| not fitted · not detected · not fitted | not fitted · not detected · not fitted | not fitted · not detected · not fitted |  |
| not fitted · not fitted · supported | not fitted · not fitted · Holm sentence | not fitted · not fitted · Holm sentence |  |
| not fitted · not fitted · contradicted | not fitted · not fitted · contradicted | not fitted · not fitted · contradicted |  |
| not fitted · not fitted · not detected | not fitted · not fitted · not detected | not fitted · not fitted · not detected |  |
| not fitted · not fitted · not fitted | not fitted · not fitted · not fitted | not fitted · not fitted · not fitted |  |

6 of 64 rows differ. Every difference is a test that comes after a contradicted one: coded, it reads the Holm sentence; corrected, it is read on its own.

## 2. Change 2 (defect 43, owner ruling: read literally): "not robust" whenever the two statistics read differently

One test on its own (first in Holm order, so the Holm step does not act). Gate passed.

| primary | residualised | control | coded | corrected | differs |
|---|---|---|---|---|---|
| supported | supported | supported | supported, defect-specific | supported, defect-specific |  |
| supported | supported | not supported | supported, but tracks activity, not defects | supported, but tracks activity, not defects |  |
| supported | contradicted | supported | not robust to the statistic | not robust to the statistic |  |
| supported | contradicted | not supported | not robust to the statistic | not robust to the statistic |  |
| supported | not detected | supported | not robust to the statistic | not robust to the statistic |  |
| supported | not detected | not supported | not robust to the statistic | not robust to the statistic |  |
| supported | not fitted | supported | not robust to the statistic | not robust to the statistic |  |
| supported | not fitted | not supported | not robust to the statistic | not robust to the statistic |  |
| contradicted | supported | — | contradicted | not robust to the statistic | **yes** |
| contradicted | contradicted | — | contradicted | contradicted |  |
| contradicted | not detected | — | contradicted | not robust to the statistic | **yes** |
| contradicted | not fitted | — | contradicted | contradicted |  |
| not detected | supported | — | not detected | not robust to the statistic | **yes** |
| not detected | contradicted | — | not detected | not robust to the statistic | **yes** |
| not detected | not detected | — | not detected | not detected |  |
| not detected | not fitted | — | not detected | not detected |  |
| not fitted | supported | — | not fitted | not fitted |  |
| not fitted | contradicted | — | not fitted | not fitted |  |
| not fitted | not detected | — | not fitted | not fitted |  |
| not fitted | not fitted | — | not fitted | not fitted |  |

4 of 20 rows differ. Change 2 never turns a reading into "supported". Note the rows with "not fitted" on one side only: read literally, they become "not robust" (see the question below).

## 3. Both changes together, and the gate

Both changes act independently as shown above. If the placebo gate failed, every test reads "NO FINDING: the placebo gate failed" under both rules.

