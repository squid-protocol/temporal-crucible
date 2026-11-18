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

## Validation design: more repositories, by fix type, sweeps against organic changes (hypotheses fixed 2026-11-17 before computing)
The named-cause links exist in volume only for curl (libgit2, redis, libxml2 have 10 to 16 usable), so the validation uses a **forward design that needs no naming**: for each quarterly interval i, the functions edited in it (the crucible's tree-sitter edit events, `ts_edits_*`, code edits only) split into **sweep edits** (events in a sweep or migration, `tools/turn/sweeps.py detect`) and **organic edits** (a function is "sweep" only if all its code edits that interval are sweep edits). Fix commits (v3c events, by class) in interval i+L, L = 1 to 3 quarters later (L = 0 shown separately: order within a quarter is unknown). A fixed function outside the changed set is asked: is it within h calls (callers, callees, either) of the changed set, against a **same-file null** (its file-mates of similar size, outside the changed set), computed exactly. Observed over expected by summing over fix commits; 95% intervals resample fix commits. Graph: snapshot at the end of interval i, confident resolved edges, functions with a name unique in their file only. Repositories: curl, libgit2, redis, libxml2 (C), prometheus (Go), sphinx (Python), ripgrep (Rust); function names from git hunk headers (git's language drivers for Go, Python, Rust).
- **V1 (replication).** For fixes a quarter after organic changes, the fixed function is within 1 call of a changed function more often than file-mates (pooled ratio above 1.3), in at least 5 of 7 repositories.
- **V2 (sweeps).** The ratio after **sweep** edits is lower than after organic edits, with an interval that includes 1 (mechanical changes leave no trail of fixes in their call neighbours).
- **V3 (fix type).** The ratio is largest for **regression**-class fixes, smaller for **other-fix**, and about 1 for **extrinsic** fixes (whose cause is outside the history).
- **V4 (time).** The ratio falls with lag: one quarter above two above three.
- **V5 (space).** One hop above two hops.
- **V6 (direction).** Enrichment in callers (dependents) is at least that in callees.
**Would surprise:** no excess outside curl; sweeps as strong as organic changes; extrinsic fixes as near as regressions (the radius would then be a map of where work happens, not of causes).

## Validation results (2026-11-17; seven repositories, forward design; output `ripple_forward_output.txt`, script `tools/sensor/ripple_forward.py`)
Repositories: curl, libgit2, redis, libxml2 (C), prometheus (Go), sphinx (Python), ripgrep (Rust). Changed functions per quarter: organic 34 to 227, sweep 2 to 132, signature edits 8 to 84. Ratios are observed over expected for random same-size file-mates; the pooled organic, one-quarter-later, within-one-call cell holds 7,394 fix commits. Related earlier work: `tools/turn/surface_area/ripple_test.py` asked whether measured reach predicts where a sweep's *edits* land (answer: about twice the base rate, no better than size and file); this asks where *fixes* land.

**Headline.** The forward association is real, small and consistent: fixed functions lie within one call of a changed function about 9% more often than file-mates do (pooled 1.09 [1.07, 1.12]), above 1 in all seven repositories (curl 1.07, libgit2 1.09, redis 1.10, libxml2 1.10, prometheus 1.07, sphinx 1.14, ripgrep 1.37 on 49 fixes), with intervals clear of 1 in five. It is much weaker than the named-cause result in curl (1.77), because the changed set (a whole quarter of edits) is so broad that about 40% of random file-mates are already within one call of it.

| hypothesis | verdict | evidence |
|---|---|---|
| V1 replication (pooled ratio above 1.3, at least 5 of 7 repositories) | **direction replicates, size does not** | pooled 1.09 [1.07, 1.12]; 7 of 7 repositories above 1, 5 of 7 with an interval clear of 1, none of the five above 1.15; against same-size random functions (not file-mates) 1.35 [1.32, 1.38] |
| V2 sweep edits show a weaker radius, interval including 1 | **barely** | pooled sweep 1.06 [1.01, 1.11] against organic 1.09 [1.06, 1.12]; by repository the order flips in libxml2 (1.14 against 1.10) and sphinx (1.28 against 1.14) and holds in curl, redis, libgit2 |
| V3 regression strongest, other-fix weaker, extrinsic about 1 | **not supported** | pooled organic one quarter later: regression 1.09 [1.03, 1.14], other-fix 1.09 [1.07, 1.12], extrinsic 1.10 [1.00, 1.21], latent 1.11 [1.00, 1.22]. Extrinsic fixes (cause outside the history) show the same ratio: in this broad design the radius cannot tell caused fixes from others |
| V4 decay with lag | **supported for regression and other-fix** | regression by lag 0, 1, 2, 3 quarters: 1.12, 1.09, 1.06, 1.02; other-fix 1.10, 1.09, 1.08, 1.06; extrinsic has no pattern (1.00, 1.10, 1.00, 1.14) |
| V5 one hop above two hops | **supported** | either direction 1.09 against 1.05; callers 1.21 against 1.13 |
| V6 callers at least as enriched as callees | **supported, strongly** | within one call: callers **1.21 [1.17, 1.25]** against callees **1.03 [1.00, 1.06]** (regression: 1.21 [1.11, 1.32] against 1.07 [0.98, 1.15]); fixes land in the code that depends on a changed function, not in what it depends on |

**Added after looking (a response to the dilution, motivated by the named-cause result for signature changes):** with only **signature-changing edits** as the changed set (8 to 84 functions per quarter), callers within one call are enriched **1.23 [1.12, 1.33]** and callees **0.98 [0.89, 1.06]**, pooled over 6,917 fix commits. Callers above 1 in 5 of 6 repositories (curl 1.43, redis 1.46, prometheus 1.36, sphinx 1.19, libxml2 1.12; libgit2 0.88, where callees are 1.34). By fix type: other-fix 1.25 [1.14, 1.39], regression 1.21 [0.93, 1.53] (831 fixes, wide), extrinsic 0.97 [0.66, 1.40] (454), latent 1.22 [0.65, 2.07]: extrinsic is the only class without the caller excess, but its interval includes the others' values.

**Fix type, in plain terms.** Separating by type does not sharpen the radius in the broad design (regression, other, extrinsic and latent all sit at about 1.1). The decay with lag is the only place the types differ: regression and other-fix fall toward 1 by three quarters, extrinsic does not. With signature changes as the exposure, the caller excess is present for other-fix and regression and absent for extrinsic. Together: a modest causal component under a larger general tendency for fixes to cluster near recently changed code, whatever the cause.

**Sweeps, in plain terms.** Fixes follow sweep edits into their call neighbours about as often as they follow organic edits (1.06 against 1.09); there is no clean "mechanical changes leave no ripple". Sweep sets are large and tied to specific names, so the comparison is noisy.

**Same function.** Of fix commits whose function can be found a quarter after a change, the fixed function was itself changed in that quarter in 55% (curl), 24% to 43% (libgit2, redis, libxml2, prometheus) and 22% (sphinx); the named-cause links gave 71% in curl.

**Caveats.** Every ratio depends on the file-mate null being the right baseline: it removes file location and size, not author, feature or release timing, which also cluster work in call neighbourhoods. Function names from git hunk headers are matched by path and name, with names ambiguous within a file dropped (a larger loss in Python and Go, where methods share names). The static call graph misses calls through function pointers and callbacks. The changed set is a quarter wide, so the timing of change against fix inside a quarter is unknown (lag 0 is mixed order). The sweep sets are partly defined by the detector's name pairs. Tests: six hypotheses fixed beforehand, one analysis added after looking (signature set). Seven repositories, four languages, three of them one repository each.

**What this says for the idea.** The blast radius is a real, direction-specific, short-range effect: after a change, fixes concentrate slightly in the callers of the changed functions (and, when the change altered a signature, noticeably so), and the effect fades over about three quarters. It is a map for review and testing around a change, not a predictor strong enough to rank functions: the effect is 10% to 25% above a same-file baseline, against 77% in the cases where the cause is known.

## Per-commit design (hypotheses fixed 2026-11-17 before running; script `tools/sensor/ripple_commits.py`)
The forward test's changed set is a quarter of edits, so about 40% of random file-mates are already within one call of it and the contrast is diluted (pooled 1.09, against 1.77 in the named-cause curl study). Tightened: pair each fix with the **individual commits of the 45 days before it** (up to 6 sampled per lag bucket of under 1, 1 to 3, 3 to 7, 7 to 14, 14 to 30, 30 to 45 days; commits touching more than 40 functions left out), the commit's own changed functions as the set, same file-mate null, same seven repositories.
- **P1.** For commits within 7 days before the fix, the within-one-call ratio is at least 1.3 pooled (the dilution explanation).
- **P2.** The ratio falls with lag: commits 14 to 45 days before show a clearly lower ratio than those within 7 days.
- **P3.** Callers are more enriched than callees at short lags.
- **P4.** The share of pairs where the fix touches a function the earlier commit touched falls with lag.
- **P5.** Regression-class fixes show the highest ratio at short lags; extrinsic fixes stay near 1 at every lag.
**Would surprise:** ratios near 1.1 even at under 3 days (the quarter-wide result was not dilution: the radius is weak), or no difference between extrinsic and regression fixes at short lags.

### Per-commit results (2026-11-17; seven repositories; outputs `ripple_commits_output.txt` and, regression fixes with the commit they name as their cause left out, `ripple_commits_regression_unnamed_output.txt`)
Pairs: 4,248 curl fixes, 1,337 libgit2, 2,053 redis, 2,167 libxml2, 1,256 prometheus, 2,416 sphinx, 90 ripgrep, each with up to 36 sampled commits of the previous 45 days (about 1.0M relation rows). Ratios are observed over expected from same-file functions, within one call, either direction.

| hypothesis | verdict | evidence |
|---|---|---|
| P1 at least 1.3 for commits within 7 days before the fix | **only for the day before** | by days before the fix: under 1 d **1.36 [1.29, 1.44]**, 1 to 3 d 1.26, 3 to 7 d 1.19. A single commit as the changed set gives more than the quarter-wide set (1.09) and less than the known-cause curl pairs (1.77): the dilution explains part of the gap, not all |
| P2 the ratio falls with lag | **partly** | all fix types 1.36, 1.26, 1.19, 1.20, 1.19, 1.17 across the six lag buckets: a fall in the first week, then flat at about 1.18, not toward 1. By repository: libgit2 1.27 within 7 days against 1.04 at 14 to 45 days, redis 1.35 against 1.21, libxml2 1.30 against 1.19, prometheus 1.25 against 1.13; curl 1.21 against 1.19 and sphinx 1.16 against 1.14 flat |
| P3 callers more than callees at short lags | **supported, and a clearer picture** | under 1 d: callers **1.61 [1.49, 1.74]**, callees 1.22 [1.14, 1.32]; by 3 to 7 d the callee excess is gone (1.03 [0.95, 1.11]) while callers stay at **1.48** and still 1.42 [1.33, 1.51] at 14 to 30 d. Two parts: a short-lived coupling in both directions, and a persistent excess in the callers (the code that depends on what changed) |
| P4 same-function share falls with lag | **supported, steeply** | the fix touches a function the earlier commit touched in 7.9% of pairs under 1 d, 3.8% at 1 to 3 d, 2.7%, 2.0%, 1.7%, 1.5% at 30 to 45 d (regression 10.4% falling to 1.3%) |
| P5 regression highest at short lags; extrinsic near 1 at all lags | **not as stated** | regression fixes do not decay: 1.27, 1.29, 1.26, 1.23, 1.25, 1.32 over the six buckets, and with the commit each fix names as its cause removed: 1.20, 1.25, 1.34, 1.29, 1.17, **1.37 [1.23, 1.51]** at 30 to 45 d, so the persistence is not the named cause. Other-fix falls from 1.39 to 1.15; extrinsic is 1.21, 1.27, 1.16, 1.17, 1.10, 1.11 (intervals mostly including 1, not near 1 at short lags); latent is noisy (n 396 to 1,035) |

**What this changes.** The radius is not mainly a recent-work effect: regression-class fixes stay about 1.2 to 1.4 times as likely to be within one call of changes made up to 45 days earlier, and the excess is in the callers (1.42 to 1.50 at 3 to 30 days, with the callee excess gone after a day). Other fixes cluster near very recent changes and fall toward 1.15 with time. Together with the signature result this supports the review order in `gitgalaxy change` (changed signature first, its callers named).

**Caveats.** Same as the forward design (file-mate null leaves author and release timing uncontrolled; static call graph; names from hunk headers, with ambiguous names dropped), plus: candidates are sampled (6 per bucket), so each fix is compared with a sample of its neighbours in time; the graph is the first quarterly snapshot after the earlier commit, so a fixed function that did not exist yet is dropped; the regression class includes reverts and fixes that only say "regression"; ripgrep (90 fixes) and the regression-only per-repository cells for libgit2 and redis are too small to read; sphinx and prometheus regression cells have wide intervals. P1 to P5 were fixed beforehand; the named-cause exclusion was added after seeing the first regression result.

## Function pointers and callbacks, found with tree-sitter (2026-11-17; `tools/sensor/ts_refs.py`, `tools/sensor/ripple_links_refs.py`; output `ripple_refs_curl_output.txt`)
**Question.** The static call graph has no edge for a function passed as a callback, stored in a table of function pointers or reached through a pointer, so the radius was probably understated.

**How big is the blind spot** (one snapshot per repository; a reference is an identifier naming a function defined in the same snapshot, in a value position: argument, initialiser, assignment, `&f`, cast, return; left out: calls, declarations, member access, dereferences and comparisons, which cannot be told from a variable of the same name without scoping). Precision spot check: 13 of 14 random references were genuine (dispatch tables, `my_setopt(curl, CURLOPT_READFUNCTION, tool_read_cb)`); the one miss, a dereference of a variable named like a function, led to the dereference rule.
| repository | functions with no static caller | of them referenced as a pointer or callback | functions with a static caller also referenced as a pointer |
|---|---:|---:|---:|
| curl | 895 | **725 (81%)** | 72 of 2,420 (3%) |
| redis | 2,380 | 1,328 (56%) | 123 of 5,841 (2%) |
| libxml2 | 869 | 355 (41%) | 63 of 2,517 (3%) |
| libgit2 | 5,463 | 880 (16%) | 144 of 4,122 (3%) |
Most functions with no static caller in curl are callbacks, not dead code; in libgit2 the uncalled functions are mostly public API entry points. Only 2% to 3% of statically called functions are also used as pointers, so the blind spot is a specific group of functions, not a general thinning of the graph.

**Does it change the radius?** The curl named-cause pairs (212 with a fixed function outside the changed set) on three graphs:
| graph | within 1 call (either direction) | against file-mates | different-file fixes, within 1 call | against file-mates |
|---|---:|---:|---:|---:|
| engine calls only | 41.0% | 1.77 [1.48, 2.20] | 19.2% | 2.08 [1.29, 3.95] |
| plus references (a function that registers a callback gets an edge to it) | 43.9% | 1.87 [1.52, 2.24] | 21.2% | 2.42 [1.28, 5.36] |
| plus siblings (functions filled into the same table) | 44.8% | 1.81 [1.52, 2.20] | 21.2% | 2.46 [1.30, 4.78] |
**Reading.** The missing edges add about three percentage points of reach and nudge the enrichment up slightly (1.77 to 1.87; cross-file 2.08 to 2.42, interval overlapping), without changing any conclusion: the radius was understated a little, not by much, in curl. Callers stay the more enriched direction (2.51 against 1.78 within one call; cross-file 3.37 against 1.83). Not tested: the forward design on seven repositories with these edges; the Linux kernel, where function-pointer tables (`struct ..._ops`) carry much of the structure and the gap is likely larger; callbacks registered through string or numeric keys; and the engine's own `reference` edges (59 in curl) against this extraction.

## OpenSSL and FreeBSD, named-cause pairs from `Fixes:` trailers (hypotheses fixed 2026-11-17 before the graphs were built or any distance computed)
**Data.** The kernel convention `Fixes: <sha>` names the commit that caused a bug. Usable pairs (reverts and self-references out; both commits touch C or header files): **OpenSSL 261** (median lag 500 days; 3% within two days, against about a third in curl; inducing commits mostly 2014 to 2026) and **FreeBSD 192** (median lag 61 days; 23% within two days; inducing commits mostly 2021 to 2025). Graphs: quarterly scan snapshots, OpenSSL from 2014 (the 17 older pairs fall away), FreeBSD from 2021 over the kernel and base system (`sys` without `sys/contrib`, `lib`, `sbin`, `bin`, `usr.bin`, `usr.sbin`, `stand`, `libexec`; about 20,000 files instead of 110,000; pairs in vendored trees such as `contrib` and `crypto` fall away). Method as for curl (`ripple_links.py`): functions from git hunk headers, same-file null, exact; fixed functions outside the inducing commit's set; callers and callees within one to three calls; tree-sitter references not used here.
- **T1 (replication).** Within two calls of the changed functions, the fixed function is found at least 1.3 times as often as a same-file function (curl: 1.54), pooled over OpenSSL and FreeBSD.
- **T2 (callers).** Callers more enriched than callees, as in curl (2.7 against 1.7 within one call).
- **T3 (time).** The effect fades with lag: strongest for fixes within 30 days, weaker for fixes a year or more later (OpenSSL's long lags make this testable; in curl the cross-over between same-day and later fixes was flat).
- **T4 (same function).** A majority of fixes touch a function the inducing commit also touched (curl 71%); lower in OpenSSL, where lags are long.
- **T5 (signatures).** When the inducing commit changed a parameter count, fixes land in callers more often (curl 33% against 13%); too few pairs to test here, reported if 15 or more.
**Would surprise:** no excess against file-mates in either repository (curl's result would then be a curl effect); callees as enriched as callers.

### OpenSSL results (2026-11-17; `ripple_openssl_output.txt`; FreeBSD to follow)
**Data.** 261 `Fixes:` pairs; usable 177 (44 have no function name in a hunk header, 35 not found in the nearest quarterly snapshot, 5 sweeps, 10 with no same-file functions to compare); **126 have a fixed function outside the set the inducing commit changed**. In 42% of pairs the fixed function is also one the inducing commit changed (curl: 71%).

| hypothesis | verdict | evidence (126 pairs) |
|---|---|---|
| T1 radius at least 1.3 against file-mates | **supported** | within 2 calls 51.6% against 34.1% for same-file functions: **1.57 [1.32, 1.95]** (curl 1.54); within 1 call 1.69 [1.31, 2.24] (curl 1.77). Against random same-size functions 30x |
| T2 callers more enriched than callees | **not replicated** | within 1 call: callers 1.62 [1.12, 2.36], callees **1.75 [1.22, 2.55]**; within 2 calls callers 1.46, callees 1.79; in absolute terms callees 23.0% against callers 19.8% (curl: 29.7% against 16.5%, with callers the more enriched). The caller direction is not a general result |
| T3 the effect fades with lag | **supported, and sharper than in curl** | fix within 30 days: within 1 call **2.11 [1.43, 3.24]**, within 2 calls 2.01 [1.54, 2.89]; 30 to 365 days: 2.27 [1.53, 3.73] and 1.88 [1.30, 3.15]; **a year or more later: 1.20 [0.77, 1.89] and 1.21 [0.91, 1.63]**, intervals including 1: no excess left. 85 of the 177 pairs are a year or more apart (median lag 500 days) |
| T4 a majority of fixes touch a function the inducing commit also touched | **not for OpenSSL** | 42% (45% within 30 days, 57% for 30 to 365 days, 34% after a year) |
| T5 signature changes ripple to callers | not tested yet (pooled with FreeBSD) | |
**Reading so far.** The radius replicates: fixes are found within one or two calls of the change about 1.6 times as often as same-file functions in both curl and OpenSSL, with the same size of effect. Two curl findings do not carry over: the caller direction (OpenSSL's callees are as enriched), and, as it turns out, the persistence: for OpenSSL's long-lag fixes (a year or more) the excess is gone, so the radius is a short-range effect in time as well as in the graph. Caveats as for curl, plus: 35 pairs fell outside the nearest snapshot (functions that did not exist at the snapshot, or renamed), 44 have no function name in a hunk header (OpenSSL's headers and macros), and the intervals are wide (126 pairs; 28 to 65 in the lag strata).

## Retrieval and same-author tests (hypotheses fixed 2026-11-17 before running; `tools/sensor/ripple_rank.py`)
Pairs: named-cause pairs from curl (message-referenced), OpenSSL and FreeBSD (`Fixes:` trailers), the ones whose fixed function lies outside the inducing commit's changed set.

**Retrieval.** Given an inducing change (its changed functions), rank every other function in the call graph of the nearest quarterly snapshot and ask how high the function the fix later touched sits. Rankers: random; size only (largest first); same file as a changed function; call-graph distance only (callers and callees within 1, 2, 3 calls); file then graph; graph then file; file then graph then size. Metric: expected hit rate in the top 5, 10, 20, 50 (ties split evenly) and median rank, per pair, with the best-ranked fixed function counted.
- **R1.** File then graph beats file alone at the top 20 by at least 5 percentage points, pooled (the graph adds ordering within and beyond the changed file).
- **R2.** For fixes in a different file from every changed function, graph distance beats size at the top 50.
- **R3.** The best ranker puts the fixed function in the top 20 for at least 40% of pairs, pooled.
- **R4.** Size alone is no better than random by a large margin (hit at 20 under twice the random rate): the effect is about neighbourhood, not about big functions.

**Same author.** Split pairs by whether the author of the fix is the author of the inducing commit.
- **A1.** The excess within 2 calls against same-file functions is present for different-author pairs: ratio at least 1.3.
- **A2.** Same-author pairs have a higher share of fixes in a function the inducing commit touched than different-author pairs.
- **A3.** The radius ratio is not larger for same-author pairs: if the effect were only "one person finishing their own work", it would vanish for different authors.
**Would surprise:** the graph adds nothing over the file in retrieval (R1 fails); the radius vanishes for different-author pairs.

### OpenSSL and FreeBSD pooled results (2026-11-17; `ripple_trailer_pooled_output.txt`)
**Data.** OpenSSL: 261 pairs, 177 usable, 126 with a fixed function outside the changed set. FreeBSD (kernel and base system, quarterly from 2021): 192 pairs, **103 usable** (40 not found in the nearest snapshot, 40 with no function name in a hunk header, 9 sweeps, 3 without same-file functions), **53 with a fixed function outside the changed set** (fixed function also changed by the inducing commit in 69%, against 42% in OpenSSL). Pooled: 280 usable, **179 outside the changed set**.

| hypothesis | verdict | evidence |
|---|---|---|
| T1 radius at least 1.3 against same-file functions | **supported** | pooled within 2 calls 52.5% against 31.3%: **1.71 [1.50, 2.00]**; within 1 call 1.88 [1.55, 2.39]. By repository: OpenSSL 1.57, **FreeBSD 2.17 [1.67, 2.95]** within 2 calls (curl 1.54) |
| T2 callers more enriched than callees | **not supported** | pooled within 1 call callers 1.87 [1.36, 2.61], callees 1.88 [1.38, 2.49]; FreeBSD callers 2.77 and callees 2.21 (overlapping), OpenSSL callees 1.75 against callers 1.62. Direction is repository-specific |
| T3 the effect fades with lag | **partly** | pooled within 1 call: fix within 30 days 2.13 [1.40, 3.11], 30 to 365 days 2.43 [1.71, 3.79], a year or more 1.49 [1.06, 2.09]; within 2 calls 2.02, 2.03, **1.41 [1.14, 1.80]**. A fade, but not to nothing pooled: OpenSSL alone loses it (1.2), FreeBSD does not (2.07 on 17 pairs) |
| T4 a majority of fixes touch a function the inducing commit touched | **borderline** | pooled 52% (FreeBSD 69%, OpenSSL 42%, curl 71%) |
| T5 signature changes ripple to callers | **supported** | inducing change altered a parameter count (40 pairs, 29 with a fix outside): callers within 1 call **34.5%**, against 20.1% for all pairs, **3.83 [1.50, 9.12]** against same-file functions; callees 1.37 [0.42, 3.40]. The same pattern as curl (33% against 13%) in a second and third repository |
**Fixes in a different file from every changed function** (62 pairs): within 2 calls 27.4% against 18.2%, **1.56 [1.12, 2.32]**; within 1 call 1.34 [0.67, 2.63]: a real but modest cross-file effect, and the one that bears on Lyu et al.'s "ghost commits" (inducing commits sharing no file with the fix).
**Reading.** Across curl, OpenSSL and FreeBSD (three repositories, three projects' conventions) fixes land within one or two calls of the change about 1.5 to 2 times as often as in same-file functions; the caller/callee direction varies by repository; and a signature change sends the fix to the callers in all three (curl 33% against 13%; pooled OpenSSL and FreeBSD 34.5% against 20.1%). The fade with time is repository-dependent. This is the review-order result in `gitgalaxy change` (changed signature first, callers named), now supported beyond curl; the broader "callers first for every change" claim is not.

### Retrieval and same-author results (2026-11-17; `ripple_rank_output.txt`; curl, OpenSSL, FreeBSD pooled)
**Data.** 787 usable named-cause pairs; **391 have a fixed function outside the inducing commit's changed set** (curl 212, OpenSSL 126, FreeBSD 53), the pairs retrieval is asked about. Candidates per pair: median 6,036 functions (curl 3,515, OpenSSL 21,055, FreeBSD 142,899).

**Retrieval, pooled (expected share of pairs whose fixed function is in the top k; ties split evenly; the best-ranked fixed function counts):**
| ranker | top 5 | top 10 | top 20 | top 50 | median rank |
|---|---:|---:|---:|---:|---:|
| random | 0.1% | 0.2% | 0.4% | 0.9% | 3,018 |
| size only (largest first) | 0.8% | 2.2% | 4.1% | 7.2% | 1,365 |
| same file as a changed function | 10.5% | 17.4% | 27.2% | 41.1% | 122 |
| call-graph distance only (1 to 3 calls) | 13.0% | 19.8% | 28.0% | 40.5% | 135 |
| file, then graph | 22.5% | 32.8% | 42.8% | 54.7% | 31 |
| graph, then file | 20.9% | 29.5% | 38.8% | 52.4% | 42 |
| file, then graph, then size | **27.2%** | **37.6%** | **46.5%** | **58.1%** | **27** |
For the 166 pairs where the fix is in a different file from every changed function, graph distance alone is best: top 20 **12.4%** (top 50 21.0%) against size 6.0% (10.8%), file-first rankers 0.1% to 6.6%, random 0.4%.

| hypothesis | verdict | evidence |
|---|---|---|
| R1 file then graph beats file alone at the top 20 by 5 points | **supported** | 42.8% against 27.2% pooled (+15.6); per repository +13 (curl), +18 (OpenSSL), +20 (FreeBSD) |
| R2 for different-file fixes graph beats size at the top 50 | **supported** | 21.0% against 10.8% pooled; both far above random (1.0%) but small in absolute terms |
| R3 best ranker at least 40% in the top 20 | **supported** | 46.5% pooled (curl 45.3%, OpenSSL 46.8%, FreeBSD 50.9%); top 5 27.2% |
| R4 size alone no better than twice random | **not supported** | size is about 10 times random at the top 20 (4.1% against 0.4%); in OpenSSL it scores 0% because the largest functions are rarely the fixed ones; far weaker than file or graph |
**Reading.** A watchlist of 20 functions chosen by (same file, then call distance, then size) holds the function the fix later touches for about 46% of pairs where the fix lands outside the changed code, from candidate sets of 3,500 to 143,000 functions; the hit rate does not fall as the repository grows. For fixes in a different file the graph carries it alone (12% at the top 20). Not shown: the share of all pairs covered once the changed functions themselves are on the list (a fix is in a changed function in 42% to 71% of pairs).

**Same author (pooled, 787 pairs: 326 same author, 461 different).**
| | pairs with a fix outside the changed set | within 1 call against same-file functions | within 2 calls | fix in a function the inducing commit touched |
|---|---:|---|---|---:|
| same author | 138 of 326 | 1.75 [1.35, 2.26] | 1.59 [1.30, 1.93] | 71% |
| different author | 253 of 461 | 1.85 [1.55, 2.20] | 1.62 [1.43, 1.83] | 60% |
| hypothesis | verdict | |
|---|---|---|
| A1 different-author pairs show the excess (at least 1.3) | **supported** | 1.62 [1.43, 1.83] within 2 calls; by repository curl 1.70, OpenSSL 1.53, FreeBSD 1.68 |
| A2 same-author pairs touch the same function more often | **supported** | 71% against 60% |
| A3 the radius is not larger for same-author pairs | **supported** | equal pooled (1.59 against 1.62; callers within 1 call 2.22 against 2.14); in curl larger for different authors (3.20 against 2.09). OpenSSL has only 14 same-author pairs |
**Reading.** The call-graph clustering of fixes does not come from one person finishing their own work: when someone else fixes a function near your change, it is as close to the change as when you do. What remains confounded is a shared feature, release or reviewer, which the author split does not remove.

### Combined coverage: the watchlist is the changed functions plus the top k neighbours (hypotheses fixed 2026-11-17 before running; `tools/sensor/ripple_coverage.py`)
Retrieval so far ranked only pairs whose fix lies outside the changed set. A real watchlist would list the changed functions too. Coverage = share of named-cause pairs whose fixed function is on the list "changed functions + the top k functions by (same file, then graph distance, then size)", for k = 0, 5, 10, 20, 50. Denominators: usable pairs (787: both commits' functions found in the nearest snapshot) and, as a conservative bound, all named pairs (1,208: curl 755, OpenSSL 261, FreeBSD 192; the unusable ones count as misses).
- **C1.** The changed functions alone cover at least half of usable pairs (curl 71%, OpenSSL 42%, FreeBSD 69% touched a changed function).
- **C2.** Adding the top 20 raises coverage of usable pairs to at least 75%.
- **C3.** Over all named pairs the top-20 list still covers at least 50%.
- **C4.** The extra gain from the top 20 over the changed functions alone is at least 15 percentage points in every repository.
**Would surprise:** coverage over all named pairs under 40% with k = 20 (most of the benefit would then rest on the filtered subset).

#### Combined coverage results (2026-11-17; `ripple_coverage_output.txt`)
Share of named-cause pairs whose fixed function is on the list "changed functions + top k neighbours" (ranker: same file, then call distance, then size). The changed set has a median of 3 functions (75th percentile 8, 90th 17), so a k = 20 list is about 23 functions long (75th percentile 28, 90th 37).

| | usable pairs | k = 0 (changed only) | k = 5 | k = 10 | k = 20 | k = 50 | **all named pairs, k = 0** | **all named pairs, k = 20** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| curl | 507 of 755 | 71.2% | 78.5% | 80.9% | 83.0% | 86.2% | 47.8% | 55.8% |
| OpenSSL | 177 of 261 | 42.4% | 55.4% | 62.1% | 67.2% | 77.4% | 28.7% | 45.6% |
| FreeBSD | 103 of 192 | 68.9% | 75.7% | 78.6% | 83.5% | 84.5% | 37.0% | 44.8% |
| **pooled** | **787 of 1,208** | **64.4%** | **72.9%** | **76.4%** | **79.5%** | **84.0%** | **42.0%** | **51.8%** |
By lag, pooled usable pairs: fix within 30 days 69.2% (changed only) to 82.6% (k = 20); 30 to 365 days 61.7% to 78.0%; **a year or more 45.1% to 67.3%** (the neighbours add 22 points there, 13 for fast fixes).

| hypothesis | verdict | evidence |
|---|---|---|
| C1 the changed functions alone cover at least half of usable pairs | **supported pooled** | 64.4%; OpenSSL alone 42.4% (long lags) |
| C2 top 20 raises usable coverage to at least 75% | **supported pooled** | 79.5% (curl 83.0%, FreeBSD 83.5%, OpenSSL 67.2% below) |
| C3 over all named pairs the top-20 list covers at least 50% | **just supported pooled** | 51.8% (curl 55.8%, OpenSSL 45.6%, FreeBSD 44.8%) |
| C4 the top 20 adds at least 15 points in every repository | **not supported** | pooled +15.1; curl +11.8, FreeBSD +14.6, OpenSSL +24.8 |
**Reading.** Putting the changed functions and the 20 best-ranked neighbours on a review list finds the function the fix later touches in about 80% of the pairs we could map and in about half of all named pairs (the unmapped pairs count as misses). The neighbours matter most where the lag is long (a year or more: 45% to 67%) and in OpenSSL, where fixes are slower and more distant. The conservative figure, 51.8%, is the one to quote.

**A speed bug found and fixed.** `ripple_links.graph` recomputed the size percentiles once per function (quadratic: hours on FreeBSD's 143,000-function graphs); it now computes them once. Results are unchanged; the earlier FreeBSD runs were slow for this reason, not because of the analysis.

## A faster tool: `tools/sensor/blast_radius.py` (2026-11-17)
**Why.** The blast-radius scripts were slow for avoidable reasons: one `git show` per commit, graphs as Python dicts of sets, a *sampled* same-file baseline (200 draws, each a list scan; hours at 140,000 functions), a quadratic percentile in the graph loader (found and fixed) and a single process. At the kernel's size (about 17,000 usable pairs, 53 snapshots of 144,000 functions) the old code would take days.
**What it does instead.**
1. Functions touched by each commit: **one** streaming `git log --no-walk --stdin -p -U0` pass over all needed commits, cached on disk.
2. Graphs: one sparse-matrix structure per snapshot (callers and callees as CSR matrices; sizes, deciles and file ids as arrays); each pair's 1, 2 and 3-call neighbourhoods are three sparse matrix-vector products per direction.
3. Baselines: the **exact** expected rate, from counts (same-file functions within one size decile, outside the changed set; and random same-decile functions), so no sampling and no list scans.
4. Parallel over snapshots (each worker loads its snapshot once and measures all its pairs), results to a table; a separate `report` step groups by repository, lag, cross-file or subsystem with bootstrap intervals over pairs in seconds.
**Validation on curl** (755 named pairs; the same inputs as the earlier scripts): the same 507 measured pairs, 212 with a fixed function outside the changed set, 71% same function; within 1 call 1.81 [1.47, 2.28] (earlier 1.77 [1.48, 2.20]), within 2 calls 1.57 [1.32, 1.89] (1.54 [1.32, 1.81]), callees 1.73 (1.66), callers 2.37 (2.69; sampling noise); cross-file pairs 2.56 within 1 call (2.08 earlier, with a slightly different definition of "different file"; intervals overlap). **Time: 5 seconds** end to end against minutes for the earlier version (OpenSSL and FreeBSD took over an hour each).
**Not in the tool yet:** the signature-change split (needs arguments per snapshot), same-author split (needs authors), the retrieval and coverage rankers, tree-sitter callback edges (`ts_refs.py`) as an optional graph layer.

## Kernel run: hypotheses fixed 2026-11-17 before any kernel distance was computed
Input: the 34,349 pairs with the causing commit from 2014 on whose commits touch scanned files (`linux_fixes_pairs.md`); quarterly scans of the core subsystems; same method as curl, OpenSSL and FreeBSD (`blast_radius.py`).
- **K1 (radius).** Pooled, the fixed function (outside the changed set) is within 2 calls of the changed code at least 1.3 times as often as same-file functions of similar size, with an interval excluding 1, and above 1.3 in at least 7 of the 10 largest subsystems (kernel, mm, include/linux, net/ipv4, net/core, net/netfilter, fs, fs/btrfs, block, net/sched).
- **K2 (ghost commits).** For the 11% of pairs where the fix and the causing commit share no file, the excess within 2 calls is at least 1.3 (a connection the file view cannot see).
- **K3 (direction).** Callers against callees is not the same in every subsystem: the caller-minus-callee gap within one call changes sign in at least 3 of the 10 largest.
- **K4 (time).** The ratio for fixes a year or more after the change is lower than for fixes within 30 days, pooled and in at least 7 of the 10 largest subsystems, with a smooth decline across four lag buckets.
- **K5 (precision).** The interval of the pooled within-2-calls ratio is narrower than 0.15 (the point of the scale).
**Would surprise:** no excess in the cross-file pairs (the ghost commits stay unexplained); a ratio below 1.2 pooled (the earlier repositories were a small-sample artefact).

### Kernel results (2026-11-17; `linux_blast_report_main.txt`, `linux_blast_report_subsystems.txt`; `blast_radius.py`, about 4 minutes end to end)
**Data.** 34,349 `Fixes:` pairs (causing commit from 2014 on, both commits touching a scanned file); 4,328 have no function name in a commit's hunk headers, 452 are sweeps, 5,095 not found in the nearest snapshot: **24,474 measured, 14,444 with a fixed function outside the changed set**, in 52 quarterly snapshots of the core subsystems (28 times curl's usable pairs). The fixed function is also a changed function in 58% of pairs (curl 71%, OpenSSL 42%, FreeBSD 69%). Ratios are against same-file functions of similar size, outside the changed set, computed exactly.

| | within 1 call | within 2 calls | callers (1 call) | callees (1 call) |
|---|---|---|---|---|
| **all pairs** (14,444) | 2.44 [2.38, 2.51] (44% vs 18%) | **1.99 [1.96, 2.03]** (52% vs 26%) | 2.41 [2.31, 2.53] | 2.62 [2.53, 2.70] |
| fix in the same file as a changed function (10,864) | 2.43 | 1.98 [1.94, 2.02] | 2.33 | 2.66 |
| **fix in a different file from every changed function (3,580)** | 2.60 [2.36, 2.83] | **2.08 [1.93, 2.22]** (24% vs 12%) | **3.52 [3.08, 4.11]** | 2.10 [1.85, 2.40] |
| fix under 30 days after the change (2,305) | 2.62 | 2.13 [2.04, 2.24] | 2.51 | 2.75 |
| 30 to 365 days (5,676) | 2.46 | 1.99 [1.93, 2.05] | 2.51 | 2.64 |
| a year or more (6,463) | 2.37 | 1.94 [1.89, 2.00] | 2.30 | 2.55 |

| hypothesis | verdict | evidence |
|---|---|---|
| K1 radius at least 1.3, in 7 of the 10 largest subsystems | **supported, in all 10** | pooled 1.99 [1.96, 2.03]; kernel 2.19, mm 2.16, include/linux 1.96, net/ipv4 2.11, net/core 2.91, net/netfilter 1.95, fs 2.29, fs/btrfs 2.55, block 2.41, net/sched 1.92; the next eight (xfs, ipv6, bluetooth, mptcp, nfs, security, mac80211, include/net) 1.65 to 2.69 |
| K2 cross-file pairs show the excess (the "ghost commits") | **supported** | 2.08 [1.93, 2.22] within 2 calls, 2.60 within 1 call; per subsystem 1.40 (xfs) to 3.12 (fs); in absolute terms 24% of the cross-file fixes are within 2 calls, so the graph connects a quarter of them and leaves three quarters unexplained |
| K3 direction differs by subsystem (3 or more of the 10 largest on the other side) | **not supported as stated** | callees above callers within one call in 8 of the 10 largest (gap -0.11 to -1.31); callers above callees in block (+0.51) and net/sched (+0.81); in the next eight bluetooth (+0.45) and mac80211 (+0.03). Heterogeneity exists, but the majority direction is callees |
| K4 the ratio is lower a year or more later than within 30 days | **supported, mildly** | 2.13 -> 1.99 -> 1.94 pooled (non-overlapping intervals for the extremes); lower in 8 of the 10 largest subsystems (not include/linux, which is equal, nor fs/btrfs, slightly higher); the fade is only about 10%: **the radius persists for years** (compare OpenSSL, where it vanished) |
| K5 interval narrower than 0.15 | **supported** | pooled within 2 calls [1.96, 2.03]: width 0.07 |
**Findings that were not predicted.** (1) **The direction depends on where the fix is.** When the fix is in the same file as a changed function, callees are slightly more enriched than callers (2.66 against 2.33): the fix lands in a helper the change uses. When the fix is in a different file, callers dominate (3.52 against 2.10): the fix lands in code elsewhere that depends on the changed function. This resolves the curl-against-OpenSSL disagreement as a mix of the two cases in different proportions. (2) The effect is larger than in curl, OpenSSL and FreeBSD (about 2.0 against 1.5 to 1.7 within 2 calls), plausibly because the kernel's modular structure ties fixes to call neighbours more tightly, or because tens of thousands of pairs remove small-sample noise; not resolved. (3) The effect barely fades with time (1.94 a year or more later), against OpenSSL's vanishing excess.
**Caveats.** Same-file baseline (no author, feature or release control; the earlier same-author test passed in three repositories but was not rerun here); static call graph (the kernel's function-pointer tables `..._ops` are everywhere: callbacks are missing, so the radius is probably understated, and by more than in curl; not tested here); function names from hunk headers (kernel macros such as `SYSCALL_DEFINE3` and `EXPORT_SYMBOL` contexts can mis-name a function); the pair selection requires scanned `.c`/`.h` files on both sides, so drivers are mostly out; 29% of pairs (no function name, sweeps, not found in a snapshot) are unmeasured and the 71% measured may differ from the rest.

## Kernel controls: same author, signature change (hypotheses fixed 2026-11-17 before running; added to `blast_radius.py`)
Same 34,349 kernel pairs and 52 snapshots. Authors from `git log --format=%ae`; a **signature change** = a function the causing commit changed whose parameter count differs between the snapshot before and the snapshot at or after the commit (as in the curl and OpenSSL/FreeBSD runs).
- **S1 (signature to callers).** For pairs where the causing commit changed a parameter count, the fix lands in callers (within 1 call) more than callees, and the callers ratio is above the pooled callers ratio (2.41): at least 3.0.
- **S2.** The signature effect holds in the cross-file pairs and in both lag groups (under 30 days; a year or more).
- **A1.** The radius (within 2 calls, same-file baseline) is at least 1.3 for different-author pairs, with an interval excluding 1; **A2.** same-author pairs have a higher same-function share than different-author pairs (earlier pooled: 71% against 60%); **A3.** the radius is not larger for same-author pairs (earlier: 1.59 against 1.62). The kernel has many reviewers and maintainers: different-author pairs should be the majority.
**Would surprise:** the radius vanishing for different-author pairs (it would then be one person's work session); no caller enrichment after signature changes (it would then be a small-repository effect).

### Kernel controls: results (2026-11-17; `linux_blast_report_controls.txt`)
| group | all pairs | outside the changed set | same function | within 1 call callers / callees | within 2 calls |
|---|---:|---:|---:|---|---|
| different author | 16,265 | 9,436 | 57% | 2.49 [2.36, 2.65] / 2.72 [2.61, 2.84] | **2.06 [2.01, 2.11]** |
| same author | 8,209 | 5,008 | 61% | 2.29 [2.15, 2.46] / 2.45 [2.35, 2.59] | 1.88 [1.82, 1.94] |
| signature changed (a changed function's parameter count differs from the previous snapshot) | 5,136 | 2,962 | 61% | 2.27 [2.11, 2.43] (26% vs 11%) / 2.28 [2.17, 2.40] (42% vs 18%) | 1.76 [1.70, 1.81] |
| no signature change | 19,338 | 11,482 | 58% | 2.48 [2.35, 2.61] (16% vs 6%) / 2.76 [2.66, 2.86] | 2.09 [2.04, 2.14] |

| hypothesis | verdict | evidence |
|---|---|---|
| A1 radius at least 1.3 for different-author pairs | **supported** | 2.06 [2.01, 2.11]; different-author pairs are 66% of all |
| A2 same-author pairs touch the same function more often | **supported, slightly** | 61% against 57% |
| A3 the radius is not larger for same-author pairs | **supported** | 1.88 same author against 2.06 different: **larger for different authors**; the clustering is not one person finishing their own work |
| S1 after a signature change the fix lands in callers more than callees, callers ratio at least 3.0 | **not supported** | callers 2.27 against callees 2.28; callers ratio 2.27 against 2.48 without a signature change |
| S2 the signature effect holds in cross-file pairs and both lag groups | not tested (S1 failed) | |
**The earlier signature result does not hold at scale.** In curl (33 pairs) callers within 1 call were 33% against 13%, and in OpenSSL and FreeBSD pooled (29 pairs) 3.83 times the same-file baseline [1.50, 9.12]. With 2,962 kernel pairs the caller excess is the same as for other changes (2.27 against 2.48), while the absolute caller rate is higher after a signature change (26% against 16%) because the baseline rises with it (11% against 6%: these changes touch well-connected functions). So the earlier figure was a small-sample overestimate, or specific to those repositories. Consequences: the wiki page and the `gitgalaxy change` output sentence that cited it are corrected (callers are listed as a checklist, since they must agree with a changed signature, not as where fixes tend to land); the forward-design figure (1.23 across seven repositories) measures something different (signature-changing edits against fixes in later quarters, against a same-file baseline) and is kept but weighed lightly.

## What kinds of changes? Fix mechanisms and causing-change types in the kernel (hypotheses fixed 2026-11-17 before classifying; `tools/sensor/change_kinds.py`)
**Method.** For the 24,474 measured kernel pairs: (a) the **fix mechanism** from the fix commit's subject and body by an ordered keyword rule set (lifetime: use-after-free, double free, leak, refcount; concurrency: race, deadlock, lock, RCU, atomics; NULL dereference or missing check; bounds and overflow; uninitialised data; error-path handling; build or compile problem; other); (b) the **causing-change type** from the verb after the subsystem prefix in its subject (add or support: feature; convert, move, rename, split, refactor, cleanup, simplify, replace: restructuring; remove or drop; optimise or improve; a fix: fix of a fix) plus size (lines changed, functions and files touched, subsystems crossed); (c) per class, the same-function share, cross-file share, lag, and the radius (within 2 calls against same-file functions). The rules are checked by reading 15 random commits per class (precision reported).
- **Q1.** Three mechanisms (lifetime, NULL or missing checks, error-path handling) make up at least 40% of the classified fixes.
- **Q2.** Concurrency fixes have a longer median lag than NULL-check fixes (at least 1.5 times).
- **Q3.** Restructuring changes (convert, move, rename, split, refactor) have a higher cross-file share of fixes than feature additions.
- **Q4.** Cross-file pairs are enriched (at least 1.3 times their overall share) for lifetime and API-contract-type fixes (refcount, ownership, error-path) against local-logic fixes.
- **Q5.** The radius (within 2 calls, same-file baseline) differs by fix mechanism: the largest class value is at least 1.3 times the smallest among classes with 300 or more pairs.
- **Q6.** Larger causing changes (more functions touched) have a higher cross-file share of fixes (monotone over four size bands).
**Would surprise:** one mechanism or one change type accounting for most of the radius (then "the pattern" is mostly one phenomenon), or no difference in radius by mechanism.

### What kinds of changes: results (2026-11-17; `linux_change_kinds_output.txt`; the first run that also used the body-based calls is `..._with_body.txt`)
**Method check.** Spot checks (12 random commits per class) showed the subject-based calls right about 85 to 90% of the time and the body-based calls (16% of pairs) right about a third of the time (stack-trace words), so the classes below use the **subject only**: 29% of the 24,474 pairs get a mechanism, 71% stay "other" (a coarse classifier: the classes describe a subset, not the whole). The causing-change type comes from the verb in its subject (an unreliable label for "use", "make", "set", folded into restructuring).

**Fix mechanism** (subject-classified fixes: 7,037):
| mechanism | pairs | median lag | same function | cross-file | within 2 calls (against same-file functions) |
|---|---:|---:|---:|---:|---|
| concurrency (race, deadlock, lock, RCU, atomics) | 2,447 | 296 d | 60% | 15% | 1.97 [1.85, 2.08] |
| lifetime (use-after-free, leak, refcount, dangling) | 1,715 | **350 d** | 66% | **11%** | 1.93 [1.80, 2.09] |
| error handling (error path, unwind, return value) | 852 | 187 d | 65% | **12%** | 2.07 [1.88, 2.32] |
| bounds and overflow | 650 | **424 d** | 56% | 14% | 2.22 [1.96, 2.51] |
| NULL dereference or missing check | 574 | 116 d | 60% | 14% | 2.18 [1.88, 2.51] |
| build or compile problem | 499 | **31 d** | 60% | 13% | 2.25 [1.94, 2.59] |
| uninitialised data | 300 | 94 d | 60% | 16% | 1.65 [1.39, 1.96] |
| other (unclassified) | 17,437 | 241 d | 57% | 15% | 1.99 [1.94, 2.03] |

**Causing-change type:**
| type | pairs | median lag | same function | cross-file | within 2 calls |
|---|---:|---:|---:|---:|---|
| feature (add, introduce, support, implement, allow, enable) | 8,254 (34%) | 327 d | **47%** | **19%** | 1.85 [1.79, 1.91] |
| restructuring (convert, move, rename, split, refactor, use, make, remove) | 5,165 (21%) | 180 d | 65% | 12% | 1.96 [1.89, 2.04] |
| a fix (fix of a fix) | 4,037 (17%) | 189 d | **71%** | **10%** | **2.34 [2.23, 2.46]** (callers 3.35, callees 3.39) |
| optimisation (avoid, reduce, improve, skip) | 880 (4%) | 197 d | 70% | 10% | 2.11 [1.91, 2.33] |
| other | 6,138 (25%) | 228 d | 59% | 14% | 2.04 [1.97, 2.12] |

**Size of the causing change** (within 2 calls: observed against expected, ratio): changed 9 or fewer lines 38% against 13%, **2.90**; 10 to 49 lines 47% against 18%, 2.64; 50 to 199 lines 56% against 26%, 2.18; 200 or more 53% against 37%, **1.45**. By functions touched: one function 32% against 11%, **2.98**; 10 or more 66% against 45%, **1.46**. Same-function share falls from 74% (9 or fewer lines) to 44% (200 or more); cross-file share is 22% for changes of 200 or more lines (12% to 13% below), and 24% for changes crossing three or more subsystems (11% for one).

| hypothesis | verdict | evidence |
|---|---|---|
| Q1 lifetime, NULL/missing check and error handling are at least 40% of classified fixes | **supported by the letter** | 45%; but concurrency is the largest class (35% of classified), so the three are not the three biggest |
| Q2 concurrency fixes have a median lag at least 1.5 times NULL-check fixes | **supported** | 296 d against 116 d (2.6 times); the longest are bounds (424 d) and lifetime (350 d), the shortest build (31 d), uninitialised (94 d) and NULL (116 d) |
| Q3 restructuring changes have a higher cross-file share than features | **not supported (reverse)** | restructuring 12%, **features 19%** |
| Q4 cross-file pairs are enriched (1.3 times) for lifetime and error-path fixes | **not supported (reverse)** | lifetime 0.75 times and error handling 0.81 times the overall 14.6%: these are *more local*; no mechanism reaches 1.3 times (uninitialised 1.09) |
| Q5 the radius differs by mechanism (largest at least 1.3 times the smallest, classes of 300 or more) | **marginal** | 2.25 (build) against 1.65 (uninitialised) is 1.36 times, with overlapping intervals; apart from uninitialised all classes are 1.93 to 2.25: the pattern is not specific to one kind of fix |
| Q6 more functions touched, higher cross-file share, monotone | **not supported for functions touched** | 16%, 16%, 15%, 10% (falling); true for **subsystems crossed** (11%, 15%, 24%); by lines the 200-line band jumps to 22% |
**Reading.** (1) The radius is **not one phenomenon**: it appears for every kind of fix we could classify (1.65 to 2.25), and for every kind of causing change (1.85 to 2.34). (2) **How fast** a fix comes depends on what is wrong: build problems in a month, NULL and uninitialised-data fixes in three to four months, locking and lifetime bugs in ten to twelve, bounds errors in fourteen. (3) **Where** the fix lands depends on the change: features are followed by dispersed fixes (47% in the same function, 19% in another file, the longest lag), fixes of fixes and small surgical edits by tight ones (71% to 74% in the same function, radius 2.3 to 2.9). (4) Lifetime and error-path fixes are more local than average, against my prediction. (5) The ratio against the same-file baseline falls with the size of the causing change largely because the baseline rises (a large change has many functions with neighbours); in absolute terms the share of fixes within 2 calls rises from 32% to 66% as the functions touched rise from one to ten or more.
**Caveats.** Keyword classes are coarse and describe 29% of fixes; the causing-change type rests on one verb; kernel conventions (descriptive subjects) may not generalise; "feature" commits also include refactors with an "add" verb; the size bands are correlated with subsystem and era; all comparisons are associations against a same-file baseline.

## Reading the diff instead of the subject (hypotheses fixed 2026-11-17 before training; `tools/sensor/change_kinds_diff.py`)
**Method.** Features from each fix commit's `.c`/`.h` diff (`git log -p -U0`): counts and shares of added and removed lines matching patterns for NULL and error-pointer checks, locking and atomics, free, put and reference counting, error-path returns and gotos, bounds arithmetic (`min`, `max`, `clamp`, `sizeof`, comparisons against sizes), zero-initialisation, condition rewrites, type and endianness changes, build-only changes (`#include`, `#ifdef`, `EXPORT_SYMBOL`, `static`, unused markers), comment-only changes, size (lines, hunks, files). **Validation:** train on the subject-classified fixes (7,037 pairs) to predict their subject label from the diff alone, 5-fold cross-validated; this says how much of the mechanism the diff carries. **Application:** predict for the unclassified 71% and keep predictions with probability 0.6 or more; cluster the rest to see what else is there. Then repeat the lag, locality and radius tables on the larger labelled set.
- **D1.** The diff alone recovers the subject classes with cross-validated macro-F1 of at least 0.6 (chance about 0.14).
- **D2.** At probability 0.6 or more, at least half of the 17,437 "other" fixes receive a class, taking coverage from 29% to at least 60%.
- **D3.** The lag order holds on the larger set: build and uninitialised and NULL fixes shorter than locking, lifetime and bounds fixes (median lag of the three short classes under half that of the three long ones).
- **D4.** Lifetime and error-handling fixes remain more local than average (cross-file share below 0.9 times the overall share).
- **D5.** The radius across mechanisms stays within a factor of 1.5 (general pattern) with the larger sample.
**Would surprise:** diff features recovering fewer than half of the subject classes (the label would then rest on words, not changes); the "other" fixes clustering into one dominant unlabelled group (a mechanism our taxonomy lacks).

### Diff-based classification: results (2026-11-17; `linux_change_kinds_diff_output.txt`)
| hypothesis | verdict | evidence |
|---|---|---|
| D1 the diff alone recovers the subject classes, macro-F1 at least 0.6 | **not supported** | cross-validated macro-F1 **0.46**, accuracy 54% (majority class 35%); F1 by class: concurrency 0.67, lifetime 0.53, build 0.50, bounds 0.43, error handling 0.41, NULL 0.35, uninitialised 0.35; most errors fall into concurrency (lock-like patterns overlap) |
| D2 at least half of the 17,437 other fixes get a class (probability 0.6 or more) | **not supported, and the labels are unreliable** | 41% assigned (coverage 29% to 58%); reading the subjects of 35 assigned fixes (not used by the model), about a third looked right: the model was trained on fixes with descriptive subjects (a different population from the rest), so its labels for the unlabelled fixes are not used |
| D3 lag order holds | **supported** | short classes (build 58 d, uninitialised 132 d, NULL 154 d; mean 115 d) against long (bounds 358 d, concurrency 280 d, lifetime 295 d; mean 311 d) |
| D4 lifetime and error handling more local than average (below 0.9 times) | **mixed** | error handling 0.84 times, lifetime 0.91 times |
| D5 radius across mechanisms within a factor of 1.5 | **supported** | 1.83 to 2.20 (factor 1.20) over classes of 300 or more pairs |
**What the leftovers are** (the 10,279 fixes below probability 0.6, ten clusters by diff pattern): two groups hold 70%: **about 3,400 rewrite or add a condition** (more `if`, a permission or validity check, a livelock guard; example subjects "require CAP_NET_ADMIN in the device netns", "avoid livelock while updating retransmit path") and **about 3,800 remove calls to lock, alloc or get functions** ("Fix unsafe decode", "don't skb_tx_error() the source skb"). The keyword taxonomy has no class for either: the unlabelled fixes are mostly two mechanisms we had not named, not noise. **Decision:** the subject-based classes stay the reference labels; the model's labels are not used; the next step is a rule-based classification of the diff's *shape*, which needs no learning and covers every fix.

### Fix shape from the diff (hypotheses fixed 2026-11-17 before running; `tools/sensor/fix_shapes.py`)
Rule-based and complete (every fix gets a shape): comment-only; large (100 or more changed lines); removes code (removed lines at least twice the added, 4 or fewer added); adds a guard (a new condition with a return or error assignment, few lines); rewrites a condition (a removed and an added condition in a hunk); adds synchronisation or release (lock, atomic, free, put); replaces a call or argument; changes a type or declaration; adds code; small edit; other. Same tables as before: lag, same-function and cross-file share, radius.
- **SH1.** Guard additions have a shorter median lag than code removals.
- **SH2.** Code removals have the highest same-function share among shapes with 500 or more pairs.
- **SH3.** The radius across shapes with 500 or more pairs stays within a factor of 1.5 (the general pattern).
- **SH4.** Large fixes (100 or more lines) have the lowest radius and the highest cross-file share.
**Would surprise:** a shape accounting for most of the radius, or radius differing by more than a factor of 2 across shapes.

### Fix shape: results (2026-11-17; `linux_fix_shapes_output.txt`; 24,474 pairs, every fix classified)
| shape of the fix | pairs | median lag | same function | cross-file | within 2 calls |
|---|---:|---:|---:|---:|---|
| replaces a call or argument | 3,172 (13.0%) | 178 d | 62% | 12.7% | **2.45 [2.28, 2.61]** |
| changes a type or declaration | 804 (3.3%) | **111 d** | 56% | 13.4% | 2.42 [2.14, 2.76] |
| removes code | 1,443 (5.9%) | **153 d** | 61% | 13.2% | 2.32 [2.11, 2.53] |
| small edit (12 or fewer lines) | 3,594 (14.7%) | 205 d | 58% | 14.9% | 2.25 [2.10, 2.38] |
| **adds a guard** (a new condition with a return or error) | 2,419 (9.9%) | **325 d** | **45%** | **19.5%** | 2.16 [2.04, 2.31] |
| rewrites a condition | 1,901 (7.8%) | 247 d | 63% | 12.0% | 2.02 [1.87, 2.17] |
| adds synchronisation or release | 2,718 (11.1%) | 269 d | 58% | 14.9% | 1.98 [1.87, 2.10] |
| other edit | 3,910 (16.0%) | 251 d | 67% | 12.2% | 1.84 [1.79, 1.90] |
| adds code | 3,666 (15.0%) | 313 d | 51% | 18.2% | 1.82 [1.74, 1.90] |
| large (100 or more lines) | 649 (2.7%) | 315 d | **72%** | 12.0% | **1.48 [1.39, 1.58]** |
| comment only | 198 (0.8%) | 155 d | 66% | 8.1% | 2.47 [1.78, 3.54] |
Shape and subject-based mechanism agree where they should (a validation of both): "adds synchronisation or release" is 56% concurrency and 31% lifetime; "comment only" is 79% build or compile; "changes a type or declaration" is 28% build and 20% uninitialised; "adds a guard" is spread over NULL (20%), error handling (24%), lifetime (18%), concurrency (18%), bounds (14%).

| hypothesis | verdict | evidence |
|---|---|---|
| SH1 guard additions have a shorter lag than code removals | **not supported (reverse)** | guards **325 d**, removals **153 d** |
| SH2 code removals have the highest same-function share (500 or more pairs) | **not supported** | 61%; the highest are large fixes (72%), other edits (67%) |
| SH3 the radius across shapes stays within a factor of 1.5 | **marginal** | 1.48 to 2.45 (factor 1.65); 1.82 to 2.45 (1.35) without the large fixes |
| SH4 large fixes have the lowest radius and the highest cross-file share | **half** | lowest radius yes (1.48; a diff touching many functions has many neighbours), cross-file share no (12.0%; the highest is guard additions, 19.5%) |
**Reading.** The most distinctive kind of fix is the **added guard** (a missing check or early return, 10% of fixes): it is the *least local* (45% in the same function, 19.5% in another file) and the *slowest* (325 days): a missing check is typically added at a different place from the change that made it necessary, long after. By contrast, mechanical corrections (replace a call or an argument, change a type, remove code) come sooner (111 to 178 days), and tightly around the change (radius 2.3 to 2.5). Feature-like fixes ("adds code") sit with the guard additions: later and more dispersed. Both the radius and the timing therefore depend on the *shape* of the correction: the dispersed, slow fixes add something that was missing; the tight, quick ones correct something that was wrong.

### Shape of the causing change, crossed with the shape of the fix (hypotheses fixed 2026-11-18 before running; `tools/sensor/cause_shapes.py`)
The same diff-shape rules (comment only, large, removes code, adds a guard, rewrites a condition, adds synchronisation or release, replaces a call or argument, changes a type or declaration, adds code, small edit, other) applied to the **causing** commit's `.c`/`.h` diff, for the same 24,474 kernel pairs; plus whether it changed a parameter count. Tables: by causing shape (lag, same-function and cross-file share, radius), and causing shape against fix shape (lift = observed over expected if independent, cells of 100 or more pairs).
- **CS1.** Causing changes that mostly add code ("adds code") are followed by more dispersed fixes than small edits: lower same-function share and higher cross-file share.
- **CS2.** The fix shape "adds a guard" is over-represented after "adds code" causing changes (lift at least 1.2) and under-represented after "replaces a call or argument" (lift at most 0.9).
- **CS3.** The median lag differs by at least a factor of 1.5 between the slowest and the fastest causing shape (500 or more pairs each).
- **CS4.** The diagonal recurs: a fix has the same shape as its causing change more often than expected (lift at least 1.2) for at least half of the shapes with 500 or more pairs.
- **CS5.** The radius varies less across causing shapes than across fix shapes (factor below 1.65 among shapes of 500 or more pairs).
**Would surprise:** no relation between causing shape and fix shape (every lift within 0.9 to 1.1): the kind of change would then not determine the kind of failure.

#### Causing-change shape: results (2026-11-18; `linux_cause_shapes_output.txt`)
**The causing commits are mostly large.** 10,426 of 24,474 (42.6%) change 100 or more `.c`/`.h` lines; "adds code" is 23.7%, "other edit" 17.8%; every small shape is 4% or less.
| causing shape | pairs | median lag | same function | cross-file | within 2 calls |
|---|---:|---:|---:|---:|---|
| **large (100+ lines)** | 10,426 (42.6%) | **301 d** | **48%** | **17.9%** | **1.63 [1.59, 1.66]** |
| adds code | 5,809 (23.7%) | 265 d | 58% | 12.7% | 2.60 [2.49, 2.72] |
| other edit | 4,354 (17.8%) | 174 d | 71% | 11.3% | 2.51 [2.38, 2.64] |
| adds sync or release | 1,030 (4.2%) | **161 d** | 73% | 10.7% | 2.81 [2.49, 3.18] |
| adds a guard | 926 (3.8%) | 216 d | 76% | 9.4% | 2.87 [2.44, 3.29] |
| rewrites a condition | 467 (1.9%) | 138 d | 76% | 12.2% | 2.94 [2.31, 3.66] |
| removes code | 448 (1.8%) | 130 d | 65% | 16.1% | 2.34 [1.96, 2.77] |
| replaces a call or argument | 447 (1.8%) | 141 d | 70% | 14.8% | 3.40 [2.58, 4.40] |
| small edit | 417 (1.7%) | 139 d | 71% | 16.8% | 2.82 [2.17, 3.63] |
| changes a type or declaration | 136 (0.6%) | 108 d | 78% | 14.7% | 3.82 [2.42, 5.80] (n 50) |
Signature changed (5,136 pairs): radius 1.76, cross-file 11.3%; no signature change: 2.09, 15.5%; the share of "adds a guard" fixes is 9.9% in both (no relation).

**Causing shape against fix shape (lift = observed over expected if independent; cells of 100 or more pairs).** Over-represented: **adds sync or release -> adds sync or release 2.53** (289 pairs), **replaces a call or argument -> replaces a call or argument 2.07** (120), small edit -> small edit 1.65, adds a guard -> rewrites a condition 1.52, large -> large 1.39, adds a guard -> adds a guard 1.38, other edit -> replaces a call or argument 1.21. Under-represented: adds sync or release -> other edit 0.71, -> small edit 0.73, -> adds code 0.76; adds a guard -> adds code 0.80. Against the subject-classified mechanism: a causing change that adds synchronisation or release is followed by concurrency fixes 49% of the time (33% to 37% for most others); one that changes a type or declaration by bounds and overflow fixes 34% (9% to 12% otherwise; 136 pairs, a third classified); one that adds a guard by lifetime (30%) and error-handling (20%) fixes (22% to 26% and 10% to 13% otherwise): a new early return can skip cleanup (plausible; about 270 classified pairs).

| hypothesis | verdict | evidence |
|---|---|---|
| CS1 "adds code" is followed by more dispersed fixes than small edits (lower same-function share, higher cross-file) | **half** | same function 58% against 71% (yes); cross-file 12.7% against 16.8% (no); the most dispersed cause is the **large change** (48% same function, 17.9% cross-file, slowest, lowest radius) |
| CS2 "adds a guard" fixes over-represented after "adds code" (at least 1.2), under-represented after "replaces a call" (at most 0.9) | **not supported** | 0.93 after adds code; 0.72 after replaces a call (32 pairs only) |
| CS3 lag differs by at least 1.5 times between the slowest and fastest causing shape (500 or more pairs) | **supported** | large 301 d against adds sync or release 161 d (1.87 times); including smaller shapes 108 d (type or declaration) |
| CS4 the diagonal recurs (same shape as the cause, lift at least 1.2) for at least half of the shapes with 500 or more pairs | **supported** | 3 of 5: adds sync or release 2.53, large 1.39, adds a guard 1.38; adds code 1.14, other edit 1.02; smaller shapes with 100 or more pairs: replaces a call 2.07, small edit 1.65 |
| CS5 the radius varies less across causing shapes than across fix shapes (factor below 1.65) | **not supported** | factor 1.76 (1.63 to 2.87) across causing shapes with 500 or more pairs |
**Reading.** (1) **The fix often repeats the kind of edit that caused it**: adding locking is followed by locking fixes (2.5 times expected), replacing a call by call-replacement fixes (2.1 times). (2) **How large the causing change is matters most**: the 43% of causes that change 100 or more lines produce the slowest (301 days) and most dispersed fixes (48% same function, 17.9% in another file) and the weakest radius (1.63); small surgical causes (a type, a call, a condition, a guard, a small edit) produce quick, local fixes and a strong radius (2.8 to 3.8). The ratio against the baseline falls for big changes partly because the baseline rises. (3) Parameter-count changes show no special link to the kind of fix. (4) The kinds of cause and the kinds of fix are related but not tightly (lifts 0.7 to 2.5), so the shape of the change says something, not everything, about the shape of the failure.
**Caveats.** Shape rules are mine and coarse; 43% of causes land in the "large" bin, so the small shapes are few hundred pairs each with wide intervals; subject-classified mechanisms cover 29% of fixes; kernel conventions; associations against a same-file baseline.

## Replicating the shape tables on OpenSSL and FreeBSD (hypotheses fixed 2026-11-18 before running; `tools/sensor/shape_replication.py`)
Same method as the kernel (`blast_radius.py` measurements; fix and causing-commit shapes from the `.c`/`.h` diffs; the kernel's numbers are recomputed in the same table), on OpenSSL (177 measured pairs, `Fixes:` trailers) and FreeBSD (103), alone and pooled (280). The samples are small (25 to 150 pairs per shape pooled; most small shapes under 20), so "replicates" means **the direction agrees with the kernel** and is counted, with intervals shown; nothing is claimed for cells under 20 pairs.
- **RS1.** Guard-adding fixes have a lower same-function share than the pooled share of all fixes, and a longer median lag than the all-fix median (kernel: 45% against 58%; 325 d against 241 d).
- **RS2.** Fixes that replace a call or argument, change a type or remove code have a shorter median lag than the all-fix median (kernel: 111 to 178 d against 241 d), pooled.
- **RS3.** Large fixes (100 or more lines) have the lowest radius among shapes with 15 or more pairs.
- **RS4.** Causing changes are mostly large: at least 30% of causing commits change 100 or more `.c`/`.h` lines (kernel 43%), and large causes have the lowest same-function share and longest median lag among causing shapes with 15 or more pairs.
- **RS5.** The recurrence lifts on the diagonal (same shape for cause and fix) are at least 1.0 for adds sync or release and for replaces a call or argument (kernel 2.5 and 2.1), where the cell has 8 or more pairs.
**Would surprise:** more than half of the directional checks (RS1 to RS5, counted per item) pointing the other way in both repositories (kernel findings would then be kernel-specific).

#### Shape replication: results (2026-11-18; `shape_replication_output.txt`; the whole replication runs in 3 seconds; measuring OpenSSL and FreeBSD with `blast_radius.py` took 18 and 39 seconds and reproduced the earlier counts: 177 and 103 measured pairs)
**Samples.** OpenSSL 177 measured pairs, FreeBSD 103, pooled 280; fix shapes have 3 to 55 pairs each pooled, causing shapes mostly under 10 apart from "large" (156) and "adds code" (49) and "other edit" (44); few cells reach the 15 pairs a radius needs. The kernel's own table is recomputed in the same output.
| check | kernel | OpenSSL | FreeBSD | pooled OpenSSL + FreeBSD |
|---|---|---|---|---|
| RS1 guard fixes: lower same-function share and longer lag than all fixes | agrees: 45% against 58%; 325 d against 240 d | **differs** in lag: 27% against 42% (agrees), 219 d against 332 d (does not) | not testable (no guard fixes among 103) | **agrees**: 25% against 52%; 219 d against 195 d |
| RS2 call, type and removal fixes come faster than the median | agrees: 165 d against 240 d | **agrees: 11 d against 332 d** | **agrees: 13 d against 66 d** | **agrees: 11 d against 195 d** (57 pairs) |
| RS3 large fixes have the lowest radius | agrees (1.48) | not testable (12 large fixes; 4 shapes have 15 or more pairs; lowest 1.53, guard) | not testable | not testable (13 large fixes; lowest 1.55, "other edit") |
| RS4 large causes: at least 30% of causes, lowest same-function share, longest lag | agrees (43%) | share 70% and lowest same-function (33%) **agree**; longest lag **differs** ("adds code" 653 d against 292 d) | share 31% and lowest same-function (50%) agree; longest lag differs ("adds code" 197 d against 109 d) | agrees on share (56%) and same-function (37%), differs on lag (231 d against 252 d) |
| RS5 diagonal lifts at least 1.0 (sync to sync, call to call) | agrees (2.53, 2.07) | not testable | not testable | not testable (one pair per cell; lifts 3.1 and 2.9 on n of 1) |
**Scored by the rule fixed beforehand** (every check counted, a conjunction failing if any part fails): per repository 2 of 6 testable checks agree (OpenSSL 1 of 4, FreeBSD 1 of 2), pooled 2 of 4: borderline against the "would surprise" bar (more than half pointing the other way in both repositories: OpenSSL 3 of 4 differ, FreeBSD 1 of 2).
**What replicates.** (1) **Mechanical corrections are quick**: fixes that replace a call or argument, change a type or remove code come in about two weeks (11 to 13 days; the kernel 165) in both repositories. (2) **Dispersal**: guard-adding fixes are the least local (pooled 25% in the same function against 52% for all fixes); large causing changes have the lowest same-function share (33% OpenSSL, 50% FreeBSD), the highest cross-file share (27%, 22%) and the weakest radius among causing shapes with a measurable one (1.53, 1.97). **What does not, or cannot be tested at this size**: "guard fixes are slow" (OpenSSL 219 d against 332 d), "large causes are slowest" ("adds code" is), recurrence on the diagonal, large fixes having the lowest radius.
**Reading.** The kernel's shape tables are, for now, kernel results: two findings (quick mechanical corrections; dispersed fixes after large changes and guard additions) point the same way in two other projects; the rest needs a second repository with thousands of named pairs. The kernel-scale candidates need a count of `Fixes:` use first (DPDK, QEMU, systemd, U-Boot, Xen, Mesa were named by the literature scan and not counted).

## Repair radius on DPDK (second kernel-scale replication; hypotheses fixed 2026-11-18 before measuring)
Name agreed with the owner 2026-11-18: **repair radius** (how far from a change its repairs land). DPDK: 17,590 `Fixes:` pairs (about 14,700 with C/H on both sides), quarterly scans 2016 Q4 to 2026 Q4, `blast_radius.py` as for the kernel, then `shape_replication.py` with DPDK added. DPDK mandates the trailer (38% of commits), so its pairs are a different selection from the kernel's. Pairs are measured against the nearest snapshot at or after the causing commit, so causes before 2017 are dropped.
- **DR1.** Of fixes with a fixed function outside the changed set, the repair radius within 2 calls (either direction) is at least 1.5 against the same-file baseline, lower bound of the bootstrap interval above 1.3.
- **DR2.** Same-function share of all fixes is between 40% and 75% (kernel 58%; OpenSSL 42%; FreeBSD 69%).
- **DR3.** Direction: same-file fixes favour callees more than callers; different-file fixes favour callers more than callees (kernel 2.66 against 2.33; 3.52 against 2.10).
- **DR4.** Shape replication, counted per check: of RS1 to RS5 (with large enough cells now), at least 4 of 5 agree with the kernel's direction.
- **DR5.** Lag fade: ratio for fixes under 90 days exceeds the ratio for fixes over 1 year.
**Would surprise:** a radius at or below 1.2 (the pattern would then be a kernel-and-small-repository result, and the trailer selection a suspect).

#### Repair radius on DPDK: results (2026-11-18; `dpdk_blast_report.txt`, `shape_replication_dpdk_output.txt`; 41 quarterly snapshots scanned in 15 minutes, measurement 23 s)
15,829 usable pairs; 9,867 measured (6,963 with a fixed function outside the changed set); 3,235 dropped for no function name in a hunk header, 325 sweeps, 2,402 not found in the snapshot.
| | DPDK | kernel |
|---|---|---|
| same function | 49% | 58% |
| radius within 2 calls, against same-file | **1.45 [1.41, 1.48]** | 1.99 [1.96, 2.03] |
| same-file fixes: callers1 / callees1 | 1.80 / 1.73 | callees higher (2.66 / 2.33) |
| different-file fixes (1,561 pairs): callers1 / callees1 | **2.43 / 1.24** | 3.52 / 2.10 |
| radius under 30 d / 30 to 365 d / over a year | 1.48 / 1.46 / 1.42 | 2.13 to 1.94 |
| cross-file share | 15.8% | 14.6% (of kernel pairs, 3,580) |
| radius, causing change large / "adds code" / "other edit" | 1.32 / 2.07 / 2.26 | 1.63 / 2.60 / 2.51 |
| median lag, large causes / all | 254 d / 235 d | 301 d / 241 d |
| causes that are large | 69% | 43% |
| same-kind recurrence (sync -> sync; call -> call) | 10.7 (n 20); 3.6 (n 19) | 2.53; 2.07 |
| hypothesis | verdict |
|---|---|
| DR1 radius at least 1.5, lower bound above 1.3 | **failed on the point value**: 1.45 [1.41, 1.48]; the lower bound (1.41) clears 1.3. Present and strong against the "would surprise" bar of 1.2, but weaker than the kernel's 1.99 |
| DR2 same-function share 40% to 75% | **supported** (49%) |
| DR3 same-file favours callees, different-file favours callers | **half**: different-file callers 2.43 against callees 1.24 (supported, as in the kernel); same-file callers 1.80 vs callees 1.73 (not supported) |
| DR4 at least 4 of 5 of RS1 to RS5 agree | **failed: 3 of 5.** RS2 (mechanical fixes faster; but only 227 d against 235 d here), RS4 (large causes: lowest same-function share, longest lag, 69%) and RS5 (recurrence) agree; RS1 (guard fixes: lower same-function share agrees; lag 219 d against 235 d does not) and RS3 (large fixes have the lowest radius: the lowest is "comment only", 1.17; large 1.24) differ |
| DR5 radius under 30 d above radius over a year | **barely**: 1.48 against 1.42, overlapping intervals; the fade is not distinguishable |
Count by the earlier rule: per repository 5 of 11 testable checks agree (DPDK 3 of 5, OpenSSL 1 of 4, FreeBSD 1 of 2).
**Reading.** (1) **The repair radius replicates in a second large repository**, weaker (1.45 against 1.99) and uniform across lag and across fix shapes (1.2 to 1.7). (2) **The strongest replications are the dispersal ones**: large causing changes give the lowest same-function share and the longest lag in both the kernel and DPDK, and different-file fixes sit among callers more than callees in both. (3) **Details specific to the kernel**: guard fixes being slow, large fixes having the lowest radius, same-file fixes favouring callees, a clear fade with lag. (4) **Selection matters**: DPDK's near-mandatory trailer gives 69% large causing commits (kernel 43%).
**Caveats.** Same as the kernel (associations, my shape rules, nearest snapshot); DPDK's unmeasured pairs (38% had no function name in a hunk header, many of them C files with unusual layouts or headers/macros) may differ from the measured ones.

## Co-change control for the repair radius (hypotheses fixed 2026-11-18 before running; `tools/sensor/cochange_control.py`)
**Question.** Is the repair radius just co-change history in disguise? For each pair the *co-change set* is every function that changed in the same commit as any function the causing commit changed, in commits strictly earlier than the causing commit (all prior history; commits touching more than 40 functions left out as sweeps; names matched as (path, function), so renames break the link). Compared on the same pairs and the same same-file baseline: (a) the fixed function is in the co-change set; (b) within 2 calls of the changed set **and not** in the co-change set; (c) in the co-change set **and not** within 2 calls. Repositories: DPDK (6,963 pairs with a fixed function outside the changed set) and OpenSSL (126); the kernel needs a full-history function index of 1.3 million commits and is left for later.
- **CC1.** Graph proximity survives the control: the ratio for (b) is at least 1.3 with a lower bound above 1.15 on DPDK.
- **CC2.** History is a stronger signal than structure here: the ratio for (a) is at least 1.2 times the repair-radius ratio (either2) on DPDK. (Echoing the 'history predicts, structure describes' debate.)
- **CC3.** The two signals overlap only partly: of fixed functions found within 2 calls, at most half are also in the co-change set; and (c) has a ratio above 1.3.
**Would surprise:** (b) at or below 1.1 on DPDK: the call graph would then add nothing beyond change history, and "repair radius" would be a co-change effect.

#### Co-change control: results (2026-11-18; `cochange_dpdk_output.txt`, `cochange_openssl_output.txt`; blast_radius.py gained an optional `CO` item field)
DPDK, 6,963 pairs with a fixed function outside the changed set (5,042 whose changed functions have earlier co-change history; median co-change set 18 functions); OpenSSL 124 pairs (113 with history; median set 104).
| measure (ratio against same-file functions of similar size) | DPDK | OpenSSL |
|---|---|---|
| repair radius, within 2 calls | 1.45 [1.41, 1.48] | 1.57 [1.30, 1.92] |
| (a) fixed function in the co-change set | **0.76 [0.72, 0.80]** | **0.36 [0.20, 0.51]** |
| (b) within 2 calls and NOT in the co-change set | **1.60 [1.55, 1.64]** | **1.91 [1.53, 2.45]** |
| (c) in the co-change set and NOT within 2 calls | 0.67 [0.63, 0.72] | 0.28 [0.11, 0.46] |
| both signals, share of the within-2-calls hits | 17% | 9% |
| CC | verdict |
|---|---|
| CC1 (b) at least 1.3, lower bound above 1.15 | **supported**: 1.60 [1.55, 1.64] (OpenSSL 1.91); removing co-change partners raises the ratio, as they are not where the fixes are |
| CC2 co-change ratio at least 1.2 times the graph ratio | **not supported, and reversed**: fixed functions are less often earlier co-change partners of the changed functions than same-file functions of similar size (0.76; OpenSSL 0.36) |
| CC3 at most half the graph hits are also co-change hits; (c) above 1.3 | **half**: overlap 17% (supported); (c) 0.67 (not supported) |
Surprise bar ((b) at or below 1.1): not met. The call graph carries the signal that history does not, in these two repositories.
**Reading.** The repair radius is **not** co-change history under another name: the call-graph neighbourhood keeps (and strengthens) its ratio once co-change partners are excluded, and the two signals share only 17% of hits. **Caution on the reversed co-change result**: ratios below 1 mean the baseline (older, often-changed functions in the same file) are more often co-change partners than the fixed functions. One untested reason is function age: fixes land disproportionately in young functions with little prior history, which a co-change set built from earlier commits cannot contain. So this control shows that the graph is not a stand-in for co-change; it does **not** show that history is a poor predictor in general (a history signal that takes age into account is a separate test). OpenSSL has 124 pairs; the kernel was not run (a full-history function index of 1.3 million commits).

## Relaxation test: do repairs spread outward over time and then stop? (hypotheses fixed 2026-11-18 before running; `tools/sensor/relaxation.py`)
The owner's reading of the repair radius: a local change disturbs the surrounding network, which then realigns step by step toward a stable state. If that holds, (1) repairs reach farther the longer after the change, (2) successive repairs of one cause move outward, (3) repair chains settle, i.e. the chance of another repair falls with each repair so far, and (4) the gaps between successive repairs grow. Data: Linux kernel (measured pairs from `measure.pkl`, all named pairs for chain counts) and DPDK; distance = fewest calls (1, 2, 3, beyond) from a changed function to a fixed function outside the changed set, against the same-file baseline as before. Predictions, with the ones I expect to fail marked:
- **RX1 (outward with lag).** The within-1-call ratio for fixes under 30 days is at least 15% higher than for fixes over a year, in both repositories. *I expect this to fail: the within-2-calls ratio already falls only 4% to 10% from fast to slow fixes.*
- **RX2 (successive repairs move outward).** For causes with two or more measured fixes outside the changed set, the later fix is within 2 calls less often than the earlier fix, by at least 5 percentage points in both repositories (paired by cause).
- **RX3 (chains settle).** Chance of another repair falls with each repair so far: P(at least 2 | at least 1) > P(at least 3 | at least 2) > P(at least 4 | at least 3). *I expect this to fail: causes differ in how buggy they are, which makes the continuation probability rise with k, and rising is the opposite of settling.*
- **RX4 (gaps grow).** For causes with three or more fixes within 3 years (cause at least 3 years before the end of the history), the median gap from fix 2 to fix 3 exceeds the median gap from fix 1 to fix 2, which exceeds the lag to fix 1 only if repairs decelerate. Counted as supported if both gap comparisons go up in both repositories.
**Would surprise (for relaxation):** RX1 and RX2 both failing and RX3 rising would mean repairs do not spread outward and bad changes keep producing repairs: a different picture, a cluster of "sick" changes, not a network settling.

#### Relaxation test: results (2026-11-18; `relaxation_output.txt`)
| | kernel | DPDK | prediction |
|---|---|---|---|
| RX1 radius within 1 call, under 30 d / over a year | 2.62 / 2.37 (ratio 1.11) | 1.70 / 1.61 (1.06) | needed 1.15: **not supported** (both) |
| RX2 later fix within 2 calls less often than the earlier fix (causes with 2+ fixes outside the changed set) | 53.6% -> 52.6% (-1.0 points [-3.1, +1.2]; 2,449 causes) | 53.6% -> 49.4% (-4.2 points [-6.6, -1.7]; 1,350 causes) | needed -5 points in both: **not supported** (DPDK points the right way, just short; the kernel shows nothing) |
| RX3 chance of another repair, k = 1 to 5 | **0.29, 0.41, 0.54, 0.60, 0.66** | **0.39, 0.51, 0.60, 0.63, 0.70** | needed falling: **not supported, and reversed in both** (rising, as I expected) |
| RX4 gaps: lag to fix 1 / fix 1 to 2 / fix 2 to 3, median days | 43 / 28 / 50 | 32 / 35 / 80 | needed increasing: kernel **not supported** (28 d is shorter than 43 d), DPDK **supported** |
Other numbers: fixes per cause (kernel) 1: 66,236, 2: 15,935, 3: 5,201, 4: 2,447, 5: 1,225, 6+: 2,379; the share of causes that are fixes themselves 10% (kernel), 16% (DPDK). Radius by lag at 1 / 2 / 3 calls falls only slowly with lag everywhere (kernel either2 2.13 -> 1.93, DPDK 1.48 -> 1.39).
**Wording defect in RX4 as registered**: the sentence compared two gaps with the lag to fix 1 in a muddled way; it is scored here by the rule the code applies (lag to fix 1 < gap 1 to 2 < gap 2 to 3, each median).
**Reading.** The "network settling outward" picture is **not supported**: repairs do not travel farther with time (flat to slightly weaker radius), successive repairs of one cause move outward only slightly or not at all (DPDK -4 points, kernel none), and the chance of another repair **rises** with every repair so far (0.29 -> 0.66 in the kernel). What the data fit better: **some changes are simply "sick"** (they generate repeated nearby repairs, one after another) and most are not; the radius describes a fixed neighbourhood where those repairs fall, not a wave that expands and fades. Rising continuation is what heterogeneity between changes produces, and a settling process would have produced the opposite.
**Caveats.** Kernel chain counts cover only pairs touching scanned core subsystems; counts for recent causes are right-censored (not enough time to be fixed), which lowers the continuation probabilities but does not by itself make them rise with k; "later fix" may repair an independent bug from the same cause, not a consequence of the first repair; associations only.
**Open follow-up.** Which causes become "sick"? Test whether the number of fixes per cause relates to the causing commit's size, shape, author experience or hub position, using the existing pair tables (the data exist: `cause_shapes.pkl`, `shapes.pkl`).

## Which changes become sick? (hypotheses fixed 2026-11-18 before running; `tools/sensor/sick_changes.py`)
"Sick" = the causing commit has two or more named fixes. Unit = causing commit among the measured pairs of the kernel and DPDK; outcome = at least 2 named fixes (primary: causes at least 3 years before the end of the history, so every cause had time to collect fixes); features = lines changed (added plus removed), diff shape of the causing commit (`fix_shapes.shape`), author's earlier commits in the repository (tenure), functions changed. **Selection caveat fixed in advance:** only causes with at least one named fix are in the data, so "sick" means "repeatedly fixed given fixed at least once"; it cannot be compared with changes that were never fixed.
- **SK1 (size).** P(2+ fixes) for causes of 100 or more lines is at least 1.3 times that for causes under 20 lines, in both repositories.
- **SK2 (shape).** "Adds code" causes have P(2+ fixes) at least 1.2 times that of the small surgical shapes (adds a guard, rewrites a condition, replaces a call, small edit) pooled, in both.
- **SK3 (tenure).** Authors with under 20 earlier commits in the repository have P(2+ fixes) at least 1.2 times that of authors with 200 or more. *I expect weak or absent: the kernel's bug-introduction literature is mixed on experience.*
- **SK4 (size is the driver).** In a logistic model with log lines, shape and tenure together, the odds ratios for shape and for tenure move at least a third of the way toward 1 compared with their separate odds ratios: size takes most of the effect.
- **SK5 (agreement).** The direction of SK1 to SK3 agrees in both repositories.
**Would surprise:** SK1 below 1.1 in both: size would then not make a change sicker, and the "bad changes keep needing repairs" picture would need another driver.

#### Which changes become sick: results (2026-11-18; `sick_changes_output.txt`)
Causing commits at least 3 years old at the end of the history, measured, with an author: kernel 12,533 (34.5% have 2+ named fixes, mean 1.76 fixes); DPDK 4,896 (42.9%, mean 2.08).
| causing change | kernel P(2+ fixes) | DPDK |
|---|---|---|
| under 20 lines | 14.5% | 13.6% |
| 20 to 99 | 29.2% | 27.3% |
| 100 to 499 | 55.0% | 51.6% |
| 500 or more | **77.8%** (mean 5.2 fixes) | **77.2%** (mean 4.2) |
| 1 function changed / 20 or more | 20.1% / 61.4% | 30.0% / 64.3% |
| small surgical shapes pooled | 13.9% | 13.3% |
| adds code | 32.3% | 29.1% |
| large (100+ lines) | 57.3% | 58.2% |
| author with under 20 earlier commits / 200 or more | 36.9% / 32.9% | 44.5% / 37.6% |
| hypothesis | verdict |
|---|---|
| SK1 100+ lines against under 20 lines at least 1.3 | **supported by a wide margin**: 3.94 (kernel), 4.28 (DPDK) |
| SK2 adds code against small surgical shapes at least 1.2 | **supported**: 2.33, 2.19 (but see SK4: shape rides on size) |
| SK3 author with under 20 earlier commits against 200 or more at least 1.2 | **not supported, direction agrees**: 1.12 (kernel), 1.18 (DPDK); the effect is small and monotone with tenure |
| SK4 shape and tenure effects move a third toward 1 once size is in the model | **supported in substance, poorly measured**: the shape effects disappear or flip (adds code 0.87 to 1.43, small shapes 0.27 to 1.65 in the kernel) because the reference group (mostly 100+ line changes) differs by size; the share-removed percentages printed (365%, 138% and so on) are not interpretable; tenure effect 1.10 and 1.02 after adjustment |
| SK5 direction agrees in both repositories | **supported** for SK1 to SK3 |
**Reading.** What becomes "sick" is, above all, **a big change**: the share with repeated repairs rises from 14% (under 20 lines) to 77% (500 or more) in both repositories, with a mean of 4 to 5 fixes per change at that size; the number of functions changed behaves the same way. Shape and author experience add little once size is accounted for (a mild effect for authors new to the repository). So the picture is the plain one: **big changes have more places to be wrong and are therefore repaired repeatedly**; nothing here shows a special kind of change that is intrinsically sick. **Selection caveat as registered:** only changes that were fixed at least once are in these data, so this cannot say how likely a big change is to be fixed at all, only that when it is, it is repaired repeatedly. The floor of one fix per cause makes the growth of fixes with size look sublinear.
**Consequence for the repair radius.** Size drives three things at once: the number of repairs, their dispersion (large causes: more cross-file, slower) and the baseline's growth, which compresses the ratio. Any statement about the radius needs a size-matched comparison, and a churn- and age-matched baseline (the same-file baseline does not control for how recently or how often a function changed, and call-graph neighbours of a changed function are plausibly hotter than same-file strangers).

## Controls for the repair radius: churn- and age-matched baseline, size bands (hypotheses fixed 2026-11-18 before running; `tools/sensor/radius_controls.py`)
**Churn/age-matched baseline.** For each fixed function outside the changed set the baseline is the same-file functions of similar size (decile plus or minus 1) outside the changed set **and in the same history stratum as the fixed function**: stratum = changes to that function in the 365 days before the causing commit (0, 1, 2 to 3, 4 or more; commits touching more than 40 functions left out as sweeps) crossed with whether its first such change falls within the 365 days before the causing commit (young) or not (older, or no earlier change). Where no matching candidate exists the plain same-file baseline is used for that function (the share is reported). Exact expectations as before. **Size bands.** The existing radius within bands of the causing change's lines (under 20, 20 to 99, 100 to 499, 500 or more). Repositories: DPDK (6,963 pairs) and OpenSSL (124, indicative only); the kernel needs a full-history function index.
- **CH1.** The radius within 2 calls against the churn- and age-matched baseline is at least 1.25 on DPDK, lower bound above 1.15.
- **CH2.** The matched baseline lowers the ratio by at least 10% relative to the plain same-file baseline (1.45 on DPDK): fixes land partly in hot code, which the plain baseline does not account for. *If the matched ratio is about equal to the plain one, hot code is not the explanation.*
- **CH3.** Size bands: the within-2-calls ratio has a lower bound above 1.2 in at least 3 of 4 size bands on DPDK.
**Would surprise (repair radius is mostly "fixes land in hot code"):** the matched ratio at or below 1.1.

#### Controls for the repair radius: results (2026-11-18; `radius_controls_dpdk_output.txt`, `radius_controls_openssl_output.txt`, `radius_by_size_output.txt`)
**Churn- and age-matched baseline (DPDK 6,963 pairs; OpenSSL 126).** Within 2 calls: plain 1.45 [1.41, 1.49], **matched 1.44 [1.41, 1.48]**; within 1 call 1.68 against 1.67; callers 1.84 against 1.84; OpenSSL 1.56 against 1.54. The matched baseline fell back to the plain one for 5.7% (DPDK) and 6.2% (OpenSSL) of fixed functions. **CH1 supported** (1.44, lower bound 1.41); **CH2 not supported** (matched / plain = 1.00 and 0.99; I expected 0.90 or lower: matching changes nothing). **The premise behind CH2 was wrong**: fixed functions are *not* hotter than their same-file candidates: changed in the prior year 19.8% against 24.6% (DPDK) and 12.1% against 22.9% (OpenSSL); first change within the prior year 11.0% against 15.2% and 5.5% against 13.7%. Fixes land slightly in *quieter* code than the same-file average. **Correction of the co-change caveat above:** the untested "fixes land in young functions" explanation for the reversed co-change result (0.76 DPDK, 0.36 OpenSSL) is not supported either: the fixed functions are not younger than their candidates. The reversal stands unexplained: fixed functions are less often earlier co-change partners and less often recently changed than same-file functions of similar size, which is an unexpected finding in its own right and not a bias I can name.
**Size bands (plain baseline; the radius within 2 calls).**
| causing change (lines) | kernel (14,444) | DPDK (6,963) | OpenSSL (126) |
|---|---|---|---|
| under 20 | **2.79** [2.62, 2.97], same function 42% | **2.07** [1.80, 2.45], 51% | n 4 |
| 20 to 99 | 2.57 [2.48, 2.65], 33% | 2.10 [1.96, 2.25], 37% | 1.88 [1.22, 3.29] (n 22) |
| 100 to 499 | 1.73 [1.68, 1.78], 25% | 1.44 [1.40, 1.49], 27% | 1.50 [1.06, 2.19] |
| 500 or more | **1.31** [1.25, 1.38], 17% | **1.18** [1.13, 1.22], 17% | 1.54 [1.26, 1.96] |
| share of causes 100+ lines | 49% | 76% | 78% |
**CH3 supported**: lower bound above 1.2 in 3 of 4 bands (DPDK; the 500+ band is 1.13 to 1.22). **The repair radius shrinks steadily with the size of the causing change** (kernel 2.79 to 1.31, DPDK 2.07 to 1.18), and **DPDK's lower pooled radius (1.45 against the kernel's 1.99) is composition**: 76% of its causes are 100+ lines against about 49% in the kernel; band by band the two repositories are close (20 to 99 lines: 2.57 and 2.10; 100 to 499: 1.73 and 1.44). The same-function share also falls with size (kernel 42% to 17%, DPDK 51% to 17%).
**Caveat on the size trend.** The baseline rises with the size of the change (expected share within 2 calls: 15%, 20%, 33%, 37% in the kernel), because a large changed set has a large neighbourhood, so part of the ratio's fall is arithmetic; the observed share is nearly flat from 20 lines up (53%, 56%, 49% in the kernel), so the absolute excess falls from 38 points (20 to 99 lines) to 12 points (500 or more) but a ratio below 1.5 for large changes should be read as "large changes spread repairs over so many places that proximity says little".
**Reading.** The repair radius survives the controls tried so far: not co-change history, not hot or young code, present at every size, strongest for small, surgical causes (2 to 2.8 times; 33 to 51% of their repairs in the same function) and weakest for rewrites of 500 or more lines (1.2 to 1.3). The size dependence is itself a finding and the right frame for the next step: a **small change has a repair radius of about 2 to 3; a large change has a repair cloud**.
**Not yet controlled.** Kernel-scale churn/age matching and co-change (full function history of 1.3 million commits); authors (same-author control passed earlier in the kernel); calls resolved only statically (callbacks missing); function-name extraction from hunk headers (a third of kernel pairs unmeasured).

## Structure of the repairs by where they land (tree-sitter; hypotheses fixed 2026-11-18 before running; `tools/sensor/repair_structure.py`)
**Data.** Pairs whose causing change is under 100 lines (where the repair radius is real: 2.1 to 2.8 times), kernel and DPDK. For each function the fix commit changed: its **relation to the cause** (from the call graph at the nearest snapshot): *same* function, *caller* of a changed function (calls it directly), *callee* (called directly by one), *two calls away*, *same file, farther*, *elsewhere*. Its **edit**: the function's old and new text (fix commit against its first parent) parsed with tree-sitter C; the statements are compared as a multiset (if, loop, return, goto, call, declaration), and the edit is named by rules on the parse: adds a guard (an `if` whose branch returns, jumps, breaks or continues), adds locking, adds cleanup (free/put/release/unlock), changes a condition, changes a call's arguments, replaces a callee, changes a declared type, changes a return, adds statements only, removes statements only, rewrites, no statement change (comments, macros, whitespace). Flags: the edit mentions a changed function by name; an added `if` tests a changed function's name. Primary label by that precedence; shares among edits that parse (functions not found or files missing are counted separately).
- **ST1 (call-site adaptation).** Among repairs in a *caller* of a changed function, at least 40% have an added or removed statement that calls a changed function; among *callee* repairs at most 15%.
- **ST2 (body-internal in callees).** The share of "adds a guard" or "changes a condition" among *callee* repairs is at least 1.3 times that among *caller* repairs.
- **ST3 (where predicts what).** The edit-type distribution differs by relation (same, caller, callee, two calls away, same file farther): Cramer's V at least 0.10 in both repositories.
- **ST4 (coverage).** At least 85% of the edits that parse receive a named type (not "rewrites" or "no statement change").
- **ST5 (return handling in callers).** The flag "an added `if` tests a changed function" is at least 1.5 times as frequent among *caller* repairs as among *same-function* repairs.
**Would surprise:** ST3 below 0.05: the edit type would then be unrelated to where the repair lands, and the radius would describe location only.

#### Structure of the repairs by where they land: results (2026-11-18; `repair_structure_dpdk_output.txt`, `repair_structure_linux_output.txt`; tree-sitter C, old and new text of each fixed function)
Causes under 100 lines. DPDK: 3,058 pairs, 6,414 (pair, fixed function) records, 99% parsed (50 functions not found). Kernel: 26,130 records, 98% parsed. Relation to the cause: same function 43% (DPDK) and 45% (kernel); caller 5% and 5%; callee 10% and 10%; two calls away 3% and 4%; same file, farther 18% and 17%; elsewhere 21% and 19%.
| edit type | all (DPDK / kernel) | same | caller | callee |
|---|---|---|---|---|
| adds a guard | 20.5 / 19.9% | 17.7 / 20.8% | 18.7 / 22.8% | 19.1 / 22.7% |
| changes a call's arguments | 11.3 / 10.0% | 11.8 / 10.2% | **20.8 / 18.0%** | 12.2 / 8.7% |
| adds statements only | 13.2 / 11.3% | 10.8 / 9.4% | 17.2 / 13.2% | 13.1 / 10.5% |
| no statement change | 12.9 / 16.7% | 11.9 / 13.4% | 7.5 / 7.7% | 15.6 / **20.0%** |
| rewrites | 11.3 / 8.0% | 14.3 / 9.8% | 6.6 / 5.8% | 9.1 / 6.7% |
| changes a condition | 7.6 / 6.2% | 10.2 / 7.8% | 5.1 / 4.9% | 7.5 / 5.7% |
| adds cleanup / locking | 3.7 / 6.0%; 1.4 / 6.8% | | | |
| hypothesis | DPDK | kernel | verdict |
|---|---|---|---|
| ST1 caller repairs that call a changed function at least 40%; callee repairs at most 15% | 32% / 1% | 34% / 2% | **half**: callees as predicted (1 to 2%); callers 32 to 34%, short of 40% |
| ST2 guard-or-condition share, callees over callers at least 1.3 | 1.12 | 1.03 | **not supported** |
| ST3 Cramer's V of edit type by relation at least 0.10 | 0.100 | 0.087 | **borderline: the effect is small** (met at the threshold in DPDK, missed in the kernel) |
| ST4 named type for at least 85% of parsed edits | 76% | 75% | **not supported** (the unnamed quarter is "no statement change" 13 to 17% and "rewrites" 8 to 11%) |
| ST5 an added `if` tests a changed function, callers over same-function at least 1.5 | 4.8% vs 0.6% (**8.7**) | 4.6% vs 0.5% (**8.7**) | **supported by a wide margin, identical in both** |
**What the data say.** (1) **The strongest structural difference is call-site adaptation:** repairs in a caller of a changed function change call arguments about twice as often (21% and 18%, against 10 to 12% for same-function repairs), a third of them edit a statement that calls the changed function, and about 9 times as often as same-function repairs add an `if` that tests the changed function (checking what it returns); callee repairs almost never touch calls to the changed function (1 to 2%). (2) **Otherwise the kind of edit is nearly the same wherever the repair lands**: guards are the most common edit everywhere (17 to 25%) and the type distribution depends only weakly on the relation (V 0.09 to 0.10). The radius describes where repairs land much more than what they do, except at callers. (3) Callee repairs have the most "no statement change" edits (kernel 20.0%).
**What "no statement change" contains (7 DPDK samples read by hand).** Mostly not "nothing": signature or storage-class changes (`int` to `static int`, new parameter), comment-only edits, preprocessor edits, statements moved between blocks (same text, different nesting: a real edit my multiset comparison cannot see), and hunk-header attribution to the neighbouring function when a new function is added after it. The label is a heterogeneous bucket; splitting it (signature, comment, preprocessor, moved statements, wrong attribution) would lift ST4 above 85%; not done.
**Caveats.** Statement-level multiset comparison (no tree alignment: moves and re-nesting are invisible); the guard and cleanup rules rest on name patterns (lock, free, put, release); the relation uses statically resolved calls and "caller" excludes functions that also appear as callees; only causes under 100 lines; fixed functions identified from hunk headers (some attribution errors as above); associations.

## Splitting the "no statement change" bucket (hypotheses fixed 2026-11-18 before running; `tools/sensor/repair_structure.py`, labels extended)
The bucket (13% DPDK, 17% kernel of parsed edits) is split, in this order, by what differs between the old and the new function: **identical function** (the text did not change: the hunk header named the neighbouring function; an attribution error, not an edit); **signature or storage class** (the text before the body differs); **comments or whitespace only** (identical once comments and whitespace are dropped); **preprocessor** (the `#if`, `#define`, `#include` lines inside the function differ); **moves or re-nests statements** (same statements, different order or depth); **other**. Nothing else in the classification changes.
- **SP1.** At least 75% of the bucket falls in a named piece (not "other") in both repositories.
- **SP2.** "Identical function" (attribution error) is at most 10% of the parsed edits.
- **SP3.** Signature changes and moves are the two largest pieces of the bucket in both repositories.
- **SP4.** The excess of "no statement change" among callee repairs (kernel 20.0% against 13.4% for same-function repairs) belongs mostly to signature or preprocessor changes, not to moves.
- **ST4 re-scored (post hoc, labelled as such):** with the named pieces counted as typed, at least 85% of the parsed edits are typed, excluding "rewrites" and "other".

#### Splitting the "no statement change" bucket: results (2026-11-18; `repair_structure_dpdk_output.txt`, `repair_structure_linux_output.txt`, `repair_structure_excl_identical_output.txt`)
The bucket (DPDK 818 edits, 12.9% of parsed; kernel 4,287, 16.7%):
| piece | DPDK (share of bucket / of parsed) | kernel |
|---|---|---|
| **identical function (attribution)** | **64.3% / 8.3%** | **75.1% / 12.5%** |
| moves or re-nests statements | 10.5% / 1.4% | 9.9% / 1.7% |
| comments or whitespace only | 7.1% / 0.9% | 4.1% / 0.7% |
| changes preprocessor lines | 6.1% / 0.8% | 1.4% / 0.2% |
| changes signature or storage class | 4.5% / 0.6% | 4.2% / 0.7% |
| other | 7.5% / 1.0% | 5.4% / 0.9% |
| hypothesis | DPDK | kernel |
|---|---|---|
| SP1 at least 75% of the bucket in a named piece | 93%: supported | 95%: supported |
| SP2 identical function at most 10% of parsed edits | 8.3%: supported | **12.5%: not supported** |
| SP3 signature and moves are the two largest pieces | not supported (identical function is largest; moves second, then comments) | same |
| SP4 the callee excess is signature or preprocessor, not moves | **not supported in a different way**: 70% (DPDK) and 87% (kernel) of the callee bucket is identical functions, not signature, preprocessor or moves |
**The finding: 8% (DPDK) and 12.5% (kernel) of the "fixed functions" were not edited at all.** The hunk-header context names the function before the changed lines, so edits to file-level text after a function (an initialiser table, a struct, a macro, a comment) are attributed to the function above them. By relation the share of records that are identical functions: DPDK same 6.4%, caller 3.3%, callee 10.9%, two calls away 11.8%, same file farther 13.0%, elsewhere 7.4%; kernel same 7.9%, caller 4.6%, **callee 17.3%**, two calls away 14.9%, **same file farther 19.9%**, elsewhere 16.5%. The phantoms are concentrated among repairs that are not in the same function (up to one in five), so the measured repair radius and the structure tables both mix real edits with misattributions.
**ST4, scored on real edits (identical functions removed from the denominator):** 86.6% (DPDK) and 89.8% (kernel) of edits get a named type, **supported**. The other scores barely move: ST1 callers 33% / 35%, callees 1% / 2%; ST2 1.21 / 1.19 (still short of 1.3); ST3 Cramer's V 0.113 / 0.093; ST5 8.5 / 8.4. The caller finding stands: changes a call's arguments 21.5% (DPDK) and 18.8% (kernel) among callers against 12.6% and 11.1% for same-function repairs.
**Consequence.** (1) The structure tables need the identical-function records removed; with them removed the bucket largely disappears and the conclusions are unchanged. (2) **Every radius figure so far counts these phantoms as fixed functions** (and probably also as changed functions on the cause side). Their direction of bias is not obvious: a phantom sits in the file of the real edit, so far phantoms dilute the radius and near ones inflate it. The radius must be re-measured with only verified functions (functions whose text really changed, on both the cause and the fix side).

## Re-measuring the repair radius with verified functions (hypotheses fixed 2026-11-18 before running; `tools/sensor/verify_functions.py`)
A hunk-header function counts as **verified** only if its text differs between the commit's first parent and the commit (tree-sitter C, both versions parsed, function found in both). Applied to the changed set of the cause and the fixed set of the fix, for every pair of the kernel (`links_linux_all.json`) and DPDK; then `blast_radius.py` is re-run with the verified sets (pairs whose verified changed set or fixed set is empty drop out, and are counted). Compared with the unverified figures on the same pairs (kernel 14,444 and DPDK 6,963 with a fixed function outside the changed set; within 2 calls 1.99 and 1.45; by size band kernel 2.79, 2.57, 1.73, 1.31 and DPDK 2.07, 2.10, 1.44, 1.18).
- **VR1 (robust).** The radius within 2 calls on verified functions is within 10% (relative) of the unverified figure in both repositories.
- **VR2 (same function rises).** The same-function share of pairs rises by at least 2 points in both (phantom fixed functions that were counted as "elsewhere" are gone, and phantoms in the changed set no longer make true same-function matches look like misses).
- **VR3 (size trend survives).** The ratio of the radius for causes under 20 lines to that for causes of 500 or more lines is at least 1.5 in both.
- **VR4 (selection).** At most 20% of the measured pairs are lost because a verified set is empty.
- **VR5 (caller direction survives).** For fixes in a different file, the callers1 ratio exceeds the callees1 ratio in both (DPDK 2.43 against 1.24 before).
**Would surprise:** the radius within 2 calls moving by more than 25% in either repository: the headline would then have been substantially an artefact of misattribution.

#### Re-measuring the repair radius with verified functions: results (2026-11-18; `verify_dpdk_output.txt`, `verify_linux_output.txt`, `verified_compare_output.txt`)
**What verification removed.** Function entries (hunk-header functions of every cause and fix commit): kernel 76.5% verified as edited, **13.0% identical (not edited)**, 10.4% present in one version only (kept), 0.1% unverifiable (renamed or added file, kept); DPDK 76.0%, **13.2%**, 10.5%, 0.3%. Pairs measured: kernel 24,474 -> 22,723 (7.2% lost); DPDK 9,867 -> 8,954 (9.3% lost).
| | kernel unverified -> verified | DPDK |
|---|---|---|
| radius within 1 call | 2.44 -> **2.67** [2.59, 2.74] | 1.68 -> **1.88** [1.81, 1.94] |
| radius within 2 calls | 1.99 -> **2.15** [2.10, 2.19] | 1.45 -> **1.57** [1.53, 1.62] |
| same-function share | 58.5% -> 59.0% | 48.6% -> 49.8% |
| under 20 lines | 2.79 -> 3.06 | 2.07 -> 2.09 |
| 20 to 99 | 2.57 -> 2.79 | 2.10 -> 2.39 |
| 100 to 499 | 1.73 -> 1.91 | 1.44 -> 1.60 |
| 500 or more | 1.31 -> 1.31 | 1.18 -> 1.23 |
| different-file fixes: callers1 / callees1 | 3.52 / 2.10 -> **4.43 / 2.74** (n 3,689) | 2.43 / 1.24 -> **2.87 / 1.50** (n 1,816) |
| hypothesis | verdict |
|---|---|
| VR1 radius within 2 calls within 10% of the unverified figure | **supported**: +7.7% (kernel), +8.6% (DPDK); both *rise* |
| VR2 same-function share rises by at least 2 points | **not supported**: +0.5 and +1.2 points |
| VR3 size trend survives (under 20 lines over 500 or more at least 1.5) | **supported**: 2.34 (kernel), 1.69 (DPDK) |
| VR4 at most 20% of pairs lost | **supported**: 7.2% and 9.3% |
| VR5 callers above callees for different-file fixes | **supported**, and stronger in both |
Surprise bar (a move above 25%): not met (worst 8.6%).
**Reading.** The headline survives. Removing functions that were never edited *raises* the radius by about 8% in both repositories (phantom fixed functions sat mostly far from the changed set, so they diluted it), and strengthens the caller direction for fixes in another file (callers 4.43 against 2.74 in the kernel, 2.87 against 1.50 in DPDK). The size trend (small causes tight, large causes diffuse) is intact, now about 3.1 down to 1.3 in the kernel and 2.1 to 1.2 in DPDK. The same-function share hardly moves (phantoms in the changed set seldom stood between a cause and its fix). From here the verified measurements (`blast/<repo>_v`) supersede the unverified ones; the controls above (co-change, churn and age, shape tables, relaxation, sick changes) were run on unverified sets and are expected to hold, but have not been re-run.
**Open ends.** 10.4% of function entries are present in one version only (a function added, removed or renamed by the commit, or one the parser could not find: macro-wrapped definitions); they are kept and not examined. A correction to a caveat above: the chain counts in the relaxation test and the "sick" analysis came from all 152,957 kernel pairs with C files in both commits (`links_linux_all.json`), not only the core subsystems, so the kernel chain counts are complete, not partial.

## Controls re-run on verified functions, and the small repositories with the better methods (hypotheses fixed 2026-11-18 before running)
**Part 1: re-run on verified sets** (`blast/<repo>_v`; history for co-change and churn built from all commits' hunk-header functions as before, the pair commits' functions verified; kernel only where the scripts do not need a full-history index): shape tables and directional checks (`shape_replication.py`), relaxation (`relaxation.py`), sick changes (`sick_changes.py`), churn and age matching (`radius_controls.py`) and co-change (`cochange_control.py`) on DPDK and OpenSSL. **Part 2: curl (755 pairs from message links), OpenSSL (261) and FreeBSD (192)** through `verify_functions.py` and `blast_radius.py`, pooled with and without verification.
- **RR1 (verdicts hold).** Of the verdicts recorded for these controls (CC1 to CC3, CH1 to CH3, RX1 to RX4, SK1 to SK5, RS1 to RS5 per repository), at most 3 change between supported and not supported in the re-run.
- **RR2 (the null results stay null).** The co-change ratio (a) stays below 1 on DPDK; the matched baseline stays within 5% of the plain baseline; the chance of another repair keeps rising with each repair (RX3).
- **SR1 (small repositories, verified).** The pooled radius within 2 calls of curl, OpenSSL and FreeBSD is at least 1.3 with a lower bound above 1.1.
- **SR2.** Verification raises the pooled radius, as it did on DPDK and the kernel (+8%).
- **SR3.** Callers above callees for fixes in a different file (pooled; the kernel 4.43 against 2.74).
- **SR4.** Size trend: pooled radius for causes under 100 lines is at least 1.2 times that for causes of 100 or more lines.
- **SR5.** The three repositories agree in direction on SR1 to SR3 (each point estimate above 1.0 within 2 calls; callers above callees).
**Would surprise:** a pooled small-repository radius below 1.1: the pattern would then be a property of large, trailer-rich repositories.

#### Controls re-run on verified functions and small repositories: results (2026-11-18; `*_verified_output.txt`, `small_repos_pooled_output.txt`, `verify_{openssl,freebsd,curl}_output.txt`)
**Part 1: the controls on verified sets (kernel and DPDK, OpenSSL where possible).**
| control | unverified | verified |
|---|---|---|
| co-change (a) fixed function in the co-change set (DPDK) | 0.76 | **0.83** [0.78, 0.87]; OpenSSL 0.36 -> 0.38 |
| co-change (b) within 2 calls and not a co-change partner | 1.60 | **1.71** [1.66, 1.77]; OpenSSL 1.91 -> 1.96 |
| both signals, share of the within-2-calls hits | 17% | 15% |
| churn- and age-matched baseline, DPDK | 1.44 against plain 1.45 | **1.55 against plain 1.57** (matched / plain 0.98); fixed functions changed in the prior year 20.1% against 23.3% of candidates |
| relaxation RX1 fast/slow within 1 call | 1.11 / 1.06 | 1.12 / 1.08 (both short of 1.15) |
| RX2 later fix within 2 calls | -1.0 / -4.2 points | -1.5 [-3.7, +0.8] / -4.0 [-7.1, -1.1] |
| RX3 chance of another repair, k = 1 to 5 | 0.29 to 0.66; 0.39 to 0.70 | identical (chain counts do not depend on function sets) |
| RX4 gaps | kernel not, DPDK supported | unchanged |
| sick changes SK1 / SK2 / SK3 (kernel; DPDK) | 3.94 / 2.33 / 1.12; 4.28 / 2.19 / 1.18 | 3.92 / 2.40 / 1.12; 4.47 / 2.42 / **1.20** |
| shape checks RS1 to RS5 on DPDK | 3 of 5 agree (RS3 differs) | **4 of 5 agree**: RS3 now agrees (large fixes have the lowest radius, 1.33) |
| per repository (DPDK, OpenSSL, FreeBSD) | 5 of 11 testable checks agree | **6 of 11** |
**RR1 supported, at its limit:** three verdicts changed, all on DPDK and all marginal or derived: RS3 (differs -> agrees), DR4 (3 of 5 -> 4 of 5, the same change seen through the bar of the DPDK hypotheses), SK3 (1.18 -> 1.20, a bar of 1.2). **RR2 supported:** the co-change ratio (a) stays below 1 (0.83), matching changes the DPDK radius by 2%, the chance of another repair keeps rising. The DPDK shape picture is now closer to the kernel's: guard fixes still not slow there (RS1 differs), but large fixes have the lowest radius, large causes have the lowest same-function share and the longest lag, and the same kind of edit recurs (sync to sync 9.9, call to call 3.6).
**Part 2: curl, OpenSSL and FreeBSD.** Function entries identified as not edited: curl 10.8%, OpenSSL 3.7% (but 23.4% present in one version only, kept), FreeBSD 13.1% (19.9% in one version only).
| radius within 2 calls | unverified | verified |
|---|---|---|
| curl | 1.57 [1.33, 1.85] (n 171) | **1.65** [1.41, 2.00] (n 156) |
| OpenSSL | 1.56 [1.33, 1.86] (115) | **1.72** [1.38, 2.20] (105) |
| FreeBSD | 2.35 [1.76, 3.41] (47) | **2.17** [1.62, 3.12] (39) |
| pooled | 1.64 [1.46, 1.82] (333) | **1.74** [1.52, 2.00] (300) |
Same-function share, verified: curl 72%, OpenSSL 43%, FreeBSD 72% (pooled 65%). Different-file fixes (pooled, verified; n 132): callers1 3.21 [1.35, 13.99] against callees1 1.35 [0.57, 2.95] (curl 7.90 against 1.51; OpenSSL 0.52 against 1.21 with 39 pairs; FreeBSD too few). By size (pooled, verified): under 100 lines 1.91 [1.56, 2.40], 100 or more 1.63 [1.39, 1.92].
| hypothesis | verdict |
|---|---|
| SR1 pooled verified radius at least 1.3, lower bound above 1.1 | **supported**: 1.74 [1.52, 2.00] |
| SR2 verification raises the pooled radius | **supported**: +5.6% (curl +5%, OpenSSL +10%, FreeBSD -8%) |
| SR3 callers above callees (different-file fixes, pooled) | **supported**: 3.21 against 1.35 (wide intervals) |
| SR4 under 100 lines over 100 or more at least 1.2 | **not supported**: 1.17, same direction as the kernel and DPDK, smaller than they show |
| SR5 all three agree on radius above 1 and callers above callees | **not supported**: curl only (OpenSSL's callers-versus-callees contrast goes the other way on 39 pairs; FreeBSD too few) |
Surprise bar (pooled radius below 1.1): not met.
**Reading.** The repair radius is present in all five repositories on verified functions: kernel 2.15, FreeBSD 2.17, OpenSSL 1.72, curl 1.65, DPDK 1.57, with intervals that exclude 1.3 for the kernel, DPDK, curl and OpenSSL (FreeBSD's lower bound is 1.62 on 39 pairs). The caller direction is solid in curl, the kernel and DPDK; the small repositories cannot confirm or deny it individually. The size trend replicates in direction only (1.17 against 2.3 in the kernel). The controls give the same answers on verified sets as before: the radius is not co-change, not hot or young code, and not an artefact of the hunk-header misattribution.
**Not done.** Mesa and QEMU (about 9,700 and 4,000 pairs with C/H on both sides); the kernel-scale co-change and churn controls (need a 1.3-million-commit history); the repair structure re-run with verified functions (identical functions were removed from its tables, no further change); the 10 to 23% of function entries present in one version only.

## Mesa replication (hypotheses fixed 2026-11-18 before running)
Third large repository: 13,180 `Fixes:` pairs of which about 9,700 have C/H on both sides; **C only** (`.c` and `.h`; Mesa's C++ and Rust are not read, so C++-heavy parts such as the AMD compiler backend are out of scope and the figures describe Mesa's C). Methods as for the kernel and DPDK: full clone, quarterly scans of `src` and `include` from 2017, `verify_functions.py`, `blast_radius.py` on the verified sets, then radius, controls and structure. Mesa differs: median lag 64 days (kernel 241, DPDK 235) and 30% of fixes in a file the cause did not touch (kernel 11 to 15%).
- **MR1.** Radius within 2 calls on verified functions at least 1.3 with lower bound above 1.2.
- **MR2.** Same-function share of measured pairs between 40% and 75%.
- **MR3.** For fixes in a different file, callers1 above callees1 (kernel 4.43 against 2.74; DPDK 2.87 against 1.50).
- **MR4.** Size trend: radius for causes under 100 lines at least 1.3 times that for 100 lines or more.
- **MR5.** Shape checks RS1 to RS5: at least 4 of 5 agree with the kernel's direction.
- **MR6.** Co-change control: (b) within 2 calls and not a co-change partner at least 1.3; (a) the co-change ratio below 1.
- **MR7.** Chance of another repair rises with each repair so far (k = 1 to 4) and size drives it (P(2+ fixes) for 100+ line causes at least 1.3 times that for under 20 lines).
- **MR8.** Faster repairs are no tighter: the radius for fixes under 30 days is less than 1.15 times that for fixes over a year (as in the kernel and DPDK); *with Mesa's short lags I give this one a coin flip.*
- **MR9.** Call-site adaptation: among caller repairs, "changes a call's arguments" at least 1.3 times as often as among same-function repairs; an added `if` testing a changed function at least 3 times as often.
**Would surprise:** radius below 1.2: the pattern would then be specific to repositories with long repair lags.

#### Mesa replication: results (2026-11-18; `*_mesa_output.txt`, `verified_compare_mesa_output.txt`, `verify_*`; C only, `src` and `include`, 41 quarterly scans in 27 minutes)
9,526 usable pairs; verification found 11.4% of function entries not edited (kernel 13.0%, DPDK 13.2%); 7,410 measured unverified, **7,021 verified** (5.2% lost), 3,799 with a fixed function outside the changed set.
| | Mesa (verified) | kernel | DPDK |
|---|---|---|---|
| radius within 2 calls | **1.78** [1.71, 1.85] (unverified 1.68) | 2.15 | 1.57 |
| same-function share | 57.2% | 59.0% | 49.8% |
| size bands: under 20 / 20 to 99 / 100 to 499 / 500+ | 2.16 / 2.02 / 1.70 / 1.34 | 3.06 / 2.79 / 1.91 / 1.31 | 2.09 / 2.39 / 1.60 / 1.23 |
| different-file fixes (1,482): callers1 / callees1 | **4.37** [3.33, 5.93] / 2.28 [1.91, 2.75] | 4.43 / 2.74 | 2.87 / 1.50 |
| co-change (a) fixed function in the co-change set | **1.04** [1.00, 1.09] | 0.83 (DPDK) | |
| co-change (b) within 2 calls, not a co-change partner | **2.18** [2.08, 2.31] | | 1.71 |
| churn- and age-matched radius | 1.74 against plain 1.78 | | 1.55 against 1.57 |
| radius by lag: under 30 d / 30 to 365 d / 1 to 2 y / over 2 y | **1.97 / 1.72 / 1.69 / 1.55** | 2.13 to 1.93 | 1.48 to 1.39 |
| chance of another repair, k = 1 to 5 | 0.19, 0.34, 0.41, 0.58, 0.57 | 0.29 to 0.66 | 0.39 to 0.70 |
| P(2+ fixes): under 20 lines / 500 or more | 10.5% / 49.1% (3.22 times for 100+) | 14.5% / 77.8% | 13.6% / 77.2% |
| repairs in callers: change a call's arguments (against same-function) | 27.2% (16.8%) | 18.8% (11.1%) | 21.5% (12.6%) |
| repairs in callers: an added `if` tests a changed function (against same function) | 5.0% (0.3%) = 14.4 times | 8.4 | 8.5 |
| hypothesis | verdict |
|---|---|
| MR1 radius at least 1.3, lower bound above 1.2 | **supported**: 1.78 [1.71, 1.85] |
| MR2 same-function share 40 to 75% | **supported**: 57% |
| MR3 callers above callees, different-file fixes | **supported**: 4.37 against 2.28 |
| MR4 radius under 100 lines at least 1.3 times that of 100 or more | **not supported, narrowly**: 2.05 against 1.59, ratio 1.29 |
| MR5 at least 4 of 5 shape checks agree | **supported**: 4 of 5 (guard fixes again not slow: 55 d against 64 d; RS5 sync to sync 15.7, n 7; call to call 2.6) |
| MR6 (b) at least 1.3 and (a) below 1 | **half**: (b) 2.18 supported; (a) 1.04 [1.00, 1.09], **not below 1** (the reversal seen in DPDK and OpenSSL does not appear in Mesa) |
| MR7 chance of another repair rises; size drives it | **supported**: rises 0.19 to 0.58, SK1 3.22 (SK3 tenure 0.97, no effect; SK2 adds code 1.75) |
| MR8 fast repairs not tighter (fast/slow under 1.15) | **failed**: 1.30 (2.45 within 1 call under 30 days against 1.89 over a year); in Mesa the radius does fade with lag (1.97 to 1.55) |
| MR9 caller repairs: call arguments at least 1.3 times; added `if` at least 3 times | **supported**: 1.62 times and 14.4 times |
Surprise bar (radius below 1.2): not met. The structure table (6,530 parsed edits, 99%; identical-function records 0 after verification; coverage 88% typed): relation same 49%, caller 5%, callee 8%, two calls away 3%, same file farther 10%, elsewhere 25%; Cramer's V of edit type by relation 0.128 (ST3 supported); ST1 callers 37% (short of 40%), callees 2%; ST2 callees over callers 1.41 (guards 20.9% in callee repairs against 9.6% in caller repairs); ST4 88%.
**Reading.** Mesa, a third independent large repository (and a different domain, graphics drivers rather than operating systems or networking), reproduces the main findings on verified C functions: a repair radius of about 1.8 that survives churn matching and strengthens when co-change partners are removed, the caller direction (4.4 against 2.3), size as the driver of repeated repairs, rising chance of another repair, and call-site adaptation (callers: arguments changed 1.6 times as often, an added `if` testing the changed function 14 times as often). Where Mesa differs it points the same way as one of the other repositories: the radius fades with lag (as in the kernel's small fade, but clearer: 1.97 to 1.55), co-change partners are not under-represented (the DPDK and OpenSSL reversal is not a general law), and the size trend is slightly weaker than the kernel's.
**Across the five repositories with verified radii:** kernel 2.15, FreeBSD 2.17 (n 39), OpenSSL 1.72, Mesa 1.78, curl 1.65, DPDK 1.57; the small-repository pooled figure 1.74.
**Caveats.** C only: Mesa's C++ and Rust files (a large part of its newer compiler code) are outside the measurement; 30% of Mesa's trailer pairs lacked C on both sides; hunk-header attribution and static resolution as before; the lag distribution (median 64 days) is much shorter than the kernel's, so "later" repairs here are within months.

## What is changing? Identifiers shared between the cause and its repairs (hypotheses fixed 2026-11-18 before running; `tools/sensor/what_changes.py`)
**Idea.** The edit types name how a repair changes code, not *what* it changes. A concrete, measurable "what" is the identifiers: the repair's added and removed statements (and calls) against the identifiers on the added and removed lines of the cause. Each shared identifier is classed by its use: **callee** (followed by `(`), **field** (after `->` or `.`), **macro or constant** (all capitals), **type** (after `struct`, `enum`, `union`), **variable or parameter** (other). Identifiers present in more than 1% of the pairs' diffs of a repository (the repository's stock vocabulary: `ret`, `i`, `NULL`, `len`, ...), C keywords and common type words are removed. Baseline: the same repair against the cause of a **different pair of the same repository and size band of the cause** (20 random draws per repair): how often two unrelated changes share an identifier. Data: verified sets, causes under 100 lines, kernel, DPDK, Mesa, OpenSSL (the small repositories pooled with OpenSSL only where counts allow). Records are (pair, fixed function) as in the repair-structure analysis.
- **WC1.** The share of repairs with at least one shared identifier is at least 2 times the shuffled baseline in every relation to the cause (same function, caller, callee, two calls away, same file farther, elsewhere) in the pooled data, including "elsewhere" (the repairs the call graph cannot reach).
- **WC2.** The share falls with distance: same function > caller and callee > same file farther > elsewhere, in at least 3 of the 4 repositories.
- **WC3.** In repairs that are **not** in the same function, the shared identifiers are mostly data (fields, macros, variables, types), not called functions, except in callers (where the called function is the shared name): data share at least 60% outside the callers.
- **WC4.** "Elsewhere" repairs (no call path within 2) that share an identifier share a **field or macro** more often than a callee: at least 50% of their shared identifiers are fields or macros.
- **WC5.** A shared identifier makes the repair more likely to be a repair of the same kind as the cause's: no test of this (listed as not tested).
**Would surprise:** the observed share within 1.3 times the baseline for "elsewhere": the repairs that the call graph cannot reach would then look unrelated to the cause by their content too.

#### What is changing? Results (2026-11-18; `what_changes_output.txt`, `what_changes_examples_output.txt`; kernel, DPDK, Mesa, OpenSSL; verified functions, causes under 100 lines; 33,746 (pair, fixed function) records from 17,031 pairs)
Share of repairs that share at least one specific identifier with the cause's diff (stock vocabulary removed: names in more than 1% of a repository's pairs):
| relation of the repair to the cause | shared identifier | baseline: another pair's cause of the same size band | **area-matched baseline** (another pair's cause whose repair landed in the same directory; post hoc) |
|---|---|---|---|
| same function | 79.7% | 0.9% (ratio 88) | 6.6% (ratio **12.0**) |
| caller | 58.4% | 0.9% (66) | 8.2% (**7.3**) |
| callee | 72.7% | 1.1% (66) | 6.4% (**11.4**) |
| two calls away | 56.8% | 0.8% (67) | 7.7% (**7.5**) |
| same file, farther | 61.4% | 0.9% (70) | 7.2% (**8.6**) |
| **elsewhere (no call path within 2)** | **44.7%** | 0.9% (53) | 6.6% (**6.7**, interval 6.4 to 7.0) |
By class of the shared identifier (share of shared tokens), repairs that are not in the same function: field 25 to 34%, variable or parameter 29 to 38%, callee 20 to 25%, macro or constant 10 to 13%, type 2 to 4%. By repository the ordering of the shares (same function > callers and callees > same file farther > elsewhere) holds in the kernel (80, 68, 63, 48%), DPDK (77, 58, 57, 40%) and Mesa (82, 63, 60, 39%); OpenSSL has too few pairs.
| hypothesis | verdict |
|---|---|
| WC1 share at least 2 times the shuffled baseline in every relation, including "elsewhere" | **supported**: 53 to 88 times; against the harder area-matched baseline 6.7 to 12 times |
| WC2 share falls with distance in at least 3 of 4 repositories | **supported**: 3 of 4 (OpenSSL not testable) |
| WC3 outside same function and callers, shared identifiers mostly data (field, macro, variable, type) | **supported**: 79% (needs 60%) |
| WC4 "elsewhere" shared identifiers at least 50% fields or macros | **not supported, narrowly**: 47% (field 34%, macro 13%; variables 29%, callees 21%) |
| WC5 (not tested) | |
Surprise bar ("elsewhere" within 1.3 times the baseline): not met (53 times; 6.7 times against the area-matched baseline).
**Concrete examples ("elsewhere" repairs: no call path within 2 to the cause, still sharing identifiers).** Mesa: cause "nir: Add a range_base+range to nir_intrinsic_load_ubo()" and repair "vc4: Add missing range_base/range at nir_load_ubos in yuv_blit fs" share the API calls `nir_intrinsic_set_range` and `nir_intrinsic_set_range_base` (another user of a changed interface); cause "nvk: Don't advertise sparse residency on Maxwell A" and repair "nvk: Reject sparse images on Maxwell A and earlier" share `MAXWELL_B` and `cls_eng3d` (the same hardware condition checked in another function); cause "kmsro: Fix renderonly_scanout BO aliasing" and repair "winsys/panfrost: Fix a scanout resource leak" share `bo_map`, `bo_map_lock`, `free_dumb` (the same objects in another file). DPDK: cause "ethdev: add Rx error counters for missed, badcrc and badlen packets" and repair "ethdev: remove missed packets from error counter" in an e1000 driver share the counter fields `imissed`, `crcerrs`, `ierrors`; cause "net/ixgbe: support committing TM hierarchy" and its repair share `tm_conf`, `shaper_profile`, `profile`, `rate`. **The repair is usually the same feature, interface, hardware condition or object appearing in a place the call graph does not connect.**
**Reading.** (1) **What is changing is mostly the same objects the cause touched**: struct fields, variables and parameters, macros and constants, the same API calls. Not a new kind of code. (2) **The call graph misses a large part of the link**: 45% of the repairs with no call path within 2 calls still share a specific identifier with the cause, 6.7 times more often than repairs of unrelated changes in the same directory (the area's vocabulary), so identifiers are a second, independent coupling beside the call graph (data and interface coupling). (3) Sharing falls with distance in the call graph, as the repair radius does, which suggests the two views measure related things. (4) All edit types show it (56 to 84% share an identifier; the share is lowest for "adds statements").
**Caveats.** The area-matched baseline was added after seeing the first numbers (post hoc); identifiers come from added and removed statements of the repair and added and removed lines of the cause (comments and strings dropped), classified by position (callee, field, macro, type, variable) without type information, so variable names are a weak signal; the stock-vocabulary cutoff (1% of pairs) shapes the baseline; named-cause pairs mean the fixer was looking at the cause's code, so some overlap is the fixer's own attention; shared identifier is association, not data flow or proof of mechanism; causes under 100 lines only; OpenSSL has 49 pairs and is only in the pooled figures.
**Next, if taken.** Say what the cause did to the shared identifier: a field or parameter added, a function's signature or meaning changed, a macro redefined, a condition or check changed, a name merely used. Then the question becomes "which kinds of change to an interface or object are followed by repairs elsewhere".

## What did the cause do to the shared identifier? (hypotheses fixed 2026-11-18 before running; `tools/sensor/cause_action.py`)
For each (pair, fixed function, shared identifier) of the previous analysis the cause's own added (+) and removed (-) lines that mention the identifier are read (comments and strings dropped) and put in one class, in this precedence: **defined** (a macro, function or prototype at line start, struct member or enum constant that appears only on added lines); **redefined or signature changed** (a definition on both added and removed lines); **definition removed** (a definition on removed lines only); otherwise a use: **check added, changed or removed** (the identifier on a line with `if`, `while`, `for` or `?`); **new use** (added lines only); **use removed** (removed lines only); **use changed** (both). A definition in a `.h` file is an **interface change**. At the cause level, a cause has an interface change if any line it adds or removes in a header is a definition line (any identifier). Data: causes under 100 lines, verified functions, the kernel, DPDK, Mesa (OpenSSL pooled, too few for its own table).
- **CA1.** Uses dominate: new use, use changed, use removed and checks together are at least 60% of the shared identifiers (pooled), i.e. the cause mostly used or changed the use of an existing name, not defining one.
- **CA2.** Repairs **not in the same function** (callee, two calls away, same file farther, elsewhere) have at least 1.5 times the share of header definitions (defined, redefined or removed in a `.h`) among their shared identifiers than same-function repairs.
- **CA3.** At the cause level: causes with an interface change have at least 1.3 times the share of their repairs in "same file, farther" or "elsewhere" than causes without one (per-pair means).
- **CA4.** The cause's action on the identifier predicts the repair's edit type: for "check added, changed or removed", the repair is "adds a guard" or "changes a condition" at least 1.3 times as often as for the other classes (lift over all tokens).
- **CA5.** "Redefined or signature changed" identifiers are followed by repairs that "change a call's arguments" or "replace a callee" at least 1.5 times as often as the average shared identifier.
**Would surprise:** CA2 and CA3 both failing: the interface (definition) changes would then not be what carries repairs to other places, and the shared names would be ordinary uses.

#### What did the cause do to the shared identifier? Results (2026-11-18; `cause_action_output.txt`; kernel, DPDK, Mesa; 66,329 (pair, fixed function, shared identifier) tokens from 19,938 pairs)
OpenSSL produced no classified tokens (49 pairs; the cause-side diff lines were not matched; its pairs are in the pair-level CA3 row only).
| cause action on the shared identifier | all | same function | caller | callee | two calls away | same file, farther | elsewhere |
|---|---|---|---|---|---|---|---|
| check added, changed or removed | 31.3% | 31.7 | 32.6 | 30.6 | 33.2 | 31.0 | 28.9 |
| new use | 31.1% | 29.5 | 25.9 | **38.2** | 32.6 | 33.7 | 33.3 |
| use changed | 20.2% | 21.7 | 22.4 | 13.6 | 15.7 | 18.7 | 19.4 |
| defined | 11.7% | 11.2 | 11.8 | 13.9 | 11.7 | 11.8 | 12.6 |
| redefined or signature changed | 1.7% | 1.8 | 3.7 | 1.3 | 1.7 | 1.4 | 1.4 |
| use removed | 2.9% | 2.9 | 2.9 | 1.9 | 3.8 | 2.5 | 3.9 |
| definition removed | 0.9% | 1.0 | 0.7 | 0.6 | 1.2 | 1.0 | 0.5 |
| definition in a header (an interface change) | 6.8% | 6.5 | 9.3 | 5.2 | 8.3 | 6.4 | **9.5** |
By the kind of name: types are almost always newly used (57%), variables most often checked (36.6%), callees mostly newly used (44.3%) and least often checked (19.0%), fields and macros resemble each other (checks 35%, new use 28 to 30%). 37% of pairs have a cause with an interface change (kernel 38%, DPDK 37%, Mesa 31%).
| hypothesis | verdict |
|---|---|
| CA1 uses and checks at least 60% of shared identifiers | **supported**: 86% (uses and checks; definitions are 14%) |
| CA2 repairs outside the same function have at least 1.5 times the header-definition share of same-function repairs | **not supported**: 7.0% against 6.5% (1.08); the callers (9.3%) and "elsewhere" (9.5%) are 1.4 to 1.5 times the same-function figure, callees (5.2%) lower: post hoc, not a result |
| CA3 causes with an interface change have at least 1.3 times the share of repairs in "same file, farther" or "elsewhere" | **not supported, narrowly**: 28.9% against 22.9% = 1.26 [1.21, 1.32]; "elsewhere" alone 16.7% against 12.9% = 1.30; in the kernel 28.9 against 22.3, DPDK 27.7 against 20.2, Mesa 29.8 against 26.2 |
| CA4 after a "check" action the repair adds a guard or changes a condition at least 1.3 times as often | **supported, strongly**: 53.0% against 26.5% = **2.00** (adds a guard 34.9% against 23.9% overall; changes a condition 18.2% against 11.0%) |
| CA5 after "redefined or signature changed" the repair changes call arguments or replaces a callee at least 1.5 times as often | **not supported**: 31.6% against 23.6% = 1.34 (n 1,159) |
Surprise bar (CA2 and CA3 both failing): **met**: interface (definition) changes are not what carries repairs to other places in any big way: the shared names are mostly ordinary uses and checks. The cause-level effect exists but is modest (1.26 times).
**Other cross-tabulation (row shares).** After "use changed" the repair most often changes a call's arguments (25.4% against 16.6% overall); after "defined" it is most often adds a guard (22.5%) or changes a call's arguments (15.4%); after "check" adds a guard (34.9%) or changes a condition (18.2%).
**Reading.** (1) **What the cause did to the shared name is mostly ordinary**: it tested the name in a condition (31%), started using it (31%) or changed a use (20%); defining something new is 12% and redefining or removing a definition is 3%. (2) **The repair mirrors the cause's action**: a cause that touched a check on a name is followed, twice as often as otherwise, by a repair that adds or changes a guard or condition on it; a cause that changed a use is followed by a repair that changes arguments 1.5 times as often. The previously found recurrence of edit types (sync after sync, call after call) shows up here at the level of the shared name. (3) **Interface changes are a minor carrier**: 37% of causes change a definition in a header, and their repairs land away from the cause's function and file 1.26 times as often. The main link between a change and its repairs elsewhere is shared objects, checks and uses, not changed interfaces.
**Caveats.** Rule-based classification of lines (regular expressions for definitions, no parser; a definition line of the shape `type name(...)` at column zero counts as a function definition or prototype, a one-name line ending in a comma as an enum constant); an identifier can appear in several actions and gets the first in the precedence (definition first, then check, then use); interface change means a definition line in a `.h` file only; association, not mechanism; the kernel is 64% of the tokens; OpenSSL not classified.

## How good a prediction is the neighbourhood, and is there lift over size? (hypotheses fixed 2026-11-18 before running; `tools/sensor/retrieval_lift.py`)
**Question.** Repowise's "size-confound wall" (memory: repowise-bench) says a pooled AUC of 0.73 for file-level defect prediction falls to 0.52 to 0.59 inside the smaller size quartiles. The equivalent test here: given a change that was later fixed, rank **every function of the program** (the nearest quarterly snapshot's call graph, minus the changed functions) and ask where the **fixed function outside the changed set** lands, with and without size. This is *where the fix goes given that a fix is needed*, not whether a change will need one. Pairs: verified sets, kernel, DPDK, Mesa. Features: size decile of the candidate, same file as a changed function, call distance to the changed set (1, 2, 3 or farther; either direction), number of callers (0, 1 to 2, 3 or more). All rankers are scored exactly from candidate counts per feature cell, ties split evenly. Metrics: per-pair AUC (the chance a fixed function outranks a random other candidate, averaged over fixed functions then pairs), the share of pairs whose best-ranked fixed function is in the top 20 and top 100, and the **within-size AUC** (the fixed function against candidates **of the same size decile**, the repowise form of the test). A logistic model on the same four features is fitted on the earliest 60% of pairs by cause date and scored on the latest 40%.
- **PL1.** Size alone is a weak ranker: mean AUC at most 0.65 in each repository.
- **PL2.** The combined ranker (file, then distance, then size) puts the fixed function in the top 20 at least 3 times as often as size alone, pooled.
- **PL3.** Distance and file together keep a **within-size AUC** of at least 0.65 pooled, and at least 0.60 inside the two smallest size quartiles of fixed functions (repowise: 0.52 and 0.57).
- **PL4.** For fixes in a different file from every changed function (no file feature), distance alone has a within-size AUC of at least 0.60 pooled.
- **PL5.** The fitted four-feature model reaches a test AUC at least 0.15 above size alone, pooled.
**Would surprise:** a within-size AUC at or below 0.55: the neighbourhood would then be a size effect in disguise.

#### How good a prediction is the neighbourhood, and is there lift over size? Results (2026-11-18; `retrieval_lift_output.txt`; kernel 12,733 pairs, DPDK 6,000, Mesa 3,799; verified sets; candidates per pair median 108,000 / 30,000 / 67,000)
Ranking the fixed function (outside the changed set) among every function of the program, pooled: **size alone** AUC 0.737, top 20 **0.2%**, top 100 0.8%; same file 0.794 / 20.9% / 47.6%; call distance alone 0.734 / 30.0% / 48.9%; file then distance 0.851 / 39.9% / 62.0%; **file, distance, then size 0.925 / 45.1% / 65.1%**; caller count 0.524. **Within the same size decile** (the repowise form; size cannot help): file then distance 0.851, call distance alone 0.734, flat across size groups (0.82 to 0.84 for file then distance; 0.71 to 0.72 for distance), where repowise reports 0.52 to 0.57 in its lower quartiles. Fixes in a different file from every changed function (8,299 pairs): distance alone AUC 0.639 (within-size 0.639), top 20 15.2%, top 100 27.2%; size alone AUC 0.748 but top 20 0.2%. Fitted four-feature model (earliest 60% of pairs, scored on the latest 40%, after fixing a convergence problem in the first fit, where the unscaled weights gave a misleading 0.62 for the model without size): test AUC 0.888 against size alone 0.740; **0.848 without size**, so the neighbourhood features alone beat size alone by 0.11.
| hypothesis | verdict |
|---|---|
| PL1 size-alone AUC at most 0.65 | **not supported**: 0.72 to 0.79 (large functions are fixed more often; as a top-k ranker size is nearly useless, 0.2%) |
| PL2 combined top 20 at least 3 times size alone | **supported**: 45.1% against 0.2% |
| PL3 within-size AUC at least 0.65 pooled | **supported**: 0.851 (distance alone 0.734) |
| PL4 different-file fixes, distance alone within-size AUC at least 0.60 | **supported**: 0.639 |
| PL5 fitted model test AUC at least 0.15 above size alone | **not supported, narrowly**: +0.148 |
Surprise bar (within-size AUC at or below 0.55): not met.
**Reading.** Given that a change is later fixed, the neighbourhood (same file, call distance) locates the fixed function far above size: within functions of the same size the AUC is 0.73 (calls only) to 0.85 (file and calls), against the wall repowise reports for file-level defect prediction. It is a different question (where a fix goes given a fix is needed, not whether a change will need one), so it is not a replication of that experiment. Most of the lift comes from the same-file feature; the call graph alone is a weaker, size-independent ranker and the main one for fixes in other files.
**Not done.** A repowise-style test (which changes will need any fix beyond size, with never-fixed changes included); added and deleted functions (hunk-header attribution hides added functions, and the previous snapshot is needed for deleted ones); a version without named causes.

## Will this change need a fix? A repowise-style test with the neighbourhood (hypotheses fixed 2026-11-18 before running; `tools/sensor/needs_fix.py`)
**Question.** Every earlier result is conditional on a fix existing. The prediction question is the reverse: given a change at the moment it is made, can anything beyond its size tell us it will later be named as the cause of a fix? Repowise's claim is that process features beat structural ones and that pooled signal is largely size. This tests that on the population of **all** changes, including the ones never fixed.
**Population and label.** Repositories: **DPDK and Mesa** (the kernel needs an all-commit function index of 1.3 million commits and was not built; OpenSSL has only 261 named causes). Every non-merge commit that touches `.c`/`.h` files, whose changed functions (git hunk-header context, unverified: the verification pass costs a parse per commit) are found in the nearest quarterly snapshot at or after it, with 1 to 60 functions, dated from the first snapshot to **two years before the end of the history**. **Label = 1 if some fix names this commit as its cause within 730 days** (`Fixes:` trailer). Base rate printed. The label is "was named in a trailer", which depends on project habit as well as on bugs: stated as the main weakness.
**Features, all known at the time of the change.** *Size (S):* log lines added plus removed in C/H files, log number of functions, log number of files. *Process (P):* author's earlier commits in the repository (tenure), the largest number of commits in the previous 365 days to any file the commit touches (file churn). *Neighbourhood (N), from the call graph at the nearest snapshot:* callers of the changed functions (sum and maximum), callees (sum), distinct files containing those callers, functions within 2 calls. Models: logistic regression on standardised log features, earliest 60% of each repository's commits for training, latest 40% for testing (AUC; 200 bootstrap resamples of the test set for intervals); a gradient-boosted model as a sensitivity check.
- **WN1.** Size alone has a test AUC of at least 0.65 in both repositories (size predicts being fixed: the earlier "sick changes" result).
- **WN2.** Adding the neighbourhood to size and process raises the test AUC by at least 0.02 in both repositories (S+P+N against S+P).
- **WN3.** Inside the smallest quartile of change size, the S+P+N model keeps a test AUC of at least 0.58 in both repositories (no wall as in repowise's Q1 of 0.525). *A coin flip: I expect the smallest changes to be nearly unpredictable.*
- **WN4.** The best single neighbourhood feature has a within-size-decile AUC of at least 0.55 in both repositories.
- **WN5.** Process alone beats neighbourhood alone (test AUC) in both repositories (repowise's ordering: process before structure).
- **WN6.** Practical lift: the top decile of the S+P+N score contains at least 1.2 times the share of fixed-cause changes as the top decile of the S+P score.
**Would surprise:** every feature group adding less than 0.01 AUC over size alone: then nothing known at change time beyond size predicts the need for a fix, as the earlier per-metric nulls suggested.

#### Will this change need a fix? Results (2026-11-18; `needs_fix_output.txt`; DPDK 25,367 changes, Mesa 71,875; label = named as the cause of a fix within 730 days: 16.7% and 6.2%; train earliest 60%, test latest 40%)
Test AUC (logistic regression), DPDK / Mesa: **size alone 0.767 / 0.718**; process alone 0.558 / 0.569; neighbourhood alone 0.681 / 0.632; size + process 0.770 / 0.721; size + neighbourhood 0.772 / 0.719; **all three 0.773 / 0.722**. All three over size + process: **+0.003 [+0.001, +0.006] / +0.000 [-0.003, +0.003]**; gradient boosting the same (+0.004 / +0.001). Share of the fixed-cause changes found in the top decile of the score: size 29.7% / 31.2%, all three 30.1% / 31.2% (random 10%). **Inside size quartiles** (test AUC of the full model): DPDK 0.591, 0.575, 0.599, 0.632; Mesa 0.563, 0.540, 0.582, 0.646 (the smallest three quartiles 0.54 to 0.60; neighbourhood alone 0.52 to 0.57; process alone 0.52 to 0.57); repowise reports 0.525, 0.572, 0.593, 0.718 for its size quartiles. Within-size-decile AUC of single features (DPDK / Mesa): callers of the changed functions (sum) 0.523 / 0.512, maximum 0.525 / 0.514, callees 0.537 / 0.528, caller files 0.524 / 0.516, functions within 2 calls 0.554 / 0.527, author tenure 0.468 / 0.482 (less experienced authors slightly more), file churn 0.548 / 0.532, lines 0.541 / 0.531.
| hypothesis | verdict |
|---|---|
| WN1 size alone test AUC at least 0.65 | **supported**: 0.767, 0.718 |
| WN2 neighbourhood adds at least 0.02 over size and process | **not supported**: +0.003, +0.000 |
| WN3 smallest-quartile AUC of the full model at least 0.58 | **not supported**: 0.591 (DPDK, just over), 0.563 (Mesa) |
| WN4 best single neighbourhood feature within-size AUC at least 0.55 | **not supported**: 0.554 (DPDK, just over), 0.528 (Mesa) |
| WN5 process alone beats neighbourhood alone | **not supported**: neighbourhood alone beats process alone (0.681 and 0.632 against 0.558 and 0.569), but only through its correlation with size (inside size deciles both are near 0.52 to 0.55) |
| WN6 top-decile share of all three at least 1.2 times that of size and process | **not supported**: 1.01, 0.99 |
Surprise bar (every group adds under 0.01 over size alone): **met** (largest gain of all three over size alone +0.006).
**Reading.** **Whether a change will need a fix is predicted by its size, and by nothing else we measured.** The same neighbourhood that locates the fix far above size once a fix is needed (within-size AUC 0.73 to 0.85) adds essentially nothing to the question of whether one is needed (+0.00 AUC). The size wall appears here too: inside the smaller size quartiles the full model is barely better than a coin (0.54 to 0.60). Process features (author tenure, recent churn of the touched files) did not beat size either, so the repowise ordering (process before structure) does not show on this label. The position, in one line: **the neighbourhood is a "where" predictor, not a "whether" predictor.**
**Caveats.** The label is "named in a `Fixes:` trailer within two years", which depends on project habit and on how much anyone looked: it measures found, tagged bugs, not bugs. Only DPDK and Mesa (the kernel needs a 1.3-million-commit index; OpenSSL has 261 named causes). Function sets from git hunk headers, unverified (13% phantoms). Neighbourhood features are structural counts at the nearest quarterly snapshot (callers, callees, caller files, functions within 2 calls); nothing semantic. No features of the kind of change were used (shape, whether it adds a check, touches error paths, changes a signature), nor of the code's own history before the change beyond file churn; all untested. Test AUC with a time split, one split per repository.
**Next candidates.** Kind-of-change features at change time (shape of the diff, adds a check or lock, touches error handling, signature changes); a label that does not depend on trailers (reverts, or later changes to the same lines); whether the cause-action classes (adds a check, changes a use) predict *needing* a fix.

## Will this change need a fix? Kind-of-change features (hypotheses fixed 2026-11-18 before running; `tools/sensor/needs_fix_kinds.py`)
Same population, label, split and baseline as the previous test (DPDK 25,367 changes, Mesa 71,875; size, process and neighbourhood give test AUC 0.773 and 0.722). New features **known when the change is made**: **K**, from the change's diff, counts of added and removed lines of each kind (the regex features of the earlier diff-shape work: added or removed null checks, locks, frees, gets, error handling, bounds checks, initialisations, allocations, conditions, types, build macros, comments, returns, calls; condition rewrites; number of hunks); **T**, the diff shape (the eleven shapes of `fix_shapes.shape`) and the kind of change by the verb of the commit subject (feature, restructure, optimisation, fix, other; `change_kinds.cause_type`). Models: logistic regression and gradient boosting on S+P+N, S+P+N+K and S+P+N+K+T.
- **KC1.** S+P+N+K+T raises the logistic test AUC by at least 0.02 over S+P+N in both repositories.
- **KC2.** Inside the smallest size quartile the full model (S+P+N+K+T, logistic) reaches a test AUC of at least 0.60 in both repositories (the size wall broken).
- **KC3.** The top decile of the full model's score holds at least 1.15 times the share of fixed-cause changes that the top decile of S+P+N holds, in both.
- **KC4.** The best single K feature has a within-size-decile AUC of at least 0.56 in both repositories (which one is recorded, not predicted).
- **KC5.** Changes whose subject marks them as fixes (a fix-of-fix) are named as causes at least 1.3 times as often as other changes of the same size decile, in both.
**Would surprise:** the full model adding less than 0.01 AUC over S+P+N in both repositories: the kind of change would then add nothing to size at change time either.

#### Will this change need a fix? Kind-of-change features: results (2026-11-18; `needs_fix_kinds_output.txt`; DPDK 25,367 changes, Mesa 71,875; 30 diff-line features, 16 shape and subject-verb indicators)
Test AUC, DPDK / Mesa (logistic; gradient boosting in brackets): size, process and neighbourhood **0.773 / 0.722** (0.764 / 0.715); + diff-line kinds **0.787 / 0.742** (0.779 / 0.739); + shape and verb **0.789 / 0.748** (0.779 / 0.748). Full model minus S+P+N: **+0.016 [+0.011, +0.021] / +0.027 [+0.021, +0.034]** (boosting +0.015 / +0.033); against size alone (0.767 / 0.718): +0.022 / +0.030. **Inside size quartiles** (test AUC of the full model, against S+P+N in brackets): DPDK 0.628, 0.623, 0.652, 0.679 (0.591, 0.575, 0.599, 0.632); Mesa 0.613, 0.592, 0.650, 0.713 (0.563, 0.540, 0.582, 0.646). Share of the fixed-cause changes in the top decile of the score: DPDK 32.1% (S+P+N 30.1%), Mesa 36.4% (31.2%); random 10%. **Strongest single features** (within-size-decile AUC; above 0.5 means more often named as a cause): **added conditions 0.583 / 0.578** (the strongest in both), added calls 0.548 (DPDK), added returns 0.545, added null checks 0.542 / 0.534, "adds code" shape 0.535 / 0.560, added comments 0.546 (Mesa), subject verb "feature" 0.541 (Mesa); less often fixed: removed calls 0.444 (Mesa), subject verb "restructure" 0.453 (Mesa), "other edit" shape 0.461 / 0.465. Changes whose subject marks them as fixes are 35% (DPDK) and 19% (Mesa) of changes and are named as causes at 0.96 and 0.97 times the rate of other changes of the same size.
| hypothesis | verdict |
|---|---|
| KC1 full model at least +0.02 AUC over S+P+N in both repositories | **not supported, narrowly**: +0.016 (DPDK), +0.027 (Mesa); both intervals exclude zero |
| KC2 smallest-quartile AUC of the full model at least 0.60 in both | **supported**: 0.628, 0.613 (the size wall is breached, modestly: S+P+N had 0.591 and 0.563) |
| KC3 top-decile share at least 1.15 times that of S+P+N in both | **not supported**: 1.07 (DPDK), 1.17 (Mesa) |
| KC4 best single kind feature, within-size AUC at least 0.56 in both | **supported**: added conditions, 0.583 and 0.578 |
| KC5 fix-subject changes named as causes at least 1.3 times as often | **not supported**: 0.96, 0.97 (a fix is no more likely to be the cause of a later fix than other changes of its size) |
Surprise bar (full model adds under 0.01 over S+P+N in both): not met.
**Reading.** **What kind of change it is adds a small but real amount beyond size**, which the neighbourhood and process did not: 2 to 3 AUC points over size alone, a top decile that holds 32 to 36% of the changes later named as causes (size alone 30 to 31%), and an AUC inside the smaller size quartiles of 0.59 to 0.65 against 0.54 to 0.60. The signal that carries it is plain: **changes that add conditions** (more branches added: more places to be wrong) are named as causes more often than others of the same size (0.58 AUC inside size deciles), followed by added calls, returns and null checks and the "adds code" shape; changes that remove calls or restructure are named less. This fits the earlier result that a cause which touched a check is followed by a repair that adds or changes a guard. The prediction remains weak in practical terms: size is still most of the 0.72 to 0.77, and a top-decile lift of 1.07 to 1.17 over S+P+N is not a usable risk score.
**Caveats.** The same as the previous test (label = named in a trailer within two years; DPDK and Mesa; hunk-header function sets unverified), plus: the diff-line features are regular expressions on added and removed lines, not a parser; 46 features were offered to the model, so a part of the +0.02 to +0.03 may be selection on one split per repository (the intervals are over the test set only); the subject-verb indicator depends on a verb list written for the kernel; no held-out repository was used.
**Next candidates.** A held-out repository (train on DPDK, test on Mesa) to check that the added conditions signal transfers; the cause-action classes as features (whether the change adds a check on a name that is widely used); a label that does not depend on trailers.

## Transfer between repositories, and the pattern of additions and deletions (hypotheses fixed 2026-11-18 before running; `tools/sensor/needs_fix_patterns.py`)
**Part A, transfer.** Train on the whole of one repository, test on the whole of the other (DPDK to Mesa, Mesa to DPDK; logistic regression and gradient boosting; same features and label as before). Nothing is shared between training and test, so the in-repository time split is not needed.
- **TR1.** The full model (size, process, neighbourhood, diff-line kinds, shape, subject verb) beats size, process and neighbourhood by at least 0.01 test AUC in both directions (logistic).
- **TR2.** "Added conditions" has a positive standardised coefficient in both repositories' fits, and the coefficients of the diff-line and shape features correlate across the two repositories (Spearman at least 0.4).
**Part B, additions and deletions** (within-size comparison: Mantel-Haenszel rate ratio over size deciles, with a 200-resample bootstrap interval; rate = share of changes named as the cause of a fix within 730 days). Specific tests:
- **EX1.** Pure additions (no removed C/H lines) have a rate ratio of at least 1.2 against the other changes; pure deletions (no added lines) at most 0.8.
- **EX2.** Changes that add an allocation without adding any release (free, put, destroy, refcount) have a rate ratio of at least 1.3 against changes that add both.
- **EX3.** Changes that add calls but add no condition, null check, error handling or return have a rate ratio of at least 1.2 against changes that add calls and one of those.
- **EX4.** Changes that remove conditions and add none have a rate ratio of at least 1.3 against all other changes (deleting checks).
- **EX5.** Changes that add synchronisation (lock, atomic, RCU, barriers) and remove none have a rate ratio of at least 1.3.
- **Exploratory scan (no prediction):** the rate ratio of each of the 30 add and remove line kinds (present or not) in both repositories; those pointing the same way in both with intervals excluding 1 are listed. Thirty patterns in two repositories invite chance findings, so only agreement across both counts.
**Would surprise:** a cross-repository AUC below size alone in either direction (then the kind-of-change lift was fitting to one project).

#### Transfer between repositories, and the pattern of additions and deletions: results (2026-11-18; `needs_fix_patterns_output.txt`)
**Part A, transfer (trained on the whole of one repository, tested on the whole of the other).**
| | size alone | size, process, neighbourhood | + diff-line kinds | + shape and verb (full) | top-decile share, full (S+P+N) |
|---|---|---|---|---|---|
| DPDK -> Mesa (test base rate 6.2%) | 0.710 | 0.714 | 0.732 | **0.739** | 34.6% (30.3%) |
| Mesa -> DPDK (base rate 16.7%) | 0.772 | 0.779 | 0.791 | **0.791** | 31.1% (29.3%) |
Gradient boosting the same within 0.01 (0.732 and 0.790 for the full model). Standardised coefficients of the diff-line and shape features: Spearman correlation between the two repositories 0.57, the same sign for 30 of 46 features; **added conditions is the largest coefficient in both (+0.40 DPDK, +0.26 Mesa)**; "comment only" shape strongly negative in both (-0.13, -0.23), "adds code" shape positive (+0.14, +0.13), "replaces a call or argument" negative (-0.08, -0.09).
**Part B, additions and deletions (Mantel-Haenszel rate ratio within size deciles; DPDK / Mesa).**
| pattern | rate ratio |
|---|---|
| **pure addition** (nothing removed) | 1.13 [1.06, 1.19] / **1.44** [1.34, 1.56] |
| **pure deletion** (nothing added) | **0.27** [0.14, 0.42] / **0.32** [0.22, 0.42] |
| mixed (both added and removed) | 0.94 / 0.80 |
| adds an allocation, no release added | 1.14 / 1.26 (against allocation with release: 0.94 / 0.86) |
| adds calls with no condition, null check, error handling or return | **0.66** / **0.66** (against added calls with a check: 0.57 / 0.60) |
| removes conditions, adds none | **0.37** / **0.58** |
| adds synchronisation, removes none | 1.24 [0.79, 1.66] (n 37) / 1.42 [0.78, 2.22] (n 53): too rare to say |
**Exploratory scan (same direction in both repositories, interval excludes 1; DPDK / Mesa).** Every kind of **added** line is more often in changes named as causes than the same-size changes without it: **added conditions 2.03 / 1.81** (the largest), added null checks 1.48 / 1.59, added error handling 1.40 / 1.64, added initialisation 1.45 / 1.59, added returns 1.49 / 1.44, added comments 1.46 / 1.60, added releases 1.30 / 1.54, added allocations 1.29 / 1.47, added calls 1.51 / 1.31, added build lines 1.45 / 1.34, added type conversions 1.33 / 1.32, added bounds 1.28 / 1.29. Every kind of **removed** line is at or below 1: removed build lines 0.86 / 0.68, removed type conversions 0.88 / 0.72, removed calls 0.91 / 0.70, removed comments 0.89 / 0.79, removed returns 0.90 / 0.82, removed bounds 0.90 / 0.83; removed null checks, locks, releases, errors, initialisations, allocations and conditions about 1.0 (0.85 to 1.16). The synchronisation line kinds are too rare in these two projects to measure (fewer than 200 changes).
| hypothesis | verdict |
|---|---|
| TR1 the full model beats size, process and neighbourhood by 0.01 in both directions | **supported**: +0.024, +0.013 (and above size alone in both: 0.739 against 0.710, 0.791 against 0.772) |
| TR2 added conditions positive in both fits; coefficients correlate at 0.4 | **supported**: +0.40 and +0.26; Spearman 0.57 |
| EX1 pure additions at least 1.2 and pure deletions at most 0.8 | **half**: deletions 0.27 and 0.32 (supported by a wide margin); additions 1.13 (DPDK, short) and 1.44 (Mesa) |
| EX2 allocation without release at least 1.3 against allocation with | **not supported, reversed**: 0.94, 0.86 |
| EX3 added calls without a check at least 1.2 against added calls with one | **not supported, reversed**: 0.57, 0.60 (added calls without a check are *less* often the cause) |
| EX4 removing conditions without adding any at least 1.3 | **not supported, reversed**: 0.37, 0.58 |
| EX5 adding synchronisation without removing at least 1.3 | **not supported / not testable**: n 37 and 53, intervals span 1 |
Surprise bar (cross-repository AUC below size alone): not met.
**Reading.** (1) **The kind-of-change signal transfers**: a model fitted on one project adds 0.013 to 0.024 AUC over size, process and neighbourhood on the other, and the strongest feature (added conditions) is the same in both. So it is not fitting one project. (2) **What marks a change as one that will need a fix is added logic, and deleted code almost never does**: changes that only delete are named as causes about 0.3 times as often as same-size changes, changes that remove conditions without adding any 0.4 to 0.6 times as often; every kind of added line is above 1 (1.3 to 2.0, added conditions the most) and added calls without any accompanying check (0.66) are below the average. The prediction that unbalanced additions (an allocation with no release, calls with no check) would carry the risk was wrong in direction: the risk is in the **amount of added logic**, branches and checks above all, not in what is missing. (3) This fits the earlier finding that a cause which touched a check is followed by a repair that adds or changes a guard: added branches are where the later fixes go.
**A weakness of the label that bears directly on this.** A fix names the commit that **introduced** the faulty lines, which is easiest to identify for added code (the lines can be blamed); a bug caused by deleting something is traceable but is cited less naturally. So the 0.3 rate ratio of pure deletions, and the lift of every kind of added line, are partly a feature of how causes get named and cannot be read as "deleting is safe". The within-size design removes size, not this asymmetry.
**Caveats.** Two repositories only; the line kinds are regular expressions tuned to the kernel's idioms (lock, get and put patterns match little in DPDK and Mesa); 30 patterns scanned in two repositories (only agreement across both is listed); association; the lift over size, 0.013 to 0.024 AUC, is small in practical terms.

## Controls on the kind-of-change result (hypotheses fixed 2026-11-18 before running; `tools/sensor/needs_fix_controls.py`)
The result to control: the kind-of-change features (diff-line kinds, shape, subject verb: "K+T") add +0.016 (DPDK) and +0.027 (Mesa) test AUC to size, process and neighbourhood ("S+P+N": 0.773 and 0.722); added conditions is the strongest feature (within-size AUC 0.58); pure deletions are named as causes 0.27 to 0.32 times as often as same-size changes. Six controls, each aimed at a named weakness, on DPDK and Mesa; "lift" below means the test AUC of S+P+N+K+T minus that of S+P+N (logistic, same time split, intervals from 200 bootstrap resamples of the test set unless noted).
- **C1, a label that does not depend on trailers.** Label = some later commit whose subject contains "fix" touches one of the changed functions (git hunk-header functions) within 365 days. This is "the function was fixed soon after", with no `Fixes:` line and no blame direction. **CT1:** the lift is at least +0.01 in both repositories on this label, and added conditions keeps a within-size AUC of at least 0.55 in both.
- **C2, project and person habits.** Add the commit's directory (two levels; the 40 most common plus "other") and its author (the 300 most prolific plus "other") as indicators to both models. **CT2:** the lift stays at least +0.01 in both.
- **C3, new code.** Drop every change that adds a new C/H file. **CT3:** the lift stays at least +0.01 in both and pure deletions keep a within-size rate ratio of at most 0.8.
- **C4, selection among 46 features.** Shuffle the K+T block jointly across changes within the same size decile (so it keeps its internal structure and its link to size, and loses its link to the change's outcome), refit and score the lift, 60 times. **CT4:** the observed lift lies above the 95th percentile of the shuffled lifts in both repositories.
- **C5, the horizon.** Label = named as a cause within 365, 730 and 1,095 days, on the same population (changes at least three years before the end). **CT5:** the lift is at least +0.01 at all three horizons in both repositories.
- **C6, time direction.** Train on the latest 60% of changes, test on the earliest 40%. **CT6:** the lift is at least +0.01 in both.
**Would surprise (a label artefact):** the lift vanishing (under +0.005) under C1 in both repositories, or under C2: the kind-of-change signal would then be what trailer-writing habits and who writes the change leave behind.

#### Controls on the kind-of-change result: results (2026-11-18; `needs_fix_controls_output.txt`; DPDK 25,367 changes, Mesa 71,875)
Lift = test AUC of S+P+N+K+T minus S+P+N (logistic). Reference on the trailer label at 730 days: **+0.016 [+0.011, +0.020] DPDK, +0.027 [+0.019, +0.034] Mesa**.
| control | DPDK | Mesa | verdict |
|---|---|---|---|
| C1 **label without trailers**: a later fix-subject commit touches a changed function within 365 days (positives 39% / 36% of changes; 30% / 10% of them are also named causes) | **+0.002** [-0.001, +0.004] | **+0.003** [+0.001, +0.004] | **CT1 not supported**: the lift disappears |
| C1 added conditions, within-size AUC on that label (trailer label) | 0.532 (0.583) | 0.522 (0.578) | falls below 0.55 |
| C1 rate ratio: pure deletion / pure addition | 0.89 / **0.76** | 0.80 / **0.87** | additions are now *less* often followed by a fix |
| C2 directory (41) and author (301) indicators in both models | +0.015 [+0.010, +0.018] | +0.022 [+0.016, +0.027] | **CT2 supported** |
| C3 drop changes that add a new C/H file (4.2% / 1.5%) | +0.017 [+0.013, +0.022]; pure deletion 0.28, pure addition 1.15 | +0.028 [+0.021, +0.035]; 0.32, 1.43 | **CT3 supported** |
| C4 shuffle K+T within size deciles (60 shuffles): mean, 95th percentile, largest | -0.002, -0.001, -0.000 | -0.003, -0.001, -0.000 | **CT4 supported**: the observed lift is far outside the null |
| C5 horizons 365 / 730 / 1,095 days (same population) | +0.020 / +0.021 / +0.023 | +0.024 / +0.024 / +0.026 | **CT5 supported** |
| C6 train on the latest 60%, test on the earliest 40% | +0.007 [+0.002, +0.012] | +0.027 [+0.021, +0.034] | **CT6 not supported** (DPDK +0.007 short of +0.01) |
Surprise bar (lift under +0.005 on the alternative label in both, or under C2): **MET** (the alternative label).
**Reading.** **The kind-of-change signal is robust to everything except the definition of the label.** It survives directory and author indicators, the removal of new-file changes, a within-size shuffle of the features (so it is not selection among 46 features), three horizons, and a train and test direction in Mesa; it is not an author or subsystem habit and not new code. But with a label that does not use trailers, "a later fix commit touches the changed functions within a year", the lift vanishes (+0.002, +0.003), the strongest feature falls to 0.52 to 0.53, and pure additions turn from 1.1 to 1.4 times to 0.76 to 0.87 times as often followed by a fix. So **what the features predict is being named as the cause of a fix (the bug is attributed to lines this change added), not the changed code being fixed soon.** The two are different things: a function gets fix commits for many reasons, and the trailer points at the commit whose added lines are blamed, which favours changes that add logic. The earlier statements that added conditions "mark changes that will need a fix" and that deletions are "safer" must be read as statements about attribution unless a label that blames lines (SZZ style) reproduces them.
**Caveats.** The alternative label is crude (the word "fix" in a subject, any fix touching a changed function, 36 to 39% of changes positive, fixes of unrelated bugs count); it is a stress test of the label, not a better label. DPDK's reversed split lifts only +0.007. Hunk-header functions are unverified. Two repositories.
**Decisive next step.** A label that blames lines without trailers: for each fix commit (subject contains "fix"), blame the lines it removes or changes in its first parent and name the commit that introduced them as the cause (SZZ). That label has the same attribution direction as the trailers, but does not depend on project habits for writing them; if the kind-of-change lift survives it, the attribution reading is the right one and the signal is genuine "added logic that later fixes blame"; if it vanishes too, the signal is a property of the trailers.

## Do repairs follow functions that are added or deleted? (hypotheses fixed 2026-11-18 before running; `tools/sensor/added_deleted_functions.py`)
**Gap.** Every repair-radius result concerns functions the cause *changed*. A function a commit **adds** is invisible to the hunk-header method (the header names the function above it), and one it **deletes** left only a "present in one version only" row that was kept and never examined. The question here is the call-graph version of the earlier one: when the graph gains or loses a node, do later repairs land in the node's neighbourhood?
**Events.** For each cause commit of the named pairs (DPDK 15,829 pairs and Mesa 9,526), every changed `.c`/`.h` file is parsed in both versions with tree-sitter (first parent against the commit; a new or deleted file has one version only). Function names present only in the new version are **added**, only in the old are **deleted**. Within a commit a deleted and an added function whose token sets overlap (Jaccard at least 0.7) are a **move or rename** and are excluded (counted). Four event groups: **ADD** (function added to an existing file), **NEWFILE** (functions of a new file), **DEL** (function deleted from a file that remains), **DELFILE** (functions of a deleted file). **Neighbourhood.** For ADD and NEWFILE, the call graph of the nearest quarterly snapshot at or after the commit, with the event functions as the "changed set". For DEL and DELFILE, the **previous** snapshot (the function no longer exists afterwards): its former callers and callees. The repairs are the verified functions the named fix commits edited (compared with the first parent, as before), measured with the same machinery as the repair radius (same-function share, within 1 and 2 calls against the same-file baseline, relation of each repaired function to the event: same, caller, callee, two calls away, same file farther, elsewhere). The same measurement is the reference for modified functions: verified radius within 2 calls DPDK 1.57, Mesa 1.78; same-function share 50% and 57%.
- **AD1.** When the cause adds a function (ADD), the fix edits that new function in at least 60% of pairs, in both repositories (new code is repaired in place).
- **AD2.** Fixes outside the new function lie within 2 calls of it at least 1.5 times as often as same-file functions of similar size, in both.
- **AD3.** Around an added function, callers (within 1 call) are over-represented more than callees: callers1 ratio above callees1 ratio, in both (new call sites are where the new function is misused).
- **DL1.** When the cause deletes a function (DEL), fixes lie within 2 calls of the deleted function in the previous graph at least 1.5 times as often as same-file functions of similar size, in both (the neighbourhood absorbs the loss afterwards).
- **DL2.** Around a deleted function, its former callers are over-represented more than its former callees (callers1 ratio above callees1 ratio), in both.
- **DL3.** The size of the loss matters: deleted functions with 3 or more former callers have at least 1.2 times the share of pairs with a repair within 2 calls that deleted functions with at most 1 former caller have, pooled.
**A group with fewer than 100 pairs having a fixed function outside the event set in a repository is reported but not tested.** **Would surprise:** a radius at or below 1.2 around both added and deleted functions (then the "neighbourhood absorbs a change" pattern is specific to modified functions).

#### Added and deleted functions: first results (2026-11-18; `added_deleted_functions_output.txt`; before the rename check below)
Events and counts, DPDK / Mesa. Cause commits with events: ADD 4,105 / 2,652, NEWFILE 1,136 / 541, DEL 622 / 668, DELFILE 37 / 57; added functions matched to a deletion (moves and renames, excluded, token Jaccard at least 0.7) 1,984 / 1,321.
| group | pairs (measured) | the fix edits an event function itself | radius within 1 call | within 2 calls | callers1 / callees1 | relations of the repaired functions: same / caller / callee / 2 away / same file farther / elsewhere |
|---|---|---|---|---|---|---|
| **ADD** (function added to an existing file) | 8,446 (6,755) / 3,595 (3,192) | 57% / 46% | 2.79 / 4.20 | **2.23 / 3.00** | 3.45 / 1.49; 4.93 / 1.78 | 30, 11, 2, 4, 20, 33% / 33, 17, 2, 4, 15, 29% |
| NEWFILE (a new file) | 3,760 (2,659) / 1,034 (879) | 79% / 79% | 2.06 / 2.44 | 1.77 / 1.93 | 2.25 / 1.48; 2.63 / 2.24 | 46, 7, 2, 2, 2, 41% / 69, 5, 2, 1, 0, 22% |
| **DEL** (function deleted, previous graph) | 1,089 (454) / 824 (456) | 0% / 2% | 3.99 / 4.88 | **3.11 / 3.02** | 4.55 / 2.23; 5.47 / 2.56 | 0, 16, 3, 4, 26, 52% / 1, 20, 2, 5, 17, 56% |
| DELFILE | 45 (15) / 85 (29) | not tested (fewer than 100) | | | | |
| hypothesis | verdict |
|---|---|
| AD1 the fix edits the new function itself in at least 60% | **not supported**: 57% (DPDK), 46% (Mesa) (a new file: 79% in both) |
| AD2 radius around added functions at least 1.5 | **supported**: 2.23, 3.00 |
| AD3 callers over-represented more than callees around added functions | **supported**: 3.45 against 1.49, 4.93 against 1.78 |
| DL1 radius around deleted functions at least 1.5 | **supported**: 3.11, 3.02 |
| DL2 former callers over-represented more than former callees | **supported**: 4.55 against 2.23, 5.47 against 2.56 |
| DL3 deleted functions with 3 or more former callers have at least 1.2 times the repair share of those with at most 1 | **supported**: 48% against 28% = 1.74 (n 324 and 399) |
Surprise bar (radius at or below 1.2 around both): not met.
**Reading (provisional).** Repairs do cluster around functions the graph gains or loses, more tightly than around modified functions (2.2 to 3.1 against 1.6 to 1.8 within 2 calls), callers more than callees, and a deletion with many former callers is followed by repairs in the old neighbourhood 1.7 times as often as one with few. **This rests on an unvalidated move-and-rename filter** (token-set overlap 0.7), which excluded a large share of added functions: a rename that slips through would appear as a delete plus an add whose "neighbourhood" is the same function under two names. The check below tests that filter.
