# Do the tests keep GitGalaxy from regressing? A quick look at what the history can and cannot say (EXPLORATORY; 2026-11-20)

Question (owner): with unit tests and golden tests "up the wazoo", does the data support the idea that the pipeline makes regressions less likely? Nothing here is a causal test; every item is a descriptive count from the PR/issue pull and the evolution data.

## Counts
- Tests accompany almost every code change: 1,543 of 1,672 PRs that change engine code (92%) also change a test; 360 of 387 fix PRs that change engine code (93%). Tests are 71% of lines by November (0% in March).
- Reverts are almost absent: 1 revert among 6,363 squash commits.
- Real failures caught before merge: 114 of 6,487 merged PRs (1.8%) carried `shepherd:needs-fix` (a real failure on the PR head). promoter-bot#70 measured review/CI send-back rates of 20% (1-2 files), 24% (3-4), 50% (5), 62% (6-7) over 1,087 PRs.
- Escapes to `main`: 161 issues labelled `ci-red-main` (a check failing on main, opened by a workflow): 94 in October, 67 in November (the label exists from October, so earlier breaks are not recorded; flakes and infra failures are included).
- Fix edits per week stayed flat while the code grew: about 146 per week in July-September (1,903 fix edits, 13 weeks) and about 153 per week in October-November (1,114, 7.3 weeks), while the engine grew from about 330 to 4,079 functions; per function that is roughly an 8-fold fall. Young code has had less time to be repaired, so this is confounded.
- Fixes of fixes: of 464 blame-derived repair pairs, 171 (37%) have an earlier FIX as the cause, median lag 2.0 days, 66% in the same function; 60 (13%) have a restructure as the cause (median 12 days).
- Labelled by two models from issue text: 15 of 100 bug issues named a recent PR as the cause; 81% (Claude) / 69% (Gemini) were judged pre-existing.
- Not caught by tests: the speed steps (compile-policy threshold x3.3-5.7 on small many-language scans, a +15% comment-stripping fix, an at-least-four-step cluster on 2026-09-26..28, a x2.7 step on the mainframe corpus in April). The test suite has CPU-clock linearity and ReDoS checks but no gate on constant-factor cost; the file-screen change (3,389 -> 991 files mapped on language-crucible) was an intended output change.

## What this does and does not support
Supports: near-universal test coupling, very few reverts, real failures stopped at the PR stage, a flat absolute fix rate as the code grew 10x, and bugs found being mostly latent gaps in a heuristic engine rather than recent regressions.
Does not support (or cannot say): any causal effect (no era without tests; AI authorship, gates and growth move together); that regressions of cost are prevented (they are not); that repairs are rare (37% of repairs are fixes of fixes; 52% of fix edits land in functions fixed twice or more); anything about escapes beyond `main` (no release or user-report data in this pull).

## How it could be tested properly
1. Test attachment per file (tests that import or are named for the module, test lines per engine line) against repairs per function-week, size-, age- and era-matched.
2. A difference-in-differences around the dated addition of a golden or crucible gate for a subsystem, against matched untouched subsystems.
3. Classify the `ci-red-main` issues into flake, infra and real regression to estimate the escape rate.
4. A speed canary: time the three small corpora (about 10-40 CPU seconds each) plus language-crucible on engine-core PRs and flag a CPU change above the measured noise (about 5%; the sensitivity pass uses 10%). It would have flagged the compile-policy cluster, and the April mainframe step; only language-crucible shows the screen and comment-stripping steps.
