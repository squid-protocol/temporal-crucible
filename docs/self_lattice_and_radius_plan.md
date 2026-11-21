# Two follow-up experiments on GitGalaxy's own history: lattice-position stability and repair radius (plan fixed 2026-11-20, before the numbers)

EXPLORATORY. Written after the owner asked (2026-11-20) whether the box has room for the repair-radius experiment and "others about the stability of functions on their lattice position".
Everything below is declared before the lattice displacements were computed. Compute cost of both is small (one niced core, minutes; no new scans); the timing sensitivity pass continues alongside.

## A. Lattice-position stability (runs first)
Position = a function's 37-dimensional vector in the scanner's reference frame (the sfs `Reference` lens vectors, z-scored), taken from the lineage ledger over the 180 daily scans; units = engine functions of 3+ lines (same unit rule as evo/analyze.py); lineages born after the first snapshot.
Displacement d(k) = Euclidean distance between a function's position at birth and at the first snapshot at least k days later (k = 7, 30, 90), for functions still alive then.
- L1 (settles early) [partly seen: the identical-at-birth shares at 7/30/90 days were already computed]: the median displacement at 30 days is at least 70% of the median at 90 days (most movement happens in the first month). Refuted below 50%.
- L2 (size, not era): displacement depends on size at birth (larger functions move more). Measured as the rank correlation of d(30) with lines at birth within an era; reported per era (Gemini, Claude, fleet). Not seen before.
- L3 (era): displacement at 30 days is larger in the Gemini era than in the fleet era (the identical-share was 66% vs 75%). Seen in direction before; reported as description.
No other hypothesis is tested now. A repair-linked version (do functions that are later repaired drift more before the repair than size-matched controls) is deferred until the repair pairs exist as a list.

## B. Repair radius (design decision needed before running)
The registered design is `docs/sensor-overhaul/sensors/ripple_radius.md` (temporal-crucible branch sensor-overhaul): hypotheses R1-R6 on curl, where each fix NAMES the commit that caused it, so the cause is an independent label.
GitGalaxy has no `Fixes:` trailers. The generator derives causes by BLAME of the lines each fix removes (464 pairs; 746 unnamed fix-like commits, 552 resolved). That makes the cause location partly circular: the blamed commit touched the same lines, so the fix is in the same function or file by construction. Consequences if run as-is: R6 (a minority of fixes in the same function) cannot be interpreted; R1 and R2 (distance on the call graph) are biased towards "close".
Proposed adaptation (not yet approved): keep the pairs but measure the radius from the fixed function to the OTHER functions the causing commit touched, excluding the function(s) whose lines were blamed, with the same nulls (A: size-matched random; B: file-mates) and the daily scan at or after the cause as the call graph. R6 reported descriptively only. Calls are Python here, C-family there; function names come from hunk headers (`def name`).
This replicates R1-R5 on a different language with weaker labels; it cannot confirm them. If the owner prefers, run the original design unchanged and report R1/R2 as biased.

## Amendment 2 (2026-11-20, owner: stop scaling the cause labels; "is there any repair radius variant we can do?"). Declared before any radius number exists.
The blame-derived pairs stay unused (circular); the pilot's labels are too few to power the original R1-R6. Two variants that need no new labels:

### V1: where do successive repairs land? (label-free; fix commits only)
Events: fix commits = merged PRs whose title starts with `fix`/`bugfix` or that carry the `bug` label, mapped to their first-parent squash commit (6,363 PRs map); functions touched per commit from the evolution generator's diff cache (Python, engine units: gitgalaxy/ or backend/, no tests, no standards/).
Pairs: a fix commit A and every LATER fix commit B within 30 days. For each function g touched by B and not touched by A (the "outside" functions, as in the original design): the call-graph relation of g to the set of functions touched by A, on the call graph of the first daily scan at or after A (resolved, single-candidate call edges from `fcall_data`; nodes = (path, function)): same file as an A function; caller within k hops; callee within k hops (k = 1, 2, 3).
Nulls: (A) a random engine function of the same size decile in that scan; (B) a random other function from the same file as g. 200 draws per observed function, seed 2982; 95% bootstrap intervals over (B) fix commits.
Strata: lag between A and B of at most 2 days versus more (same-day follow-ups are an author finishing their own change).
- V1-R1 (radius): g is within 2 hops (either direction) of A's functions more often than the repo-wide null (ratio above 3).
- V1-R2 (beyond the file): against null B the ratio within 2 hops is above 1.5.
- V1-R3 (direction): successive repairs land in callers of the earlier repair's functions more often than in callees (ratio above 1.5).
- V1-R4 (decay): excess over null falls with hops (1 > 2 > 3).
Refutations: no excess against null B (the radius is file locality), callees as common as callers, or no ripple at all. Reported as a replication of the curl pattern for a different quantity (successive repairs, not cause-to-fix), on a young repo with agent-written commits; a time-clustering confound (the same worker fixing the same subsystem in a burst) is partly handled by the nulls and by the lag strata, not removed.
Prior work: logical (co-change) coupling versus structural dependency is well studied; V1 is a descriptive measurement on this repo, not a novelty claim.

### V2: the 10 agreed cause -> fix pairs (descriptive only; n = 10)
Pairs from `docs/self_evolution/cause_labeller_pilot/agreed_pairs.json`; the original R1-R6 definitions (ripple_radius.md) with the same call graph rule; reported per pair, no intervals, no verdicts. Purpose: see whether the original quantities can be computed on this repo at all.
