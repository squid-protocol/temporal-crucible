# The independent statistic — report

**2026-11-15.** Amendment 5 section 9's independent check of the primary statistic, as specified in
`docs/process/comparison_scorer_spec.md` section 6.

**How it was done.** A second builder — a fresh Claude Fable session, a different model from the first
builder, given section 6 of the specification and the interface of one test and nothing else — wrote
`tools/compare/indep_stat.py`: the statistic as a plain loop over pairs, with every listed reading of the
registration's words as a switch. **Before running anything**, it wrote down which reading of each choice it
judged the plain meaning of the words (`tools/compare/INDEP_STAT_PRIOR.md`, 10:37 AM Eastern). It did not
open the reference statistics module, the reference scorer, the reviews, the defect log or git history, and
said so. The comparison with the reference was then run by the orchestrating session, which may read it.

## Result

| choice | the builder's prior | the reading the reference takes |
|---|---|---|
| a remainder when files do not divide evenly into bands | band = floor(rank × k ÷ n) | **the same** |
| "within 1.5" | inclusive | **the same** |
| "plus equal-LOC pairs by their share" | (1 − share) × the mean of the two sides + share × the equal-size concordance | **the same** |
| pooled or per band | one formula over all eligible pairs | **the same** |
| "≥ 100 eligible pairs" | equal-size pairs count | **the same** |
| "the repo has ≥ 300 files" | the repo's ranked files | **the files in use for this predictor** |
| "ties broken by path" | Python string order | **the same** |

- **With the one difference changed, the independent implementation equals the reference bit for bit** on all
  2,000 stress cases (built so that every choice bites) and on every confirmatory cell of both decoy studies
  (33 + 33).
- **The match is unique.** Every one of the 10,080 combinations of readings (the seven listed choices and the
  builder's three extra ones) was tried on 120 cases: one combination of the seven matches; it appears three
  times only through an extra option that has no effect under pooling.
- **Every other single reading differs** from the reference: by more than 0.005 in 122 to 1,472 of the 2,000
  cases.
- **The builder's prior, as written,** equals the reference in 1,792 of 2,000 cases (it differs by more than
  0.005 in 123, at most 0.030), and in 32 of 33 confirmatory cells of each decoy study (at most 0.0023 in the
  study without an effect and 0.0154 in the study with one).

`tests/test_indep_stat_vs_reference.py` keeps the comparison as a standing test.

## What this shows

1. **The reference computes a well-defined statistic** that an independent implementation, written as a plain
   loop, reproduces exactly. Together with the third review's 400 cases and the first reviewer's 2,983, the
   primary statistic is the most-checked piece of SA3.
2. **The registration's words were nearly enough.** An independent reader, given only the words, landed on the
   reference's reading for six of the seven open choices. That is better than the first reviewer expected
   (defect log 64, which was written by a reader who had already seen the code).
3. **The one place the words mislead** is "10 if the repo has ≥ 300 files". The code counts the files **in use
   for the predictor** — after files with no value are dropped — not the repo's ranked files. An independent
   reader took "the repo" literally. Where a repo has between 300 and a few more ranked files and some are
   dropped for a missing value, the two readings use different band counts and the statistic moves by up to a
   few hundredths.

## What follows

- **The code governs**, as for every other gap (Amendment 5). The registration is owed an **erratum**: "10 if
  the files in use for that predictor number 300 or more, else 5." A draft is
  `docs/sa3_amendment5_erratum2_draft.md`. It cannot be entered now: the registration is sealed. It goes in
  with the scoring step's documents, and the seal is re-taken after it.
- Defect log 64 is updated with this measurement.
