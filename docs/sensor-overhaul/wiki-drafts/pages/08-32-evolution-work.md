> **Status: design and prototype, not shipped.** Draft for GitGalaxy's `docs/wiki/`, written 2026-11-19 against the evolution-report prototype (`tools/report/evolution_report.py` in the temporal-crucible `sensor-overhaul` worktree). Numbers come from `docs/sensor-overhaul/sensors/ripple_radius.md`. Exploratory unless a line says otherwise.

# Evolution report: where the work goes

Every function edit (a function named in a commit's diff headers; a function edited in two commits counts twice) is put in exactly one category, first match wins:

1. **sweep**: more than 60 functions in the commit
2. **revert**: subject starts with Revert
3. **fix, named cause**: `Fixes:` trailer
4. **fix, cause by blame**, or **fix, no cause found**: fix-like subject, no trailer
5. **tests only**: every code file touched is a test file
6. **comment or whitespace only**: from the diff
7. **formatting, docs, licence**: by subject
8. **adds code** (added lines at least three times removed), **removes code**, **modifies** (the rest)

The report groups them as **organic change**, **sweeps**, **fixes** and **mechanical** (reverts, tests only, comment-only, formatting).

## Measured behavior (exploratory)
| | DPDK | Mesa |
|---|---|---|
| sweeps (share of edits) | 20.9% | 18.0% |
| fixes of all kinds | 17.8% | 9.0% |
| mechanical | 2.8% | 1.7% |
| organic change | 58.5% | 71.3% |
Sweeps are 0.5% (DPDK) and 0.3% (Mesa) of all commits. Of the organic edits, a third (DPDK) and a fifth (Mesa) are later cited as the cause of a fix.

## Limits
- The fix rule is keyword-based and misses fixes: a hand check of 40 organic commits per project found about 3 of 40 (DPDK) and 8 of 40 (Mesa). The true fix share is higher than shown.
- Function counts come from git diff headers; about one in eight function names is a neighbour of the function actually edited.
- The contributors chart counts distinct author e-mails; one person with two addresses counts twice.

## Differences from the research log
The report's rule differs slightly from the research partition: a subject about formatting, docs or licence ("fix typo", "fix whitespace") is classified as formatting even if it also says fix, tests-only uses every file a commit touches (not only code files), and the diff parser handles file names with spaces, non-ASCII names and deleted files. On DPDK this moves fixes from 17.8% to 17.3% of edits and mechanical from 2.8% to 3.1%. The hand-check miss rate quoted above was measured with a narrower fix rule (fix, fixes, fixed, bug, regression) than the one shipped here, and has not been re-measured.

## Worked example
A quarter in which sweeps make up half the edits is usually one planned migration, not a sudden jump in organic work. Read the sweep list to find it, then read the organic line without it.

## What to do about it
Judge a project's pace from the organic and fix lines; treat sweeps as separate events to plan and review. A rising fix share with a flat organic line means more repair per unit of new work.
