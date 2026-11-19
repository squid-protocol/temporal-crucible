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
Sweeps are under 1% of commits in both. Of the organic edits, a third (DPDK) and a fifth (Mesa) are later cited as the cause of a fix.

## Limits
- The fix rule is keyword-based and misses fixes: a hand check of 40 organic commits per project found about 3 of 40 (DPDK) and 8 of 40 (Mesa). The true fix share is higher than shown.
- Function counts come from git diff headers; about one in eight function names is a neighbour of the function actually edited.
- The contributors chart counts distinct author e-mails; one person with two addresses counts twice.
