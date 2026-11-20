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
