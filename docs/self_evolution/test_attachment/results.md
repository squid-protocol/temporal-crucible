# Test-attachment study results (plan: temporal-crucible-wt-selfscan/docs/self_test_attachment_plan.md; exploratory, observational)
Scripts: build.py (snapshots, imports, touches, births, sizes -> derived.pkl, build_log.json), analyze.py (descriptives, models -> results.json). Full numbers: results.json.

## Counts
36 ISO weeks (2026-03-16..11-16, UTC; last week partial). 6,700 first-parent / 6,919 non-merge commits; diff cache 4,111 commits (all found in git log). 246 engine files ever (219 at tip). 7,796 engine function touches (1,297 fix) in 977 file-weeks. 695 fix commits (643 by subject, rest PR `bug` label; label rule applied to first-parent squash commits only).
Rows dropped: 6 (week 0, no previous week-end), 106 (file absent from the tree at previous week-end), 34 (no size in the daily scan). Model rows: 831 file-weeks, 173 files.
Attached share of engine files (mean of weekly snapshots): Mar 0%, Apr 0%, May 56%, Jun 88%, Jul 94%, Aug 94%, Sep 93%, Oct 91%, Nov 94%.

## Descriptive (lag-1 attachment)
Attached: 714 file-weeks, 143 files, pooled fix share 19.1% (1195/6269), median lines 282. Unattached: 117 file-weeks, 61 files, 9.7% (64/663), median 219.
Variation: 85.9% of rows attached; only 117 unattached rows, 86 of them in the Gemini era; only 31 files are seen in both states. Power is limited.

## Hypotheses
T1 attached vs not: OR 0.57, 95% CI 0.29-1.13 (p 0.107). NOT SUPPORTED (interval includes 1); the point estimate is below 1.
T2 dose log(1+n tests): coef -0.575, CI -0.917..-0.232 (OR per log unit 0.56, 0.40-0.79). SUPPORTED by the declared rule.
T3a lead (next-week attachment): OR 0.31 (0.14-0.70) vs lagged on the same 761 rows OR 0.52 (0.28-0.96); log version lead -0.516 (-0.890..-0.142) vs lag -0.566 (-0.907..-0.225). The lead is as strong or stronger, so the lagged result does not show tests acting first.
T3b: files with a fix touch in week t had attachment rise by the end of week t+1 in 82/229 (35.8%) file-weeks, files without in 310/2288 (13.6%); cluster-robust OR 3.56 (2.34-5.42). Consistent with tests being added after bugs. POST HOC: among touched files only, 23.0% vs 35.8%; among files unattached at start, 58/393 vs 0/12 (too few).
## Robustness
2-week lag (attachment at end of week t-2; my reading of "previous 2 weeks"): binary OR 0.73 (0.30-1.78); log coef -0.335 (-0.781..0.111). Neither interval excludes no effect.
File-level (159 files born in window, attachment at end of week B+3, total fix share, size-decile matched): pooled fix share 17.4% attached (120 files) vs 12.6% unattached (39); decile-matched OR 1.37 (0.91-2.05), the opposite direction, not significant.

## Deviations / problems
- Weeks by UTC commit date; era by week Monday; plan's "week-end commit" = newest first-parent commit at or before Sunday 23:59:59 UTC.
- Excluded all of gitgalaxy/standards/ (including code files there) as "pattern tables"; only top-level `gitgalaxy`/`backend` Python counts as engine.
- Attachment counts every .py under tests/ (helpers and conftest too); 1/3 to 1/2 of test files resolve to no engine file (importing via subprocess, other paths, or standards), so attachment is undercounted. No transitive imports.
- Age = weeks since first commit adding the path (renames count as new files); files present at the first commit have age counted from 2026-03-21.
- Previous-4-week touches are truncated for the first weeks. Interpretation of the 2-week lag is mine. Cluster-robust SEs with 173 files, but few unattached files.
## What it shows
Fix share per touch is lower for files with more attached tests (dose) but not significantly lower for attached versus unattached, the lead is as strong as the lag, and fixes precede attachment rises, so this does not show that tests reduce regressions.
