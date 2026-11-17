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

## Results (2026-11-17; curl; output `ripple_radius_curl_output.txt`, script `tools/sensor/ripple_links.py`)
**Data.** 755 curl regression fixes name the commit that caused them; reverts removed; 507 pairs usable (154 have no function name in a hunk header, 42 are sweeps of more than 60 or 30 functions, the rest not found in the snapshot). In 212 of them (42%) the fix touches a function **outside** the set the inducing commit changed: the only pairs a ripple can be read from. libgit2, redis and libxml2 have 20, 20 and 32 usable pairs (10, 14 and 16 with a fixed function outside the change): too few for any statement; their same-function shares (65%, 55%, 75%) match curl.

**A design error found and fixed before reading any result.** The first computation counted a fix inside a changed function as "no call relation" while the file-mate null could land anywhere, which biased the comparison against the call graph. The second version, used below, restricts to fixed functions outside the changed set, and the nulls exclude the changed set too.

| hypothesis | verdict | evidence (212 pairs with a fixed function outside the change unless stated) |
|---|---|---|
| R1 radius: within 2 hops far more often than random | **supported** | within 2 calls in either direction: **47.6%** of fixes, against 5.1% for random functions of the same size (9.3x, 95% 6.8 to 12.4); within 1 hop 41.0% against 2.6% (15.6x) |
| R2 beyond file locality (ratio above 1.5 against file-mates) | **supported, modest** | within 2 hops: 1.54 [1.32, 1.81] against random file-mates of the fixed function; within 1 hop 1.77 [1.48, 2.20]. For the 104 pairs where the fix is in a different file from every changed function: within 2 hops 26.0% against 6.8% (3.8x) and 1.65 [1.14, 2.43] against file-mates |
| R3 callers more than callees (ratio above 1.5) | **mixed** | in absolute terms the other way: the fixed function is a **callee** of the changed code in 29.7% (1 hop) against a **caller** in 16.5%. Against file-mates the enrichment is larger for callers (2.68 [1.84, 3.94]) than callees (1.66 [1.29, 2.24]); in the cross-file pairs only callers are enriched (1 hop 3.19 [1.22, 9.10], 2 hops 2.02 [1.18, 3.47]; callees 1.36 and 1.15, intervals include 1) |
| R4 decay with distance | **supported** | against file-mates: 1 hop 1.77, 2 hops 1.54, 3 hops 1.42; against the repo null 15.6, 9.3, 6.2. Most of the reach is within one hop: callers 16.5%, 20.3%, 22.2% and callees 29.7%, 34.0%, 34.4% at 1, 2, 3 hops |
| R5 signature changes ripple more to callers | **supported in direction, small sample** | when the inducing commit changed a parameter count (33 pairs with a fix outside), the fixed function is a caller within 1 hop in 11 of 33 (33%), against 24 of 179 (13%) otherwise (Fisher exact p = 0.009; odds ratio 3.2) |
| R6 minority in the same function (under 40%) | **not supported** | **71%** of fixes touch a function the inducing commit also touched (74% when the fix comes within 2 days, 69% when later); 85% are in the same file |

**Lag.** Fixes two or more days later ripple at least as much as same-day follow-ups: within 1 hop 44.5% against 35.7%; against file-mates 1.85 [1.48, 2.42] against 1.65; for 2 hops the same-day pairs lose significance (1.31 [0.96, 1.86]).

**Plain reading.** When a curl change later needs a regression fix, most of the time (71%) the fix is in the same code the change touched. In the minority where it lands elsewhere, about half the time (48%) the fixed function is within two calls of the change, against 5% for a random function of that size, and about 1.5 times as often as a random function from the same file. The effect is tight: most of it is within one call. Signature changes send the fix to callers (the code that depends on the changed function) three times as often (33% against 13%). Fixes to helper functions the changed code calls are the commonest cross-function pattern in absolute terms.

**Caveats.** Curl only, and only fixes that name their cause in the commit message (a selection by the project's habits; fixes that do not say what they fix are absent). The inducing commit is what the message says, not proven. Function sets come from git hunk-header context (154 of 755 pairs have none) and match snapshot functions by path and name. The call graph is static and resolved: calls through function pointers and callbacks, common in curl, are not edges, so the radius is understated. 212 pairs carry the ripple results; 33 the signature result; ten or so comparisons were read, the six hypotheses fixed beforehand and the lag and cross-file strata not. Exploratory; a replication needs a second repository with enough named links (libgit2, redis and libxml2 have 10 to 16).

**For a sensor.** The blast radius is a useful, local, call-graph-bound quantity for a *specific change*, not a metric of a function: for a change set, list the functions within one call (callers first for signature changes, then callees) and the same file's other functions. The reach sensor and `gitgalaxy change` already give callers and one hop out for touched functions; this result says that is the right radius and suggests ordering the review list by callers for signature changes.
