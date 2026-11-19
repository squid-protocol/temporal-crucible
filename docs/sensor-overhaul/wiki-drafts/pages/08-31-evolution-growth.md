> **Status: design and prototype, not shipped.** Draft for GitGalaxy's `docs/wiki/`, written 2026-11-19 against the evolution-report prototype (`tools/report/evolution_report.py` in the temporal-crucible `sensor-overhaul` worktree). Numbers come from `docs/sensor-overhaul/sensors/ripple_radius.md`. Exploratory unless a line says otherwise.

# Evolution report: growth

Four timelines from the quarterly scans. Quarterly means a function born and deleted inside one quarter is not seen.

| Chart | Definition |
|---|---|
| Size | Functions found by the scan at each quarter |
| Births and deaths | **New code**: a function whose name did not exist in the previous scan. **Moved in**: new here, but the name existed elsewhere before. **Removed**: gone, and the name no longer exists. **Moved out**: gone here, the name exists elsewhere. |
| Age layers | Functions present at each quarter, grouped by the year they first appeared. The first layer includes everything that existed at the first scan. |
| How much is alive | Share of the functions edited this quarter (named in a commit's diff headers), and share untouched for the last four quarters |

## Measured behavior (DPDK, exploratory)
- Median of the last 16 quarters: 776 commits edit 2,368 functions (4% of the code); 1,103 functions are born (544 brand-new code in new files, 437 new functions in existing files, 131 moved), 346 disappear (28 with a whole file, 134 removed from a file that stays, 128 moved).
- Births outrun deaths about 3 to 1 in DPDK and 1.8 to 1 in Mesa. Whole-file deletions are 8 to 14% of deaths; moves and renames are up to a third (Mesa).

## Limits
- Moves are matched by function name, which is crude (two unrelated functions with one name look like a move).
- Function identity is (file, name); a moved file looks like deaths plus births with the same names.
- A scan reads the code at a commit; macros and generated code affect counts.
