> **Status: design and prototype, not shipped.** Draft for GitGalaxy's `docs/wiki/`, written 2026-11-19 against the evolution-report prototype (`tools/report/evolution_report.py` in the temporal-crucible `sensor-overhaul` worktree). Numbers come from `docs/sensor-overhaul/sensors/ripple_radius.md`. Exploratory unless a line says otherwise.

# Evolution report: how far to trust it

What the labels are made of, and how reliable each is.

| Label | Source | Reliability |
|---|---|---|
| Sweep | rule: more than 60 functions in one commit | strong |
| Fix | `Fixes:` trailer or a fix-like subject | moderate: misses fixes in the remainder (about 8 to 20% of organic commits in two hand checks) |
| Cause | `Fixes:` trailer, or blame | named causes are strong; blame is moderate (finds a cause for 83 to 85% of unnamed fixes in DPDK and Mesa, but names where lines last changed) |
| Function | git diff-header context | moderate: roughly one in ten names a neighbour of the function actually edited (8% in DPDK, 12.5% in Mesa; not measured elsewhere) |
| Cc: stable, Reported-by | trailers | strong where a project uses them; usually sparse (Reported-by on 2 to 4% of fixes) |

## What the report shows
The share of commits that name their cause, how many fix-like commits have no cause, trailer habits, and a note whenever a number rests on a sample.

## What it does not say
- **Extrinsic or latent:** the report never labels a fix "extrinsic"; a cause outside the history cannot be seen. Fixes with no findable cause are shown as such.
- **Forecasts:** whether a particular change will need a fix is not predicted.
- **Accuracy of the look-first lists:** measured per repository by `gitgalaxy backtest`.

## Why a project can look different
Projects differ in message habits: DPDK names causes for about a third of its commits, Mesa for 6%, nDPI and curl for almost none. A project with terse messages looks low on fixes and needs blame to show repairs.

## What to do about it
Check the "how fixes are found" card first. If a project names few causes, read repair figures as lower bounds, and run with blame (a sample) to see timing.
