> **Status: design and prototype, not shipped.** Draft for GitGalaxy's `docs/wiki/`, written 2026-11-19 against the evolution-report prototype. Exploratory.

# Evolution report: stage

A one-word description of how fast a repository's code base is growing, shown at the top of "Where it stands now" with the numbers behind it.

| Stage | Growth in functions per year, last three years |
|---|---|
| Expanding | 15% or more |
| Growing | 5% to 15% |
| Steady | -2% to 5% |
| Shrinking | below -2% |

It is a description of the **pace of net growth**, not of a product's life cycle. The report also prints edits per function per year, the fix share and sweep share of the last year's edits, the share of older functions untouched for four quarters, and the project's age, so the label can be checked against them.

## Measured behavior (exploratory)
On 19 reference repositories (C, Go, Python, Rust) growth per year ranged from -3.0% (libxml2) to 22.3% (prometheus), median 7.8%. Under the cut points: 3 expanding, 9 growing, 6 steady, 1 shrinking. The table is in the research notes (`stage_calibration.md`).

## Limits
- The cut points were set by inspecting the same repositories; they have not been checked against how maintainers describe their projects.
- Growth counts net functions in the scan; directories the scan skips and large moves shift it.
- A project that paused during the last three years reads as steady.

## What to do about it
Use it as a prompt, not a verdict: an expanding project needs review capacity for the new code; a steady one is mostly upkeep, so look at the fix share and the repeat-spot list; a shrinking one is being pruned, so check what is leaving.
