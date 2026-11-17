# Blast radius of a change: where do the fixes for it land? (exploratory; hypotheses fixed 2026-11-17 before any distance was computed)

**Idea (owner, 2026-11-17):** metrics of single functions have not tied to issues and fixes; look instead at a local reach radius, discrete chains of logic units: a change causes a fix or issue sometime later, downstream of it.

## Design
Use cases where the change and its fix are **known**: regression-class fix commits whose message names the commit that caused them (the crucible's `v3c` events, `why = references <sha> (N d earlier)`; reverts excluded, since a revert touches the same code by construction). For each pair (inducing commit I, fix commit F):
1. Functions touched by each commit, from the git hunk header (`git show -U0`), C-family files only.
2. The call graph of the first quarterly snapshot at or after the inducing commit: nodes `(path, function)`, confident resolved call edges (`fcall_data`, kind call, one candidate).
3. For the fix's functions, the call-graph relation to the inducing change's functions: the same function; the same file; a **caller** within k hops (the fix is in code that depends on the change); a **callee** within k hops (the fix is in code the change relied on).
4. Two nulls, because most of what looks like a radius is file locality: **A (repo-wide)** random functions of the same size decile; **B (same file)** random other functions from the same file as the fixed function. B isolates the call graph: given the fix is in this file, is the fixed function call-near the change more than its file-mates are?
Stratified by lag (fix the same day or next, against 2 or more days later) because same-day follow-ups are the author finishing their own change.

## Hypotheses
- **R1 (radius).** The fixed function is within 2 call hops (either direction) of the inducing change's functions more often than the repo-wide null (ratio above 3).
- **R2 (beyond the file).** Against null B (file-mates), the fixed function is still within 2 hops more often (ratio above 1.5): the call graph says something file location does not.
- **R3 (direction).** Fixes land in **callers** of the changed code (dependents) more often than in **callees** (ratio above 1.5).
- **R4 (decay).** Excess over null falls as hops increase: 1 hop above 2 hops above 3 hops.
- **R5 (signature).** When the inducing change altered a function's parameter count, the caller-direction excess is larger than for other inducing changes.
- **R6 (same function).** A minority of fixes (under 40%) are in a function the inducing commit also touched; the rest are elsewhere.

## What would surprise
No excess against null B (the radius is only file locality); callees as common as callers; or most fixes in the same function (no ripple at all).
