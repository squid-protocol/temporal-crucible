# Independent statistic — the second builder's prior

Written before `indep_stat.py` was run against anything, and before any comparison with the reference.
Source: `docs/process/comparison_scorer_spec.md` section 6 only (the quoted registration words and the table
of readings), plus the docstring of test 5. The reference implementation, the reviews, the defect log and git
history were not opened.

For each of the seven choices, the reading I judge to be the plain meaning of the registration's words.

| # | choice | my prior reading | switch value |
|---|---|---|---|
| 1 | a remainder when files do not divide evenly into bands | band = floor(rank × k ÷ n) | `remainder = "floor_rank"` |
| 2 | "within 1.5" | inclusive (larger ÷ smaller ≤ 1.5) | `ratio = "inclusive"` |
| 3 | "plus equal-LOC pairs by their share" | (1 − share) × the mean of the two sides + share × the equal-size concordance | `equal = "weighted"` |
| 4 | pooled or per band | one formula over all eligible pairs | `pooling = "pooled"` |
| 5 | "≥ 100 eligible pairs" | equal-size pairs do count toward the 100 | `floor = "equal_counts"` |
| 6 | "the repo has ≥ 300 files" | the repo's ranked files | `n300 = "ranked"` |
| 7 | "ties broken by path" | Python string order | `tiebreak = "string"` |

## Why

1. **Remainder — floor(rank × k ÷ n).** "Equal-count ... ties broken by path" describes ranking the files and
   cutting the ranking into k groups as equal as possible. That rules out, for me, the quantile reading (equal
   sizes sharing a band needs no tie-break) and the two chunk readings (a short or a long last band is not
   "equal-count": the last band can be off by up to k − 1 files). The words do not choose among the three
   balanced readings; I take floor(rank × k ÷ n) because it is the one-line formula a person writes for
   "equal-count band of a rank". This is my least certain choice.
2. **"Within 1.5" — inclusive.** "Within" a limit ordinarily includes the limit, as in "within 5 miles".
3. **Equal-LOC share — the weighted average.** "By their share" says the equal-size pairs enter with a weight
   equal to their share of the eligible pairs; a weight of `share` for them leaves `1 − share` for the rest,
   which is the only listed reading that is a true average (stays in 0..1, and equals 0.5 for a predictor with
   no information).
4. **Pooled.** Item 2 makes the band a condition for a pair to be eligible, and item 3 then scores "pairs";
   nothing in the words averages over bands or gives a band a weight.
5. **Floor — equal-size pairs count.** A pair of equal-size files in one band has ratio 1, so by item 2 it is
   an "eligible pair", and item 4 says "eligible pairs" without exception. ("Each side" I read as the two
   unequal sides, positive larger and positive smaller.)
6. **≥ 300 files — the repo's ranked files.** "The repo has ≥ 300 files" is said of the repo, not of a
   predictor; a count that changes with the predictor's missing values is not a property of the repo.
7. **Ties — Python string order.** "By path" with no qualifier is the path string compared as a string; a
   natural (digits-as-numbers) order would have had to be said.
