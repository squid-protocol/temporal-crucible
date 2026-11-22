# Repair-radius variants on GitGalaxy's own history: results (EXPLORATORY; pre-declared in `docs/self_lattice_and_radius_plan.md` Amendment 2, commit 9bfe1f9; 2026-11-20)

Full tables: `repair_radius/results.md` (scripts `tools/selfhistory/radius_v1.py`, `radius_v1_posthoc.py`). Run by an agent at low priority in about 40 seconds; numbers checked against the output files.

## V1: where do successive repairs land? (626 fix PRs by title prefix or `bug` label; 379 fix commits with Python engine functions; 39,285 pairs of a fix and a later fix within 30 days; 79,567 "outside" functions from 372 later fix commits; call graph of the first daily scan at or after the earlier fix)
Observed rate over null rate, 95% bootstrap interval over later-fix commits:
| relation | vs null A (random same-size function) | vs null B (file-mates) |
|---|---|---|
| within 1 hop, either direction | 1.91 [1.66, 2.16] | 1.40 [1.29, 1.50] |
| within 2 hops, either direction | 1.91 [1.66, 2.16] | 1.29 [1.21, 1.37] |
| within 3 hops, either direction | 1.80 [1.57, 2.02] | 1.31 [1.22, 1.40] |
| caller within 2 hops | 2.56 [2.17, 2.95] | 2.58 [2.25, 2.95] |
| callee within 2 hops | 1.56 [1.33, 1.81] | 0.91 [0.83, 0.98] |
Same-day follow-ups (lag at most 2 days, 10% of pairs): 2.45 [2.13, 2.79] against null A, 1.33 [1.22, 1.44] against null B.
Declared verdicts: V1-R1 (within 2 hops above 3x null A): **not met** (1.91, upper bound 2.16). V1-R2 (above 1.5x null B): **not met** (1.29 [1.21, 1.37]; a small excess beyond the file). V1-R3 (callers over callees above 1.5): **not met on raw rates** (0.88 [0.73, 1.06]); met on excess over null B (2.85 [2.38, 3.43]); the declared wording is ambiguous between the two, so both are reported. V1-R4 (excess falls with hops): **not met** (1.91, 1.91, 1.80 against null A; callers against null B rise with hops).

## The permutation check does not come out clean
Shuffling which later fix is paired with each earlier fix (within lag bins) leaves the excess almost unchanged: within 2 hops about 1.85 against null A, 1.33 against null B. So most of the V1 excess is not about the pairing.

## Post hoc (added after seeing the permutation result; exploratory; nothing above altered)
Hypothesis: fix commits keep touching a small recurring set of hot functions, so a repo-wide random null is too easy. Null C draws from the functions touched by any fix commit in the 30 days before the later fix, weighted by touch count.
Concentration: 428 distinct functions account for 1,169 fix touches; the top 5% take 30% of touches, the top 20% take 59%; 56% of the "outside" functions of a later fix had already been touched by an earlier fix.
Against null C the overall excess disappears: within 2 hops 0.88 [0.75, 1.00], same-file 0.87 [0.74, 1.00], callers about 0.94, callees 0.82 [0.70, 0.97]; the permutation check against null C gives about 0.95. Only the same-day stratum keeps a modest excess (within 2 hops 1.21 [1.05, 1.38]; same-file 1.32 [1.18, 1.46]; callees 1.29 [1.08, 1.54]), the signature of an author finishing their own change.
Reading: successive repairs land near each other only as much as the recurrence of hot functions predicts. In this repo the "radius" is hot-spot concentration (the repeat-repair finding: 52% of fix edits in functions fixed twice or more), not a ripple along the call graph.

## V2: the 10 agreed cause -> fix pairs (descriptive)
4 of 10 give nothing to measure (three have no Python engine functions in cause or fix; the cause PR of issue 2204 has no first-parent commit). Issue 3929 (the lazy-compilation cause): cause = 7 functions in `core/detector.py`, fix = 2 in `galaxyscope.py`, no overlap and no relation at 1-3 hops. Issue 1193: fix overlaps the cause on 3 functions; of 3 outside functions, all in the same file. Issue 3909: cause is a 55-function sweep, fix 25, 12 overlapping; 11 of 13 outside functions in the same file; 4 callers and 5 callees at 1 hop. Issue 5525: 1 overlap; 3 outside functions, all in the same file and all callees. Issue 3946: no overlap; 1 of 6 outside functions in the same file. Issue 2827: the fix function is the cause function. Mostly same file, sometimes neighbours on the call graph; n = 10, no verdicts.

## Caveats
Different quantity from the curl experiment (successive repairs, not cause to fix) on a young repo with agent-written commits; the curl result for causes (9.3x within 2 hops) is not contradicted. 32% of outside functions (37,707) were dropped because they were absent from the earlier fix's scan (mostly newer files), and early call graphs are tiny (169 nodes in March, 3,286 in November); function identity is (path, name); rows repeat the same later-fix function under many earlier fixes, handled by the bootstrap over later-fix commits but not burst clustering by time; null C is post hoc.
