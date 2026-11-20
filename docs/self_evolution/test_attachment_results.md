# Test-attachment study: results (EXPLORATORY; plan `docs/self_test_attachment_plan.md`, commit bbfacd3, fixed before any model was fitted; 2026-11-20)

Question: do changes to files that have unit tests attached end up as fixes less often? Full tables `test_attachment/results.md`; scripts `tools/selfhistory/test_attach_build.py` and `test_attach_analyze.py`. Run by an agent at low priority; key numbers checked against `results.json`.

## Data
36 ISO weeks (2026-03-16 to 11-16); 246 engine files ever; 7,796 function touches of which 1,297 are in fix commits (695 fix commits: 643 by subject prefix, the rest by the `bug` label); 977 file-weeks with a touch; 831 rows over 173 files after dropping 6 (first week), 106 (file not in the previous week-end tree) and 34 (no size). Attachment = distinct test files that import the file's module, at the previous week-end. Share of engine files with at least one attached test: 0% in March and April, 56% May, 88% June, 91-94% from July on.

## Descriptive
| lagged attachment | file-weeks | files | pooled fix share | median lines |
|---|---|---|---|---|
| attached | 714 | 143 | 19.1% (1,195 of 6,269 touches) | 282 |
| unattached | 117 | 61 | 9.7% (64 of 663) | 219 |
Almost every row is attached (85.9%); only 117 are unattached, 86 of them in the Gemini era, and only 31 files appear in both states. The test has little power and the contrast is partly an era contrast.

## Against the declared hypotheses
- T1 (attached versus not, odds ratio below 1 with the interval wholly below 1): OR 0.57, 95% interval 0.29 to 1.13, p = 0.107. **Not supported** (interval includes 1); the point estimate is below 1.
- T2 (dose, log(1 + attached test files)): coefficient -0.575, interval -0.917 to -0.232 (OR 0.56, 0.40 to 0.79). **Supported by the declared rule.**
- T3a (direction): the lead model (next week's attachment) gives OR 0.31 (0.14 to 0.70) against 0.52 (0.28 to 0.96) for the lagged model on the same 761 rows; the dose versions are -0.516 (lead) and -0.566 (lag). The lead is as strong as or stronger than the lag, so the lagged result does not show tests acting first.
- T3b (tests after bugs): attachment rose by the next week-end in 35.8% (82 of 229) of file-weeks with a fix touch, against 13.6% (310 of 2,288) without; odds ratio 3.56 (2.34 to 5.42). Consistent with tests being added after bugs.
- Robustness: two-week lag, binary OR 0.73 (0.30 to 1.78), dose -0.335 (-0.781 to 0.111): neither excludes no effect. File-level, size-decile matched (159 files born in the window, 120 attached): fix share 17.4% attached against 12.6% unattached; OR 1.37 (0.91 to 2.05), the opposite direction and not significant.

## Reading
There is no clear evidence here that attached tests lower the share of a file's changes that are fixes. The one result that clears its declared rule (the dose) is matched or beaten by a lead model that cannot be a causal effect of tests, and tests are demonstrably added after fixes. The raw and file-level contrasts point the other way. With 86% of rows attached, the repo cannot answer this question by comparing tested with untested files: unit tests are near-universal (92% of engine-code PRs add or change one), so the variation that would identify an effect is mostly the early period before the tests existed.
Limits: unit-test coupling only (golden and crucible pipeline tests attach to everything and are not measured); a third to a half of test files resolve to no engine file (subprocess use, `standards/` imports) so attachment is undercounted; imports are not followed transitively; `gitgalaxy/standards/` is excluded entirely; weeks are UTC and the last week is partial; file age resets on renames.
What would be informative instead: the second test in the quick look (the repair rate in a subsystem before and after a dated golden or crucible gate, against matched subsystems), or a design that varies the pipeline itself.
