> **Status: design and prototype, not shipped.** Draft for GitGalaxy's `docs/wiki/`, written 2026-11-19 against the evolution-report prototype (`tools/report/evolution_report.py` in the temporal-crucible `sensor-overhaul` worktree). Numbers come from `docs/sensor-overhaul/sensors/ripple_radius.md`. Exploratory unless a line says otherwise.

# Evolution report: which changes get repaired

Organic commits at least three years old (so each had time to be repaired) are grouped by the number of functions they edit. The chart shows the share later cited as the cause of at least one fix.

## Measured behavior (strong, replicated on DPDK and Mesa)
- DPDK: 17% of one-function commits are later cited, 27% of 2 to 3, 36% of 4 to 10, 44% of 11 to 30, 45% of 31 to 60.
- Size is the one per-change signal that held up (test AUC 0.72 to 0.77 for "will this change need a fix"). Neighbourhood, author tenure, reviewer trailers (Reviewed-by, Acked-by, Tested-by) and the kind of change added nothing measurable once size is held fixed (for example Reviewed-by: rate ratio 0.97).

## Limits
- "Cited" means named or blamed as the cause of a later fix: a lower bound (unfound causes add more).
- When causes come from a blame sample, later-repaired shares are understated; the report says so under the chart.
