<!-- input snapshot hash fb9a176c82 -->
# Mechanism buckets, quiet-step test, text screen (Amendment 1 + 2)

Events (LOCALISED, passes merged, deduped by commit): 35 (32 with a CPU-metric corpus, 3 files-only). First-parent commits 6700; engine-path (touch core or standards) 1634, of which 27 are cache-gap core commits (merges/root absent from the diff cache; function count unknown) and excluded from the quiet test: 1607 used. EXPLORATORY.

Effect of the cache gap on the base-rate quiet share: 81.1% excluding them vs 81.5% if they were silently counted as 0-function (quiet).

## Bucket counts (cutoff 3 functions)

| bucket | events | engine-path commits | all commits |
|---|---|---|---|
| a standards (no core) | 5 | 614 | 614 |
| b core, <=3 funcs (quiet) | 12 | 690 | 690 |
| c core, >3 funcs | 15 | 303 | 303 |
| d only tools/tests/docs/other | 1 | 0 | 5037 |
| e no files | 0 | 0 | 29 |
| gap: core, not in diff cache | 2 | 27 | 27 |

Cutoff 5 functions: events b/c = 19/8, engine-path b/c = 827/166. Strictly standards-only commits: events 0, engine-path 18. Cache-gap events: 21f84abe4a, 92dae57c58.

## Quiet-step test

Each test compares the event group with its own complement among engine-path commits (cache-gap commits excluded): the share, its exact 95% interval, the pooled Fisher exact test and an era-stratified Mantel-Haenszel test use the SAME populations. 'Others' = engine-path commits minus ALL event commits for the all-events tests, minus the >25% events only for the >25% test. Eras by commit date: gemini <07-06, transition 07-06..07-21, claude 07-22..09-26, fleet >=09-27.

### primary: CPU-metric events (files-only events excluded) (32 events; 3 not in the engine-path or cache-gap, excluded)

| quiet definition | events quiet | share (95% CI) | others quiet | Fisher OR | Fisher p | MH OR | MH p (strata used) |
|---|---|---|---|---|---|---|---|
| (a)+(b), quiet = core with <=3 functions (primary) | 15/29 | 52% (33% to 71%) | 1287/1575 = 81.7% | 0.24 | 0.0003 | 0.28 | 0.0021 (4) |
| (a)+(b) with a cutoff of 5 functions | 22/29 | 76% (56% to 90%) | 1417/1575 = 90.0% | 0.35 | 0.0237 | 0.45 | 0.1463 (4) |
| strict bucket (a) alone (only standards files) | 0/29 | 0% (0% to 12%) | 18/1575 = 1.1% | 0.00 | 1.0000 | 0.00 | 1.0000 (3) |

Per era (primary definition): gemini: events 1/5 quiet, others 23/40; transition: events 0/1 quiet, others 22/29; claude: events 8/14 quiet, others 607/755; fleet: events 6/9 quiet, others 635/751

### all events incl. files-only (35 events; 3 not in the engine-path or cache-gap, excluded)

| quiet definition | events quiet | share (95% CI) | others quiet | Fisher OR | Fisher p | MH OR | MH p (strata used) |
|---|---|---|---|---|---|---|---|
| (a)+(b), quiet = core with <=3 functions (primary) | 17/32 | 53% (35% to 71%) | 1287/1575 = 81.7% | 0.25 | 0.0002 | 0.31 | 0.0026 (4) |
| (a)+(b) with a cutoff of 5 functions | 24/32 | 75% (57% to 89%) | 1417/1575 = 90.0% | 0.33 | 0.0132 | 0.44 | 0.1022 (4) |
| strict bucket (a) alone (only standards files) | 0/32 | 0% (0% to 11%) | 18/1575 = 1.1% | 0.00 | 1.0000 | 0.00 | 0.9955 (3) |

Per era (primary definition): gemini: events 2/6 quiet, others 23/40; transition: events 0/1 quiet, others 22/29; claude: events 9/16 quiet, others 607/755; fleet: events 6/9 quiet, others 635/751

### CPU events above 25% (13 events; 0 not in the engine-path or cache-gap, excluded)

| quiet definition | events quiet | share (95% CI) | others quiet | Fisher OR | Fisher p | MH OR | MH p (strata used) |
|---|---|---|---|---|---|---|---|
| (a)+(b), quiet = core with <=3 functions (primary) | 5/13 | 38% (14% to 68%) | 1299/1594 = 81.5% | 0.14 | 0.0008 | 0.19 | 0.0053 (4) |
| (a)+(b) with a cutoff of 5 functions | 9/13 | 69% (39% to 91%) | 1432/1594 = 89.8% | 0.25 | 0.0373 | 0.38 | 0.2081 (4) |
| strict bucket (a) alone (only standards files) | 0/13 | 0% (0% to 25%) | 18/1594 = 1.1% | 0.00 | 1.0000 | 0.00 | 1.0000 (3) |

Per era (primary definition): gemini: events 1/3 quiet, others 24/43; transition: events 0/1 quiet, others 22/29; claude: events 2/6 quiet, others 614/765; fleet: events 2/3 quiet, others 639/757

Reference: share of ALL events (including events outside the engine path, which count as not quiet) in (a)+(b) at cutoff 3: 17/35 = 49%.

## Text screen (performance words on commit subject + PR title)

Population for both recall and precision: engine-path first-parent commits. Precision = events hit / all engine-path commits hit. Events missed by the sampling or below T are not events here, so they count against precision (it is a lower bound).

### Corrected regex (DEVIATION from join_steps.py: closing word boundary, no 'batch', 'index' without trailing space)
- Hits among engine-path commits: 54 of 1634 = 3.3%; among non-event engine-path commits 3.1%.
- Recall: 5 of 34 engine-path events = 15% (95% 5% to 31%); over all 35 events 5 hit.
- Precision: 5 of 54 = 9.3% (event base rate 2.1%). Fisher OR 5.46, p = 0.0044.
- Events hit: 46a6aff44c, 68ff0c3885, 2a70f9ac86, 7e2808c964, 115f265465.

### join_steps.py regex as inherited (for comparison)
- Hits among engine-path commits: 74 of 1634 = 4.5%; among non-event engine-path commits 4.3%.
- Recall: 5 of 34 engine-path events = 15% (95% 5% to 31%); over all 35 events 5 hit.
- Precision: 5 of 74 = 6.8% (event base rate 2.1%). Fisher OR 3.83, p = 0.0165.
- Events hit: 46a6aff44c, 68ff0c3885, 2a70f9ac86, 7e2808c964, 115f265465.

## Resolutions of ambiguities

- Engine-path commit = touches at least one core or standards file. Engine functions = distinct (path, function) in the diff cache for core paths; absent core commits (merges, root) are flagged 'gap' and excluded, not counted as quiet.
- Bucket order: no files -> e; any core -> gap/b/c; else any standards -> a; else d. (d)/(e) overlap in the plan; here (e) = no file changed. (a) allows tests/docs alongside; strict (a) is shown separately.
- Primary excludes files-metric events; size above 25% uses the CPU boundary_rel only.
