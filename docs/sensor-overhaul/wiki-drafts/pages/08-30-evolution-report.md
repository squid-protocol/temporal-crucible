> **Status: design and prototype, not shipped.** Draft for GitGalaxy's `docs/wiki/`, written 2026-11-19 against the evolution-report prototype (`tools/report/evolution_report.py` in the temporal-crucible `sensor-overhaul` worktree). Numbers come from `docs/sensor-overhaul/sensors/ripple_radius.md`. Exploratory unless a line says otherwise.

# Evolution report

A one-page, plain-language history of a repository: how it grew, where the work went, how quickly and where repairs arrived, and which functions keep needing them. It describes the past; it does not forecast bugs.

## What it needs
- **Git history only:** activity by kind, sweeps, repairs and their timing, repeat spots, which changes get repaired, label quality, contributors. Works on any C, Go, Python or Rust clone, in minutes.
- **Quarterly scans (optional):** adds code-base size, births and deaths of functions, age layers, how much of the code is alive, and how close repairs land to the change that caused them (the repair radius).
- **Blame (optional):** finds causes for fixes that do not name one (needed when a project does not use `Fixes:` trailers).

## How to read it
Every figure has a confidence label: **Strong** (a counting rule or replicated), **Moderate** (a label with known error, such as the keyword rule for fixes), **Exploratory** (one project, no replication). Each section ends with a "so what" line and a link to the page that explains how it was computed.

| Term | Meaning |
|---|---|
| Sweep | One commit that edits more than 60 functions: renames, API conversions, reformats. Planned, mechanical. |
| Organic change | Everything else that is not a fix or mechanical: features, refactors, new code, removals. |
| Fix | A commit with a `Fixes:` trailer or a fix-like subject (fix, bug, regression, crash, leak, overflow, race, deadlock, uaf, null). |
| Cause | The earlier commit a fix repairs: named in the fix, or found by blame. |

## Sections
1. [Growth](08-31-evolution-growth.md) (needs scans)
2. [Where the work goes](08-32-evolution-work.md)
3. [Sweeps](08-33-evolution-sweeps.md)
4. [Repairs: when, and how close](08-34-evolution-repairs.md), see also [repair radius](08-29-repair-radius.md)
5. [Repeat spots](08-35-evolution-repeat-spots.md)
6. [Which changes get repaired](08-36-evolution-which-changes.md)
7. [How far to trust it](08-37-evolution-label-quality.md)

## What it is not
- It does not say whether a particular change will need a fix. Size is the only per-change signal that held up in our tests; structure, author experience and reviewer trailers added nothing.
- It does not measure how well this repository's "look first" and triage lists work. That is a separate command, `gitgalaxy backtest`.
