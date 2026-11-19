> **Status: design and prototype, not shipped.** Draft for GitGalaxy's `docs/wiki/`, written 2026-11-19 against the evolution-report prototype (`tools/report/evolution_report.py` in the temporal-crucible `sensor-overhaul` worktree). Numbers come from `docs/sensor-overhaul/sensors/ripple_radius.md`. Exploratory unless a line says otherwise.

# Evolution report: sweeps

A sweep is one commit that edits more than 60 functions. In a random sample of sweep subjects from DPDK and Mesa the pattern is clear: renames (`rename bonded to bonding`), API conversions (`standardize on negative errno values`), reformatting (`unify the indent coding style`, `add .clang-format`), namespace changes, branch merges and generated headers.

The report lists the twelve largest with date, size, subject, and whether the sweep was later cited as the cause of a fix (named by a `Fixes:` trailer or found by blame).

## Measured behavior (exploratory)
- Sweeps are 0.5% (DPDK) and 0.3% (Mesa) of all commits, and 18 to 21% of function edits.
- Fixes follow sweep edits about as often as organic edits at the repository level (a forward test across seven repositories: 1.06 vs 1.09 times the same-file baseline), so "mechanical" does not mean "safe". Per function edited, sweeps get fewer prompt repairs than organic edits (2.5 to 3.2% of sweep-edited functions are also fixed in the same quarter, against 5 to 7% for organic).
- Sweeps are cited as a cause at the commit level most often (44 to 52% of their edits), because they touch so much code.

## Limits
- The 60-function threshold is a rule, not a judgement of intent. A large feature can pass it.
- Most radius and triage results in the research log exclude sweeps; their repairs are less studied.

## Worked example
In DPDK, `ethdev: add namespace` (2021-10-22) edited 1,105 functions and was later named as the cause of fixes. `build: mark exported symbols` (2025-04-07, 2,905 functions) has none named so far. The report shows the count of fixes that name each sweep as their cause.

## What to do about it
Plan a sweep like a migration: list the callers it touches, review it in slices, and watch for fixes in the following quarters. "Mechanical" does not mean "safe": at the repository level fixes followed sweep edits about as often as organic edits (research result, not computed for your repository by this report).
