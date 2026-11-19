> **Status: design and prototype, not shipped.** Draft for GitGalaxy's `docs/wiki/`, written 2026-11-19 against the evolution-report prototype (`tools/report/evolution_report.py` in the temporal-crucible `sensor-overhaul` worktree). Numbers come from `docs/sensor-overhaul/sensors/ripple_radius.md`. Exploratory unless a line says otherwise.

# Evolution report: repeat spots

For every fix commit, the functions named in its diff headers get one fix each. A function with two or more is a repeat spot.

## What the report shows
- Fix edits in total and distinct functions fixed.
- The share of fix edits landing in functions fixed twice or more, and five times or more.
- The ten most repaired functions with their files.

## Measured behavior (exploratory)
- DPDK and Mesa: functions fixed twice or more hold about 60% of fix edits; functions fixed five or more times hold 14 to 20% of a quarter's fixes.
- It is not a tiny hot list: the top 1% of fixed functions hold 8% of fix edits and the top 10% hold 31 to 32%. Repairs are spread wide but repeat.
- Small, old C projects show higher concentration (curl and nDPI: 78% and 76% of fix edits in functions fixed twice or more), partly because they have fewer functions.

## Limits
- Function identity is (file, name) from git diff headers; a function renamed or moved starts a new count.
- A refactor that touches a function in a fix-like commit counts as a fix.
