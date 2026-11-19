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

## Checking the move and rename filter (hypotheses fixed 2026-11-18 before running; `tools/sensor/rename_check.py`)
The owner's pointer: the engine's structural fingerprint and git's rename and follow machinery should resolve renames well. Three ways of recognising that an added function is a moved or renamed deleted function of the same commit: **M1** token-set Jaccard at least 0.7 (used so far); **M2** the engine-style structural match from the scan databases, with no names: the yes/no fingerprint of 18 keyword families (branches, pointers, allocation, bit operations, locks, cleanup, safety checks, I/O, API, state flux, concurrency, globals, casts, bail-outs, prints, heat triggers, macros) equal, the call set (callee names) overlapping at least 0.5, and size within a factor of 2, taking the deleted function from the previous snapshot and the added one from the next; **M3 (reference, independent of both)** git's line-origin tracking: `git blame -w -M -C -C -C` on the added function's lines at the commit; the function is a **move** of a deleted function when at least half of its lines are attributed to commits older than the cause and at least half of its lines also occur in that deleted function (the partner); **new code** when at most 10% of its lines are older. DPDK, up to 150 cause commits that both add and delete functions.
- **RC1.** M2 finds the partner of at least 70% of the reference's moves where both snapshots hold the functions; M1 at least 60%.
- **RC2.** Both methods call at most 10% of the reference's new-code functions a move (precision).
- **RC3.** M1 and M2 disagree on whether an added function is a move for at least 15% of the added functions (so the choice of matcher matters).
- **RC4.** The reference finds moves that **neither** method matches in at most 15% of its moves.
**Would surprise:** M1 recalling under 40% of the reference's moves (the 1,984 and 1,321 matched functions would then be a floor, and the unfiltered events a mixture with renames).

#### Checking the move and rename filter: results (2026-11-18; `rename_check_output.txt`; DPDK, 120 cause commits that both add and delete functions, 600 added functions blamed)
Reference (git line-origin tracking, `blame -w -M -C -C -C`): **move 191, new code 194, ambiguous 215** (the ambiguous ones are not scored).
| matcher | recall of the reference's moves | right partner | calls new code a move |
|---|---|---|---|
| **M1** token-set overlap 0.7 (used in the added/deleted run) | **77%** (of 191) | 76% | **4%** |
| **M2** engine-style structural match (18-family fingerprint, call set, size) | **57%** (of 124 moves with snapshot data) | 48% | 7% (of 96) |
M2 had snapshot data (the function present in both the previous and the next quarterly scan) for 124 of the 191 moves and 96 of the 194 new functions. M1 and M2 disagree on whether an added function is a move for 14% of the 327 with snapshot data; **20% of the reference's moves (39 of 191) are matched by neither**.
| hypothesis | verdict |
|---|---|
| RC1 M2 recall at least 70%, M1 at least 60% | **not supported**: M2 57%, M1 77% |
| RC2 both call at most 10% of new code a move | **supported**: 4% and 7% |
| RC3 disagreement at least 15% | **not supported, narrowly**: 14% |
| RC4 moves neither finds at most 15% | **not supported**: 20% |
Surprise bar (M1 recall under 40%): not met.
**Reading.** The token-overlap filter used for the added and deleted run recognises 77% of the moves that git's own line tracking finds, with 4% false alarms, so the filter was reasonable; the structural fingerprint did **not** do better in this setting (57%, right partner 48%). Why M2 trails, by the examples: it compares quarterly scans (a function can change a lot within a quarter), the fingerprint here is 18 keyword families and a call set, not the engine's control-flow skeleton layer, and it needs the function in both scans. The moves neither finds are mostly **splits and rewrites** (for example `tap_tx_l3_cksum` and `tap_tx_l4_cksum` both taken out of `tap_tx_offload`; `hash_rxq_special_flow_enable` from `hash_rxq_allmulticast_enable`: one function becoming two or a body reworked while moving), which a name-free fingerprint does not catch either. **A cheap improvement:** treating a function as a move when either M1 or M2 says so recalls about 80% of the reference's moves; the exclusion in the added and deleted run misses roughly 1 in 4 moves, so some renames remain in the ADD and DEL groups. The effect of that on the radius around added and deleted functions is not yet measured. **Caveats.** One repository, 120 commits; the reference is itself imperfect (blame can miss heavy rewrites, and ambiguous cases are left out); M2 uses a 18-family proxy for the engine's fingerprint, not the full scanner.

## Sensitivity of the added and deleted function result to the rename filter (hypotheses fixed 2026-11-18 before running; `tools/sensor/added_deleted_sensitivity.py`)
The first run excluded added functions matched to a deleted one by token overlap 0.7 (recall 77% of git-confirmed moves, 4% false alarms; about 1 move in 4 still got through). To see whether the radius depends on that choice the ADD and DEL groups are rebuilt under six filters, each excluding functions it calls moves or renames: **none** (nothing excluded: every move counts as an add plus a delete); **J.5**, **J.7** (the first run), **J.9** (token overlap thresholds); **M2** (structural fingerprint of 18 keyword families equal, call set overlap at least 0.5, size within a factor of 2, from the scans before and after the commit); **union** (J.7 or M2; recall about 80%). DPDK and Mesa; same measurement as before (radius within 2 calls against the same-file baseline, same-function share, callers1 and callees1).
- **SN1.** The radius within 2 calls around **added** functions is at least 1.5 in every filter, in both repositories.
- **SN2.** The radius around **deleted** functions is at least 1.5 in every filter, in both.
- **SN3.** The radius under every filter lies within 15% of the J.7 value (the conclusion does not depend on the filter).
- **SN4.** Callers1 stays above callees1 around both added and deleted functions in every filter, in both.
- **SN5.** DL3 holds under the union filter: deleted functions with 3 or more former callers have at least 1.2 times the share of pairs with a repair within 2 calls that those with at most 1 have, pooled.
**Would surprise:** the radius around added or deleted functions at or below 1.2 under any filter (then the result was a feature of one filter).

#### Sensitivity of the added and deleted function result to the rename filter: results (2026-11-18; `added_deleted_sensitivity_output.txt`)
Added functions excluded as moves, of 19,744 (DPDK) and 10,002 (Mesa): J.5 1,663 and 1,004; J.7 1,291 and 706; J.9 691 and 327; M2 477 and 356; union 1,355 and 815.
Radius within 2 calls against the same-file baseline, by filter (**none** keeps every move as an add and a delete):
| group | repository | none | J.5 | J.7 (first run) | J.9 | M2 | union |
|---|---|---|---|---|---|---|---|
| ADD | DPDK | 2.24 | 2.24 | 2.23 | 2.24 | 2.23 | 2.23 |
| ADD | Mesa | 3.05 | 2.99 | 2.99 | 3.07 | 3.04 | 2.99 |
| DEL (previous graph) | DPDK | 2.78 | 3.18 | 3.08 | 2.81 | 3.08 | 3.07 |
| DEL | Mesa | 2.98 | 3.08 | 2.99 | 2.91 | 2.94 | 2.95 |
Callers1 against callees1 (union): ADD DPDK 3.48 against 1.47, Mesa 4.93 against 1.75; DEL DPDK 4.56 against 1.91, Mesa 5.46 against 2.39. Same-function share of added-function pairs: 57% (DPDK) and 46% (Mesa) in every filter.
| hypothesis | verdict |
|---|---|
| SN1 radius around added functions at least 1.5 in every filter | **supported**: 2.23 to 2.24 (DPDK), 2.99 to 3.07 (Mesa) |
| SN2 radius around deleted functions at least 1.5 in every filter | **supported**: 2.78 to 3.18, 2.91 to 3.08 |
| SN3 every radius within 15% of the J.7 value | **supported**: the largest deviation 10% (DEL, DPDK, J.5 and J.9 against J.7) |
| SN4 callers1 above callees1 everywhere | **supported** (every filter, group and repository) |
| SN5 DL3 under the union filter | **supported**: deleted functions with 3 or more former callers 48% (n 308) against 27% (n 398) with at most 1 = **1.80** |
Surprise bar (any radius at or below 1.2): not met (lowest 2.23).
**Reading.** The added and deleted function result does **not** depend on how renames are handled: the radius around added functions moves by under 3% across six filters (including none at all) and around deleted functions by at most 10%. So the roughly 1 move in 4 that the first filter missed cannot account for the result. After a function is added, repairs land within two calls of it 2.2 (DPDK) to 3.0 (Mesa) times as often as same-file functions of similar size, callers above callees; after one is deleted, repairs land among its former neighbours about 3 times as often, former callers above former callees, and a deletion with several former callers (3 or more) is followed by a repair in the old neighbourhood 1.8 times as often as one with at most one. These radii are larger than around modified functions (1.57 and 1.78 on the same verified measurement), so **the graph absorbs the gain or loss of a node at least as locally as it absorbs a change to one**.
**Caveats.** Two repositories, C only; an added function is in the changed set as a whole (new functions that call or are called by many others will have large neighbourhoods; the baseline is same-file functions of similar size, which does not model that); the former callers of a deleted function have to be edited in the same commit, so what is measured is the repair that follows the commit, not the edit it forced; function splits and rewrites that move code (about 20% of git-confirmed moves are found by neither matcher) are in the ADD and DEL groups under every filter; NEWFILE and DELFILE are descriptive only (DELFILE under 100 pairs); the kernel was not run.

## Ranking test for added and deleted functions: AUC and top 20 (hypotheses fixed 2026-11-18 before running; `tools/sensor/retrieval_added_deleted.py`)
The ranking test of the neighbourhood (reference: modified functions, kernel, DPDK and Mesa pooled, 22,532 pairs: size alone AUC 0.737 and top 20 **0.2%**; same file 0.794 / 20.9%; call distance alone 0.734 / 30.0% with within-size AUC 0.734; file then distance 0.851 / 39.9%; **file, distance, then size 0.925 / 45.1%**; random 0.500 / 0.0%) is repeated with the **added** (ADD) and **deleted** (DEL) function events as the change. Same machinery: every function of the call graph is a candidate (ADD: the snapshot at or after the commit, DEL: the previous snapshot, the event functions excluded); positives are the verified functions the named fix edited, outside the event set; rankers scored exactly from feature-cell counts, ties split. Events as in the sensitivity run with the **union** filter (moves and renames excluded). **A file-level version** is added: every file of the snapshot is a candidate, a file is positive if a repaired function (outside the event set) lies in it; features of a file: contains an event function, fewest calls from any of its functions to the event (1, 2, 3 or farther), size decile of the file (sum of function sizes); rankers: random, file size, event file, call distance, event file then distance, event file, distance, then size. DPDK and Mesa, per group.
- **RL1.** The function-level combined ranker (file, then distance, then size) puts a repaired function in the top 20 for at least 3 times the share of pairs that size alone does, for ADD and for DEL, in both repositories.
- **RL2.** Call distance alone has a within-size AUC of at least 0.65 for ADD and for DEL in both.
- **RL3.** For DEL, call distance alone has a top-20 share of at least 30% (the modified-function value) in both repositories (a deleted function leaves a tighter neighbourhood).
- **RL4.** At file level the combined ranker (event file, then distance, then size) has a repaired file among its top 20 for at least 60% of pairs, for ADD and for DEL in both.
- **RL5.** The function-level combined ranker's top-20 share is at least 40% for ADD and for DEL in both (modified functions: 45%).
**Would surprise:** a within-size AUC at or below 0.55 for call distance in either group (then the neighbourhood of an added or deleted function is a size effect).

#### Ranking test for added and deleted functions: results (2026-11-18; `retrieval_added_deleted_output.txt`; union rename filter)
Pairs with events / ranked (a repaired function outside the event set exists in the graph); candidates per pair (median): DPDK ADD 8,421 / 4,342, 30,069 functions, 1,800 files; DPDK DEL 1,037 / 439, 33,561 and 1,971; Mesa ADD 3,575 / 2,041, 66,939 and 4,343; Mesa DEL 792 / 430, 66,226 and 4,197.
**Functions (AUC, top 20 of about 30,000 to 67,000; DPDK ADD / DPDK DEL / Mesa ADD / Mesa DEL).**
| ranker | AUC | top 20 |
|---|---|---|
| random | 0.500 | 0.1 / 0.1 / 0.0 / 0.0% |
| size alone | 0.789 / 0.765 / 0.832 / 0.805 | **0.4 / 0.4 / 0.2 / 0.2%** |
| same file as the event | 0.764 / 0.762 / 0.750 / 0.717 | 27.7 / 32.0 / 25.8 / 25.0% |
| call distance alone | 0.677 / 0.663 / 0.700 / 0.671 | 39.6 / 36.5 / 40.7 / 35.8% |
| file, then distance | 0.821 / 0.800 / 0.814 / 0.776 | 44.3 / 45.9 / 43.4 / 37.8% |
| **file, distance, then size** | **0.916 / 0.905 / 0.934 / 0.911** | **52.5 / 52.9 / 50.4 / 44.3%** |
Within-size AUC (size cannot help): call distance 0.677 / 0.663 / 0.700 / 0.671; file then distance 0.821 / 0.800 / 0.814 / 0.776. For comparison, modified functions pooled: size alone 0.737 and top 20 0.2%; call distance 0.734 and 30.0%; combined 0.925 and 45.1%.
**Files (every file of the snapshot a candidate; a file is positive if a repaired function outside the event set lies in it).**
| ranker | top 5 | top 20 | top 50 (DPDK ADD) | top 20, repairs in **other** files only: DPDK ADD / DPDK DEL / Mesa ADD / Mesa DEL |
|---|---|---|---|---|
| random | 0.3% | 1.3% | 3.3% | 1.3 / 1.2 / 0.5 / 0.5% |
| file size alone | 1.8% | 7.1% | 17.8% | 5.7 / 5.1 / 2.6 / 2.5% |
| the event's own file | 59.3% | 59.9% | 60.7% | not applicable |
| call distance alone | 65.4% | 73.1% | 73.9% | 48.5 / 40.7 / 41.6 / 37.7% |
| **event file, distance, then size** | **75.9%** | **79.9%** | 81.7% | **50.4 / 43.0 / 43.1 / 38.8%** |
Combined file ranker, repaired file in the top 20, all repairs (DPDK ADD / DEL, Mesa ADD / DEL): **80% / 76% / 73% / 67%**; repairs in other files only: **50% / 43% / 43% / 39%**.
| hypothesis | verdict |
|---|---|
| RL1 combined top 20 at least 3 times size alone in every group | **supported** (117 to 258 times) |
| RL2 call distance within-size AUC at least 0.65 in every group | **supported**: 0.663 to 0.700 |
| RL3 DEL call distance top 20 at least 30% | **supported**: 36.5%, 35.8% |
| RL4 combined file ranker, repaired file in the top 20 for at least 60% | **supported**: 67% to 80% |
| RL5 combined function ranker top 20 at least 40% | **supported**: 44% to 53% |
Surprise bar (within-size AUC of call distance at or below 0.55): not met.
**Reading.** The neighbourhood ranks the repaired function and file for added and deleted functions as well as it does for modified ones, and slightly better at the top: the combined function ranker has the repaired function in its top 20 of tens of thousands for 44 to 53% of pairs (45% for modified functions; size alone 0.2 to 0.4%), and at file level a repaired file is among the top 20 files for 67 to 80% of pairs (random 0.5 to 1.3%). **The easy part is the event's own file** (53 to 60% of pairs by itself); counting only repairs in **other** files the top 20 still holds one for **39 to 50%** of pairs (random 0.5 to 1.3%, file size 2.5 to 5.7%), found by call distance. The call-distance ranker alone is the one that works for other-file repairs (within-size AUC 0.66 to 0.70).
**Caveats.** The event is known at change time, but the ranker uses where the added or deleted function sits and its call neighbours, which for an added function means its callers and callees at the next quarterly scan (a small look-ahead: calls added after the commit and before the scan are in the graph); only pairs where a repaired function outside the event set exists in the graph are ranked (about half of the pairs); size-only AUCs are high (0.77 to 0.83) because larger functions and files are repaired more often, but useless at the top (0.2 to 0.4%); two repositories, C only; "files" here are the files of repaired functions identified from the fix commit's verified hunk-header functions.

## Validation in other languages (hypotheses fixed 2026-11-18 before running; `tools/sensor/lang_validation.py`)
**Problem.** Every result so far is C, from projects that write `Fixes: <sha>` trailers. Python, Go, Java and Rust projects do not, so the cause of a fix has to come from somewhere else. **Cause label without trailers (SZZ style):** a *fix commit* is a non-merge commit whose subject contains "fix", "fixes", "fixed", "bug" or "regression" (not "revert") and which modifies source files of the language outside test paths; for each hunk of the fix that removes or changes lines, `git blame -w -M` on the parent attributes those lines to the commits that last wrote them; the commit blamed for the most lines (older than the fix) is the **cause**. Test files (paths with test, tests, testing, spec; `test_*.py`, `*_test.go`, `*Test.java`) are excluded from the functions on both sides. **Functions without hunk headers:** each commit's changed files are parsed with tree-sitter in the parent and the commit; a function counts as changed if its name occurs in both with different text (names plain, as in the scan databases). **Measurement:** the same exact measurement as for C (`blast_radius.measure_snapshot`: repaired functions outside the cause's changed set, within 1 and 2 calls against same-file functions of similar size, callers and callees, same-function share), on the existing quarterly scans: Python sphinx, scapy and sqlmap; Go prometheus; Java commons-lang and commons-io; Rust ripgrep. Calibration: the same SZZ pairs on the C projects **DPDK** (2,500 sampled fixes) and **curl**, set against their trailer-based radius on verified functions (DPDK 1.57, curl 1.65). Caveat fixed in advance: with this label the cause is, by construction, a commit whose lines the fix removed, so the fixed function usually sits in the changed set; the measured repairs are the *other* functions the fix edited, a different selection from the trailer pairs.
- **LG1 (calibration).** SZZ pairs on DPDK and curl give a radius within 2 calls within 25% of the trailer-based value (DPDK 1.57, curl 1.65). If this fails, the language results are reported but not compared with C.
- **LG2.** In each of the Python, Go and Java repositories with at least 100 pairs that have a repaired function outside the changed set, the radius within 2 calls is at least 1.3 with a lower bound above 1.1.
- **LG3.** For repairs in a different file, callers1 is above callees1, pooled over the non-C repositories.
- **LG4.** The pooled non-C radius within 2 calls lies between 1.2 and 2.5 (the same order as C).
- **LG5.** Pooled over the non-C repositories, causes of under 30 changed lines have at least 1.2 times the radius of causes of 100 or more lines (the size trend of C).
**Would surprise:** a pooled non-C radius at or below 1.1 (then the pattern is a property of the C projects measured, or of trailer labels).

#### Validation in other languages: results (2026-11-18; `lang_validation_output.txt`, `lang_validation_by_language_output.txt`; causes from SZZ-style blame, 2,500 fix-like commits sampled per repository at most)
| repository (language) | fix-cause pairs / measured / repaired function outside the changed set | same function | radius within 1 call | **within 2 calls** | callers1 / callees1 | resolved call edges per function; functions with a caller |
|---|---|---|---|---|---|---|
| **calibration** DPDK (C) | 1,841 / 977 / 594 | 57% | 1.73 | **1.55** [1.44, 1.67] (trailers: 1.57) | 1.95 / 1.66 | 1.98; 67% |
| calibration curl (C) | 1,306 / 815 / 383 | 70% | 1.63 | **1.43** [1.31, 1.58] (trailers: 1.65) | 1.64 / 1.75 | 2.28; 56% |
| sphinx (Python) | 1,539 / 982 / 450 | 71% | 1.96 | **1.62** [1.42, 1.84] | 1.52 / 2.09 | 0.78; 21% |
| scapy (Python) | 1,142 / 481 / 280 | 67% | 1.62 | **1.48** [1.24, 1.75] | 1.37 / 2.04 | 1.02; 25% |
| sqlmap (Python) | 2,211 / 1,714 / 783 | 72% | 2.48 | **1.85** [1.67, 2.05] | 2.10 / 2.49 | 1.45; 36% |
| prometheus (Go) | 1,260 / 698 / 380 | 63% | 1.93 | **1.50** [1.33, 1.69] | 1.99 / 1.96 | 1.57; 35% |
| commons-lang (Java) | 684 / 179 / 73 | 73% | 1.39 | 1.18 [0.77, 1.80] | 1.38 / 1.40 | 0.72; 15% |
| commons-io (Java) | 312 / 110 / 66 | 58% | 2.40 | 2.48 [1.86, 3.45] | 1.52 / 3.84 | 0.89; 16% |
| ripgrep (Rust) | 173 / 87 / 64 | 38% | 0.92 | 1.04 [0.70, 1.39] | 0.00 / 1.03 | 0.26; 9% |
| **pooled by language, within 2 calls** | | | | **Python 1.70 [1.59, 1.84] (n 1,245); Go 1.50 [1.33, 1.71] (315); Java 1.63 [1.24, 2.12] (110); Rust 1.04 [0.71, 1.35] (56); C with blame-based causes 1.50 [1.41, 1.59] (870)** | | |
Pooled non-C (all seven): **1.63 [1.53, 1.73]** (n 2,096), same function 69%. Repairs in a different file, pooled non-C (n 869): callers1 1.47, callees1 2.72. Under 30 changed lines against 100 or more, pooled non-C: 2.11 against 1.41 (1.49 times); Python and C show the size trend in every repository that has enough small causes (sphinx 1.78 against 1.39, scapy 2.66 against 1.25, sqlmap 2.09 against 1.64, prometheus 2.97 against 1.35, DPDK 2.13 against 1.42).
| hypothesis | verdict |
|---|---|
| LG1 SZZ radius within 25% of the trailer radius on DPDK and curl | **supported**: 1.55 against 1.57 (-1%), 1.43 against 1.65 (-14%): the blame-based label reproduces the trailer result in C |
| LG2 radius at least 1.3 (lower bound above 1.1) in each Python, Go and Java repository with at least 100 pairs | **supported for the four testable repositories** (sphinx 1.62, scapy 1.48, sqlmap 1.85, prometheus 1.50, lower bounds 1.25 to 1.67); both Java repositories have fewer than 100 repaired pairs outside the changed set (73 and 66), so untestable (their pooled 1.63 is compatible, with an interval of 1.24 to 2.12) |
| LG3 callers1 above callees1 for different-file repairs, pooled non-C | **not supported**: 1.47 against 2.72 (callees above callers in Python and Java; equal in Go: 1.06 and 1.06 on 132 pairs) |
| LG4 pooled non-C radius between 1.2 and 2.5 | **supported**: 1.63 |
| LG5 under 30 lines at least 1.2 times 100 or more, pooled non-C | **supported**: 2.11 against 1.41 = 1.49 |
Surprise bar (pooled non-C radius at or below 1.1): not met.
**Reading.** **The repair radius is not a property of C.** With a cause label that needs no trailers (calibrated on two C projects, where it reproduces the trailer value to within 1% and 14%), repairs land within two calls of the changed functions 1.5 to 1.9 times as often as same-file functions of similar size in three Python projects (1.48 to 1.85) and in a Go project (1.50), the same order as in C (1.57 to 2.15), and the size trend appears again (small causes about twice, large ones 1.4). **The caller-first direction does not carry over**: in Python and Java the callees are over-represented more than the callers (callers 1.47 against callees 2.72 for repairs in a different file). **A caution on every non-C figure:** the static call graph is much sparser than in C (0.7 to 1.6 resolved confident edges per function against 2.0 to 2.3; only 15 to 36% of functions have a recorded caller against 56 to 67%), because method calls through objects, interfaces and traits are not resolved. A sparse graph misses neighbours, so the radius is probably understated, the caller-direction numbers (callers need resolved incoming calls) cannot be trusted, and Rust (0.26 edges per function, 9% with a caller; ripgrep radius 1.04 on 56 pairs) and Java are untestable in practice rather than negative.
**Caveats.** SZZ labels have their own artefacts (blame follows lines, not the author's intent, and the fixed function usually lies in the changed set by construction, so only the *other* functions the fix edited are measured; same-function shares of 57 to 73% here are not comparable with the trailer figures); fix commits identified by words in the subject; test files excluded from both sides; 2,500 fix-like commits sampled per repository; tree-sitter names are plain (methods of different classes with the same name in a file are merged); Ruby, PHP, C#, TypeScript and the rest are untested; nothing here tests the added and deleted function result, the ranking test or the will-it-need-a-fix test outside C.

## What is the call graph missing in the other languages? (hypotheses fixed 2026-11-18 before running; `tools/sensor/callgraph_audit.py`, `tools/sensor/lang_graph_sensitivity.py`)
**Correction to the claim above.** "Sparse" was measured as confident edges per function, which is not accuracy: it counts only edges the engine resolves to **one** target (`candidates` = 1), and a graph can be thin because calls are unresolvable, or because the analysis filtered out ambiguous edges. The engine's database also records, per call edge, how it was resolved (`step`: class, file, import, qualified, receiver, typed, tie, unseen) and how many candidate targets it had. For sphinx (latest scan) the `call` edges are 11,672: 5,853 with one candidate, **4,359 with more than one** (dropped by the analysis), 1,460 unresolved.
**Audit A, what the engine records (all nine repositories, latest scan).** Call edges by resolution: unique target, ambiguous target (candidates above 1), unresolved; and by resolution step.
**Audit B, what the engine does not record (independent check against the source).** Every source file of the latest scan's commit is parsed with tree-sitter; each call site whose callee has a simple name that **some function in the repository defines** is a *name-resolvable call*, taken as the pair (file, callee name). Call form: *plain* (`f(x)`), *method or member* (`x.f()`, `x->f()`, Go selector, Rust field or path), by language grammar. Recall = the share of these pairs for which the engine has a `call` edge for that file and name at all, with a resolved target, with a unique target. Name matching is the generous standard (the same resolver an ideal name-based tool would use); it says what the engine fails to link even by name, not whether the links it makes are right.
**Audit C, does it matter for the result.** The language measurement is repeated with the call graph admitting ambiguous edges up to 3, 10 and any number of candidates (the first run: 1).
- **CG1.** Ambiguous edges (candidates above 1) are at least 25% of the resolved call edges in each of the Python, Java and Go repositories, and at most 20% in each C repository.
- **CG2.** Independent recall (any engine edge for a name-resolvable (file, name) pair) is at most 85% in the non-C repositories pooled and at least 90% in the C repositories pooled.
- **CG3.** In the non-C repositories pooled, plain calls have a recall at least 10 points above method or member calls.
- **CG4.** Admitting ambiguous edges up to 10 candidates changes the pooled Python radius within 2 calls by at most 20% (the radius is not an artefact of the confidence filter).
- **CG5.** Admitting ambiguous edges raises the callers1 over callees1 ratio for different-file repairs, pooled Python, to at least 1.2 times the confident-only ratio (callers are the casualty of the filter).
**Would surprise:** independent recall below 50% in the non-C repositories (the engine would then be missing most calls by name, and every non-C graph result would be unreliable).

#### What is the call graph missing in the other languages? Results (2026-11-18; `callgraph_audit_output.txt`, `lang_graph_sensitivity_output.txt`; latest scan of each repository)
**Audit A, recorded `call` edges (unique target / ambiguous target / unresolved) and Audit B, recall against the source (name-resolvable (file, callee name) pairs: an engine edge exists / a resolved target / a unique target).**
| repository | functions | edges | unique / ambiguous / unresolved | recall: any edge / resolved / unique | plain calls: any / unique | member calls: any / unique |
|---|---|---|---|---|---|---|
| dpdk (C) | 60,500 | 123,151 | 97 / 1 / 2% | 96 / 94 / 93% | 96 / 93% | n 332: 1 / 1% |
| curl (C) | 7,392 | 17,501 | 96 / 3 / 0% | 99 / 99 / 99% | 100 / 99% | |
| sphinx (Python) | 7,499 | 11,672 | 50 / 37 / 13% | 87 / 80 / 48% | 82 / 73% | 89 / 39% |
| scapy (Python) | 7,656 | 14,146 | 55 / 24 / 21% | 86 / 83 / 53% | 89 / 83% | 84 / 41% |
| sqlmap (Python) | 2,982 | 7,020 | 62 / 25 / 14% | 91 / 84 / 62% | 95 / 75% | 88 / 54% |
| prometheus (Go) | 10,562 | 37,393 | 44 / 38 / 18% | 97 / 82 / 49% | 99 / 79% | 97 / 38% |
| commons-lang (Java) | 11,565 | 24,214 | 34 / 55 / 10% | 86 / 73 / 33% | 75 / 46% | 89 / 30% |
| commons-io (Java) | 7,285 | 16,174 | 40 / 48 / 12% | 88 / 76 / 34% | 83 / 48% | 89 / 30% |
| ripgrep (Rust) | 2,419 | 3,147 | 20 / 47 / 33% | **34 / 25 / 9%** | 95 / 70% | **25 / 2%** (path calls 41 / 6%) |
Steps by which the ambiguity arises: **receiver** (a method called on an object: 3,450 edges in sphinx, 16,258 in prometheus, 7,681 in commons-lang; 39 to 62% ambiguous, 23 to 51% unresolved in Python, Go and Rust), **typed**, **class**, **qualified**, **overload** (Java) and **import** (Go 52% ambiguous). **Audit C, the language measurement with the call graph admitting ambiguous edges** (radius within 2 calls; confident only / up to 3 / up to 10 / any number of candidates): **Python 1.70 / 1.71 / 1.67 / 1.66**; Go 1.50 / 1.43 / 1.34 / 1.27; Java 1.63 / 1.43 / 1.43 / 1.41; Rust 1.04 / 0.97 / 0.97 / 1.20; C with blame causes 1.50 / 1.50 / 1.49 / 1.49. Pooled Python, repairs in a different file (n 638): callers1 / callees1 2.04 / 4.08 (confident), 1.51 / 3.77 (up to 10 candidates).
| hypothesis | verdict |
|---|---|
| CG1 ambiguous edges at least 25% of resolved edges in the Python, Java and Go repositories, at most 20% in C | **supported**: Python 29 to 43%, Go 46%, Java 54 to 62%, Rust 70%; C 1 to 3% |
| CG2 any-edge recall at most 85% non-C pooled and at least 90% in C | **not supported, the engine does better than predicted outside C**: non-C pooled 88%, C 96% (but Rust 34% pulls the non-C figure down: Python 86 to 91%, Go 97%, Java 86 to 88%) |
| CG3 plain calls at least 10 points above member calls in recall | **not supported on whether an edge exists** (plain 90%, member 88%); **supported on whether it resolves to one target** (plain 46 to 83% unique, member 30 to 54%: a method call is recorded but is usually ambiguous) |
| CG4 admitting ambiguous edges changes the pooled Python radius by at most 20% | **supported**: 1.70 to 1.67 (-2%) |
| CG5 admitting ambiguous edges raises callers over callees (other-file repairs, pooled Python) to at least 1.2 times | **not supported**: 0.50 to 0.40; the callees-over-callers direction does not come from the filter |
Surprise bar (non-C recall below 50%): not met overall (88%); **met for Rust** (34%).
**Reading.** **The call graph for Python, Go and Java is not missing calls; it is missing certainty.** The engine records an edge for 86 to 97% of the calls that can be matched to a repository function by name (C: 96 to 99%), but only 33 to 62% resolve to **one** target, because method calls through an object (the `receiver` step) match several functions of the same name. The analysis had used only the unique-target edges, which dropped 24 to 62% of the edges; **admitting the ambiguous ones does not change the language result**: the Python radius stays at 1.66 to 1.71, Go and Java drift down (1.50 to 1.27 and 1.63 to 1.41) as wrong candidates add noise, and the callees-above-callers direction in Python is unchanged. So **the earlier statements that a sparse graph "probably understates the radius" and that the caller figures "cannot be trusted" were too strong for Python, Go and Java**: the result is robust to the filter. **Rust is the real gap**: the engine records an edge for only 34% of name-resolvable calls (member calls 25%, path calls such as `Type::new` 41%), against 95% for plain calls, so the ripgrep radius (1.04) is a statement about the graph, not about Rust.
**Caveats.** Recall is measured against name matching (a call site whose callee has the same simple name as some function in the repository), not against what the program really calls; it says nothing about whether the targets the engine picks are right, which needs an oracle (a Python, Go or Java call graph tool); a call recorded with several candidates may point at the wrong one; one scan per repository, the latest; tests included in the graph; ripgrep is one small project; name-resolvable pairs are counted per (file, callee name), so several call sites of the same name in a file count once.

#### Back-test gate for "where to look first": result (2026-11-18; see `sensors/suspects.md` section 14, `backtest_gate_output.txt`)
Held-out repositories, blame-based causes. Function top 20 of the ranking (same file, call distance, size) against size alone: **C 47.3% against 5.4%** (libgit2, redis, libxml2; 1,604 pairs; within-size AUC 0.737); **Python 35.7% against 6.6%** (sphinx, scapy, sqlmap; 1,513; 0.644); **Go 42.4% against 4.5%** (prometheus; 380; 0.692); files top 10 of the ranking 83.6%, 60.9%, 70.3%. The registered gate (top 20 at least 30% for C and 25% for Python and Go; within-size AUC at least 0.65 and 0.60) is met on those two criteria in every language; **the third criterion, at least 50 times the share of size alone, fails in every language (9, 5 and 9 times) because it depends on the number of candidates** (size alone finds 4 to 8% in these small repositories, 0.2 to 0.4% in the large ones). A scale-free replacement (at least 15 percentage points and 3 times) is proposed, post hoc, and awaits the owner's approval.

## Same directory as a ranking feature (hypotheses fixed 2026-11-18 before running; `tools/sensor/same_directory.py`)
The mock-up's miss (virtio-user: four repaired functions in a sibling file of the same directory, ranked 1,346 to 20,680) suggests that **directory proximity** is a feature the ranking lacks: every candidate with no call link to a changed function currently ties and is ordered by size. **Directory category** of a candidate: 4 = its file's directory is the directory of a changed function's file; 3 = it shares all but the last component with it (a parent, a sibling or a child directory one level away); 2 = shares all but two; 1 = shares the first component; 0 = nothing (the best over the changed files). Rankers, all with the changed functions' own file first: **B** (baseline) same file, then call distance, then size; **S** same file, then call distance, then **same directory (category 4)**, then size; **G** same file, then call distance, then **directory category (graded)**, then size. (Same-directory only as a tie-break within a call distance, so every call-linked candidate stays ahead of every unlinked one in the same class.) Data: DPDK and Mesa (trailer-named pairs, changed functions found by tree-sitter in both versions of each commit) and the held-out repositories of the gate (libgit2, redis, libxml2, sphinx, scapy, sqlmap, prometheus; blame-based causes); function top 20 and top 100, file top 10 and top 20; "other-file repairs only" counts only repaired functions and files outside the files of the changed functions (the case the feature is for).
- **SD1.** S raises the function top-20 share by at least 3 percentage points over B in each of: DPDK, Mesa, and each of the C, Python and Go held-out groups pooled.
- **SD2.** G is at least as good as S (its top 20 at most 0.5 points lower) in each of those five datasets.
- **SD3.** For repairs in **other files only**, the function top-20 rises by at least 5 points and the file top-10 by at least 5 points (S over B), in each dataset.
- **SD4.** No loss for repairs in the changed files: the function top-20 for the same-file repairs does not fall by more than 1 point (S against B).
**Would surprise:** a gain under 1 point in any dataset (then directory proximity adds nothing the same-file and call-distance rankers do not already have).

#### Same directory as a ranking feature: results (2026-11-18; `same_directory_output.txt`)
B = same file, call distance, size (the validated ranking); S = the same with "same directory" as a tie-break within each call distance; G = graded directory category as the tie-break. DPDK and Mesa: 4,000 trailer pairs each sampled (1,429 and 1,601 ranked); held-out repositories: blame pairs.
| dataset (pairs) | function top 20 B / S | function top 100, other-file repairs only B / S | **files top 10, other-file repairs only B / S** | files top 20, other-file only B / S | files top 10, all repairs B / S |
|---|---|---|---|---|---|
| DPDK (1,429) | 49.4 / 49.7% | 20.0 / **39.4%** | 51.7 / **63.0%** | 58.5 / **77.3%** | 83.2 / 87.2% |
| Mesa (1,601) | 40.8 / 41.0% | 15.0 / 22.0% | 30.9 / **37.3%** | 39.3 / **51.3%** | 67.2 / 70.0% |
| C held-out (1,604) | 47.3 / 47.3% | 22.7 / 24.1% | 51.0 / 52.7% | 75.7 / 77.7% | 83.6 / 84.3% |
| Python held-out (1,513) | 35.7 / **38.1%** | 30.6 / 33.0% | 34.0 / 38.6% | 50.5 / 52.8% | 60.9 / 64.0% |
| Go held-out (380) | 42.4 / 43.5% | 24.4 / **35.1%** | 42.4 / 46.6% | 59.4 / **69.8%** | 70.3 / 72.4% |
G (graded) equals S within 0.1 point everywhere at function level and within 1 to 3 points at file level (Go file top 10: S 46.6%, G 44.9%). **Repairs in the changed files themselves:** unchanged (S = B in every dataset). Function top 20 for repairs in **other files only** (B / S): DPDK 3.6 / 4.6%, Mesa 2.9 / 3.4%, C 2.9 / 3.0%, Python 7.3 / 10.8%, Go 4.5 / 6.3%. (The spot check on the mock-up's pair is not in the sampled pairs.)
| hypothesis | verdict |
|---|---|
| SD1 S raises the function top 20 by at least 3 points in every dataset | **not supported**: +0.4, +0.2, +0.0, +2.4, +1.1 |
| SD2 G at least as good as S | **supported** (differences -0.1 to +0.0) |
| SD3 other-file repairs: function top 20 and file top 10 each up by at least 5 points in every dataset | **not supported**: function top 20 +1.0, +0.5, +0.1, +3.6, +1.7; file top 10 **+11.3**, **+6.4**, +1.7, +4.6, +4.2 |
| SD4 no loss for same-file repairs | **supported** (exactly unchanged) |
Surprise bar (a gain under 1 point in any dataset): **met** for the function top 20 in four of five datasets.
**Reading.** **Directory proximity helps files, not the top 20 functions.** A repaired function in a sibling file is usually far down any function list (a directory holds hundreds of functions with no call link to the change), so the function top 20 barely moves (+0.0 to +2.4); but ranked as **files**, the sibling file rises sharply: for repairs in other files the top-10 files contain a repaired file 63% instead of 52% (DPDK), 37% instead of 31% (Mesa), 47% instead of 42% (Go), 39% instead of 34% (Python), and 53% instead of 51% (C held-out). The top 100 functions for other-file repairs doubles in DPDK (20% to 39%) and rises by 8 to 11 points in Mesa and Go. Nothing is lost for repairs in the changed files. **Design consequence:** use the directory as a tie-break in the **file ranking** (changed file, then call distance, then same directory, then size) and keep the function list as it is; a suspect file can carry the reason "same directory as X's file". The graded version adds nothing over the binary one.
**Caveats.** Trailer pairs sampled to 4,000 per repository; blame-based pairs for held-out repositories; C held-out repositories are small, so file top-10 and top-20 are high for every ranker; the gain is largest where repositories are organised in directories by driver or module (DPDK, Mesa) and smallest in flat projects (libgit2, redis).

## Reverse triage: from the place a bug was repaired to the change that caused it (hypotheses fixed 2026-11-19 before running; `tools/sensor/triage_reverse.py`)
The ranking so far runs forward (a change, then where the repair lands). Incident triage runs backwards: **a failure is located in a function; which recent change caused it?** Test on pairs where the **author named the cause** (DPDK and Mesa `Fixes:` trailers, independent of line blame), 1,500 pairs sampled per repository. **Failure site** = the functions the fix edited (tree-sitter, both versions; a proxy: a real report may point elsewhere). **Candidates** = every non-merge commit in the 730 days before the fix that changed 1 to 60 C/H functions (hunk-header functions, the same representation for the true cause and the others); the pair is kept only if the true cause is among them. **Call graph** of the nearest quarterly scan at or before the fix. **Rankers** (each ties broken by recency, most recent first): **REC** recency alone (the usual habit); **SIZE** number of changed functions, then recency; **FILE** touches a file of the failure site; **BLAME** changed one of the failure functions; **N1** the neighbourhood ranking: changed a failure function, then same file, then call distance (1, 2, 3 calls either way), then same directory; **N1b** the same without the directory step. Metric: the rank of the true cause (top 1, top 5, top 20, mean reciprocal rank), over all pairs and over the pairs where the true cause did **not** change a failure function ("cause elsewhere": the case blame cannot solve).
- **RT1.** N1 puts the true cause in the top 20 for at least 50% of all pairs, pooled over the two repositories.
- **RT2.** On the "cause elsewhere" pairs, N1's top 20 is at least 20%, against at most 5% for recency alone.
- **RT3.** On the "cause elsewhere" pairs, N1b's top 20 is at least 5 points above FILE's (call distance adds to the file).
- **RT4.** On the "cause elsewhere" pairs, N1's top 20 is at least 2 points above N1b's (the directory step adds).
- **RT5.** Recency alone gets the true cause into the top 20 for at most 5% of all pairs (the candidate lists are long: thousands).
**Would surprise (the neighbourhood is no help backwards):** on "cause elsewhere" pairs N1's top 20 within 1 point of FILE's.

#### Reverse triage: results (2026-11-19; `triage_reverse_output.txt`; DPDK and Mesa trailer-named pairs, 1,500 sampled per repository; ranked: DPDK 600, Mesa 968; the rest dropped: true cause older than 730 days or without functions 505 and 255, no failure function 205 and 124, failure function not in the graph, no earlier scan; candidates per fix: thousands)
Rank of the true cause among the commits of the 730 days before the fix, pooled (1,568 pairs):
| ranker | top 1 | top 5 | top 20 | MRR |
|---|---|---|---|---|
| REC recency alone | 0.3% | 0.8% | **3.1%** | 0.009 |
| SIZE | 0.0% | 0.0% | 0.8% | 0.002 |
| FILE touches a failure file | 14.9% | 35.3% | 59.1% | 0.252 |
| BLAME changed a failure function | 26.0% | 46.4% | 55.5% | 0.349 |
| N1b neighbourhood without directory | 28.7% | 55.9% | 73.1% | 0.409 |
| **N1 neighbourhood** | **28.7%** | **56.4%** | **74.2%** | **0.411** |
**Cause elsewhere** (the true cause did not change a failure function: 681 pairs, 43%): REC 0.0 / 0.1 / **1.8%**; FILE 5.3 / 17.3 / **35.1%**; BLAME 0.0 / 0.0 / 1.2%; N1b 5.7 / 22.0 / 41.7%; **N1 5.7 / 23.1 / 44.2%** (top 1, top 5, top 20). By repository, N1 top 20: DPDK all 79.0%, cause elsewhere 55.8% (REC 0.0%, FILE 40.4%); Mesa 71.2% and 36.8% (REC 2.9%, FILE 31.7%).
| hypothesis | verdict |
|---|---|
| RT1 N1 top 20 at least 50%, all pairs | **supported**: 74.2% |
| RT2 cause elsewhere: N1 top 20 at least 20%, recency at most 5% | **supported**: 44.2% and 1.8% |
| RT3 N1b at least 5 points above FILE (cause elsewhere) | **supported**: +6.6 |
| RT4 N1 at least 2 points above N1b (cause elsewhere) | **supported**: +2.5 |
| RT5 recency alone at most 5% (all pairs) | **supported**: 3.1% |
Surprise bar (N1 within 1 point of FILE, cause elsewhere): not met.
**Reading.** Searched backwards, the neighbourhood ranks the causing change into the top 20 of thousands of recent commits for **74% of repairs** (recency: 3%), and for **44% of the repairs whose cause did not change a failure function**, the case line blame cannot solve (blame: 1%; file overlap alone: 35%; the call graph adds 6.6 points, the directory 2.5). The same ingredients as the forward list work in reverse. 57% of the causes changed a failure function (blame's territory); even there the neighbourhood ranking is better in the top 20 (the same function is touched by many commits in two years, and the call-graph tiers order them). Top 1 is modest (28.7%): this narrows a search, it does not name the culprit. **Caveats:** the failure site is the **fix's** edited functions, a proxy (a real report points at a symptom, often elsewhere); only causes within 730 days (about a third dropped in DPDK); hunk-header function sets (unverified) for the candidates; two C repositories; trailer-named causes; the candidates are commits that changed 1 to 60 functions.

## Three extensions of the reverse triage (hypotheses fixed 2026-11-19 before running; `tools/sensor/triage_sites.py`, `tools/sensor/agent_context.py`)
**1. A realistic symptom site.** The first reverse-triage test used all the functions the fix edited as the failure site, which a real report would not know. Same pairs, candidates and rankers (REC, FILE, BLAME, N1), with the site replaced by: **S1** the single first function the fix edited (file path order, then source order); **S2** a single edited function drawn at random; **S3** a **caller** (one call away) of an edited function that the fix did not edit (the symptom surfaces upstream of the fault; only fixes whose edited functions have such callers); **S4** a function named in the fix commit's subject (an identifier that is a function of the graph; only fixes with one). The ranking is read against the **truth the trailer names**.
- **SY1.** With one edited function as the site (S1 and S2), N1 still puts the true cause in the top 20 for at least 55% of pairs.
- **SY2.** With a caller as the site (S3), N1's top 20 is at least 25% and at least 5 points above FILE's.
- **SY3.** With the function named in the subject (S4), N1's top 20 is at least 50%.
- **SY4.** Difficulty ordering by N1's top 20: S3 (caller) is the lowest of the four sites.
**2. Does it shorten a bisect?** A bisect over the time-ordered commits of the 730 days before the fix finds the cause in about log2(N) tests (N all non-merge commits in the window). A **prior-weighted bisect** instead splits the candidates (the commits that changed C functions) so that each test halves the prior probability mass; the prior comes from a ranker's rank of each candidate through the **rank-to-probability curve fitted on one half of the pairs** (the empirical distribution of the true cause's rank, log-binned, smoothed) and evaluated on the other half (and the reverse). Steps are counted until one candidate remains, for the whole-fix site and for S1. Priors: uniform over the candidates, recency, FILE, N1.
- **BS1.** N1-weighted bisect needs on average at least 3 fewer tests than the classic bisect over all commits.
- **BS2.** N1-weighted bisect needs at least 0.5 fewer tests than FILE-weighted on average.
- **BS3.** For at least 30% of pairs N1-weighted bisect needs at most 5 tests.
**3. Context for a coding agent: the other functions a fix edits.** Given the **first function a fix edits** as the starting point, rank the functions (and files) of the call graph for the **other functions the same fix edits** (fixes that edit at least 2 functions, verified by tree-sitter): the "files missing from your diff" and "context an agent should read" problem. Rankers: SIZE; SAMEFILE; **N** (same file, call distance, same directory, size); **LEX** (shared words of the function names, split on underscores and capitals, then size); **N+LEX** (reciprocal-rank fusion, parameter-free). Candidates: all functions of the nearest scan at or before the fix; DPDK and Mesa (trailer pairs) and the held-out C repositories of the gate (blame pairs). Metric: share of the other edited functions found in the top 20 (recall at 20), share of fixes with at least one found in the top 20, and files: at least one other edited file in the top 5 files.
- **AC1.** N's recall at 20 is at least 50% (pooled over fixes).
- **AC2.** N beats LEX by at least 15 points of recall at 20.
- **AC3.** For fixes that edit more than one file, at least one other edited file is among N's top 5 files for at least 60% of them.
**Would surprise (the neighbourhood does not help the symptom-site or agent problems):** SY1 below 40%, or AC2 below 5 points.

#### Reverse triage extensions: results (2026-11-19; `triage_sites_output.txt`, `agent_context_output.txt`; DPDK and Mesa, 600 pairs sampled each for sites and bisect; agent context 3,827 fixes in 9 repositories)
**Symptom sites** (true cause in the top 20, pooled; REC / FILE / BLAME / N1): whole fix 2.8 / 59.9 / 56.3 / **74.8%**; S1 first edited function 2.8 / 58.6 / 48.9 / **71.8%**; S2 random edited function 2.8 / 58.7 / 48.9 / **72.3%**; S3 a caller of an edited function (457 pairs) 3.1 / 45.3 / 20.1 / **59.1%**; S4 function named in the subject (192 pairs) 2.6 / 9.9 / 6.8 / **9.9%**.
**Bisect** (steps to isolate the cause; classic bisect over all commits of the window 14.7 on average): uniform over candidates 13.7; recency 14.7; FILE-weighted 8.4; BLAME-weighted 9.4; **N1-weighted 6.4** (median 5; at most 5 tests for 53%); with the single first function as the site 6.7 (50%). Priors fitted on one half of the pairs, evaluated on the other (both ways).
**Agent context** (other functions a fix edits, given the first one; recall at 20, pooled): SIZE 8.1%, SAMEFILE 40.5%, **N 42.7%**, LEX 27.8%, N+LEX 43.9%; fixes with at least one other function found: N 56.6%, N+LEX 60.2%; other edited file in the top 5 files: N 48.6% (size alone 28.4%). By repository N ranges 36% to 51%.
| hypothesis | verdict |
|---|---|
| SY1 one edited function as the site, N1 top 20 at least 55% | **supported**: 71.8% and 72.3% |
| SY2 caller as the site, N1 at least 25% and 5 points over FILE | **supported**: 59.1% against 45.3% |
| SY3 function named in the subject, N1 at least 50% | **not supported**: 9.9% |
| SY4 the caller site is the hardest | **not supported** (S4 is lowest, by far) |
| BS1 N1-weighted bisect at least 3 tests fewer than classic | **supported**: 8.3 fewer (6.4 against 14.7) |
| BS2 at least 0.5 fewer than FILE-weighted | **supported**: 2.0 fewer |
| BS3 at most 5 tests for at least 30% | **supported**: 53% |
| AC1 N recall at 20 at least 50% | **not supported**: 42.7% |
| AC2 N at least 15 points above LEX | **not supported, by 0.1 point**: +14.9 |
| AC3 other edited file in the top 5 files for at least 60% | **not supported**: 48.6% |
Surprise bar (SY1 below 40% or AC2 below 5): not met.
**Reading.** (1) **The reverse ranking survives realistic sites:** from one edited function it still finds the cause in the top 20 for 72%, and from a function one call upstream (a symptom surfacing away from the fault) for 59%, 14 points above file overlap and three times what blame manages. (2) **Used to guide a bisect it roughly halves the tests** (6.4 against 14.7; half of the searches need 5 or fewer), the most practical number so far. It needs candidate priors only, not any test oracle. (3) **S4 is a failed test of mine, not evidence about the method:** the identifiers in a subject line that matched a graph function are mostly generic words (`init`, `free`, `check`), so the "site" is usually a wrong function (FILE also gets 9.9%); a proper test needs the real bug report. (4) **Agent context is a weaker result:** given one function of a fix, the other functions it edits are in the top 20 at 43% (56.6% find at least one); the call graph helps modestly over same-file (+2 points) and name-word overlap is far behind alone (27.8%) but adds when fused (+1.2). Three of my predictions missed (AC1, AC2 by 0.1, AC3), so for retrieval-for-agents the honest claim is "about 4 in 10 of the functions to co-edit are in a 20-item list", from the first function alone. **Caveats:** bisect priors are fitted on the same two repositories (cross-fitted within them); the bisect counts probes of a perfect oracle on commits that touch C functions (commits that do not are excluded from candidates, which flatters all weighted rankers equally but not the classic count over all commits); two repositories for the triage tests; agent context uses fix-edited functions as truth (co-edits, not necessarily needed context).

## Test selection as a call-graph problem (hypotheses fixed 2026-11-19 before running; `tools/sensor/test_selection.py`)
Tests are functions in the call graph too (they call the code they exercise). Question: given the **source functions a fix edits**, can the neighbourhood rank the **test files** the same fix touches (the tests its author thought covered the bug)? Proxy truth, not test outcomes: the test files the fix commit edited or added (only those that exist in the graph of the nearest earlier scan). Test file = path containing a `test`, `tests`, `testing`, `t/` or `spec` directory segment, or a file name starting `test_` or ending `_test`. Repositories: DPDK and Mesa (trailer pairs), libgit2, redis, libxml2 (blame pairs). Fixes kept: at least one source function edited that is in the graph, at least one touched test file that exists in the earlier graph. Rankers over the test files of that graph: **SIZE** lines of code; **DIR** longest shared path prefix with the edited source files, then size; **NAME** words shared between the edited source file names and the test file path (idf), then size; **N** nearest call distance (1, 2, 3 calls either way) from the edited functions to any function of the test file, then DIR, then size; **N+NAME** reciprocal-rank fusion. Metrics: share of fixes with a touched test file in the top 1, 5, 10 test files; and the **run budget**: the share of all test files that must be run, on average, before the first touched one is reached.
- **TS1.** N has a touched test file in its top 5 for at least 40% of fixes, pooled, against at most 10% for SIZE.
- **TS2.** N's top 5 is at least 5 points above DIR's (the call graph adds to path proximity).
- **TS3.** N's mean run budget is at most 15% of the test files (random: 50%).
- **TS4.** N+NAME's top 5 is at least 3 points above N's.
- **TS5.** In at least 4 of the 5 repositories N's top 5 beats SIZE's by at least 15 points.
**Would surprise (the call graph does not reach the tests):** N's top 5 within 2 points of DIR's.
**Known limit stated in advance:** truth is where authors put tests, not what fails; macro registries and test harnesses hide call edges.

#### Test selection: results (2026-11-19; `test_selection_output.txt`; 305 fixes: dpdk 24, mesa 11, libgit2 108, redis 155, libxml2 7; median 32 to 377 test files per repository)
Pooled, a touched test file among the first 1 / 5 / 10 test files, and run budget (share of all test files run before the first touched one): SIZE 3.9 / 16.7 / 25.2%, 34.9%; DIR 6.2 / 17.7 / 27.2%, 34.2%; **NAME 25.9 / 48.9 / 56.7%, 20.7%**; N 20.3 / 35.4 / 43.9%, 28.1%; N+NAME 22.3 / 33.8 / 43.0%, 21.2%. Top 5 by repository (SIZE / DIR / NAME / N / N+NAME): dpdk 8 / 4 / 88 / 75 / 79; mesa 9 / 64 / 73 / 73 / 82; libgit2 15 / 15 / 51 / 48 / 43; redis 19 / 17 / 40 / 17 / 17; libxml2 43 / 43 / 43 / 43 / 43.
| hypothesis | verdict |
|---|---|
| TS1 N top 5 at least 40%, SIZE at most 10% | **not supported**: 35.4% and 16.7% |
| TS2 N at least 5 points above DIR | **supported**: +17.7 |
| TS3 N run budget at most 15% | **not supported**: 28.1% |
| TS4 N+NAME at least 3 points above N | **not supported**: -1.6 |
| TS5 N beats SIZE by 15 points in 4 of 5 repositories | **not supported**: 3 of 5 (redis and libxml2 fail) |
Surprise bar (N within 2 points of DIR): not met.
**Reading.** The call graph does reach the tests (+17.7 points over path proximity, 2 to 5 times random), but a plain **file-name match between the edited source file and the test file (NAME) beats it** (48.9% against 35.4% in the top 5) and adding the graph to NAME does not help (fusion 33.8%). Redis shows the limit: its call graph never reaches the test files that fixes touch (N equals DIR), so the graph signal there is nil. **Caveats:** three repositories have 7 to 24 fixes; truth is the test files an author touched, not test failures; only test files that exist in the earlier C graph count (Tcl, Python and shell test suites are outside it); fixes that add a new test file are excluded because the file is not in the earlier graph. **Position:** for choosing tests, naming convention carries most of the signal; the call graph is a weaker second source and is worth including only where tests call the code directly (DPDK, Mesa, libgit2).

## Do the call graphs see the tests? An audit, and tests as a signal of change (hypotheses fixed 2026-11-19 before running; `tools/sensor/test_graph_audit.py`)
Prompted by the weak test-selection result (redis: the graph never reached the test files). **Audit** (latest quarterly scan of each repository: dpdk, mesa, libgit2, redis, libxml2 in C; scapy and sphinx in Python; prometheus in Go; test file = the same path rule as the test-selection study): the share of test files with at least one function that has a call edge into non-test code ("wired"), counting only confident edges (as in every result so far) and counting ambiguous edges too (`BLAST_MAXC=100`); and the share of non-test functions within 3 calls of any test function ("test reach"). **Tests as a signal of change** (same five C repositories, fixes as in the test-selection study, plus all fixes of those samples for the descriptive share): TE1 the share of fixes that touch a test file; TE2 for fixes that touch both source functions and a test file in the earlier graph, the share where a touched test file has a function within 3 calls of an edited source function; TE3 in the reverse triage (DPDK and Mesa trailer pairs, fixes that touch a test file) a ranker **N1T** = N1 with a tier "the candidate commit touched a test file the fix touched" placed just below "changed a failure function" against N1 alone, rank of the true cause in the top 20.
- **TA1.** In at least 3 of the 5 C repositories at least 50% of test files are wired (confident edges).
- **TA2.** Admitting ambiguous edges raises the wired share by at least 10 points in at least 2 repositories.
- **TA3.** Redis wired share below 20%.
- **TA4.** In the median repository at most 50% of non-test functions are within 3 calls of a test function (large parts of each project are not graph-reachable from the tests).
- **TE1.** At least 30% of fixes touch a test file, pooled.
- **TE2.** At least 50% of the fixes with both have a touched test file within 3 calls of an edited source function.
- **TE3.** N1T is at least 3 points above N1 in the top 20 on those pairs.
**Would surprise (the tests are as visible as the source):** TA1 in all 5 repositories with at least 80% wired, and TA2 nowhere.

#### Test-graph audit and tests as a signal: results (2026-11-19; `test_graph_audit_output.txt`)
**Audit** (latest scan; test files / test functions; wired = share of test files with an edge into non-test code, confident edges / all edges; test reach = share of non-test functions within 3 calls of any test function): dpdk 301 / 4,843, 86.4 / 86.4%, reach **5.4%**; mesa 333 / 3,932, 80.5 / 85.3%, **4.0%**; libgit2 477 / 5,234, 95.0 / 95.0%, **38.9%**; redis 369 / 2,500, 32.8 / 32.8%, **7.7%**; libxml2 34 / 88, 8.8 / 8.8%, **0.4%**; scapy 4 / 36, 75 / 75%, 0.2%; sphinx 205 / 2,069, 53.7 / 61.5%, 10.5%; prometheus 299 / 3,635, 86.6 / 97.0%, 27.2%.
**Signal of change:** fixes touching a test file: dpdk 5% (132 of 2,419), mesa 1% (21 of 2,487), libgit2 15%, redis 17%, libxml2 11%; pooled 8.5%. Of the 307 fixes that edit a source function and a test file present in the graph, a touched test file is within 3 calls of an edited source function for 25.7% (dpdk 75%, mesa 36%, libgit2 51%, redis 1%, libxml2 0%). Reverse triage on fixes that touch a test file: only 9 pairs (dpdk 5, mesa 4); N1T 80% against N1 60% in dpdk, equal in mesa.
| hypothesis | verdict |
|---|---|
| TA1 at least 3 of 5 C repositories with at least 50% of test files wired | **supported**: 3 of 5 (dpdk, mesa, libgit2), redis 33%, libxml2 9% |
| TA2 ambiguous edges add at least 10 points in 2 repositories | **not supported**: 1 (prometheus +10.4; mesa +4.8, sphinx +7.8) |
| TA3 redis wired below 20% | **not supported**: 32.8% |
| TA4 median test reach at most 50% | **supported**: 6.5% (far lower than predicted) |
| TE1 at least 30% of fixes touch a test file | **not supported**: 8.5% |
| TE2 touched test file within 3 calls for at least 50% | **not supported**: 25.7% |
| TE3 N1T at least 3 points above N1 | **inconclusive**: +11.1 points on 9 pairs (the script's "supported" is not a verdict) |
Surprise bar (all 5 at least 80% wired, ambiguous edges nowhere): not met.
**Reading.** (1) **Most test files are wired but the tests reach little of the code**: 4 to 8% of non-test functions are within 3 calls of a test function in dpdk, mesa and redis (libgit2 39%, prometheus 27%); the call graph holds the tests but its edges mostly stop at the API boundary, so a fix deep in the source is rarely within 3 calls of the test the author touched (25.7%; dpdk 75% where the tests call the internals, redis 1%). (2) **Ambiguous edges are not the cure** (+10 points in one repository). The gap is missing or deeper edges, not unresolved targets. (3) **Test edits are rare signals in these projects** (8.5% of fixes; mesa 1%, mostly because fixes ship without tests or tests live in other languages and harnesses), too rare for a general ranking feature; the one data point (N1T +20 in dpdk on 5 pairs) is anecdote. (4) **Gaps in my audit**: libxml2's tests are mostly top-level files my path rule does not match (34 test files found), so its 8.8% and 0.4% understate its tests; the 3-call reach was not repeated at larger distances. **Next:** measure test reach at 5 and 10 calls to see whether the tests connect at all, and test whether test-reachability separates repaired functions from size-matched peers.

## Test reach: how deep do the tests connect, and are repaired functions less test-reachable? (hypotheses fixed 2026-11-19 before running; `tools/sensor/test_reach.py`)
**Depth.** Share of non-test functions that a test function reaches through calls within 1, 2, 3, 5, 10 calls (latest scan; confident edges), dpdk, mesa, libgit2, redis, libxml2, prometheus, sphinx. **Repairs.** For every fix of the study samples (as in the test-selection study), each source function the fix edited that exists in the nearest earlier graph; for each, whether a test reaches it within k calls (k = 3, 5, 10), against what is expected for functions of the same size decile in the same graph (non-test, any function of the decile, so the comparison holds size fixed). Observed minus expected share, per repository, with a 95% interval from resampling fixes (1,000 draws).
- **TR1.** In dpdk, mesa and redis, the 10-call share is at least twice the 3-call share (the tests do connect with depth).
- **TR2.** At 5 calls, repaired functions are **less** test-reachable than size-matched functions in at least 5 of the 7 repositories (difference negative with the interval excluding 0 in at least 4).
- **TR3.** Pooled over the repositories, repaired functions are reached at most 90% as often as expected at 5 calls.
**Would surprise (the opposite):** repaired functions more test-reachable than expected in at least 5 of 7 (hot code is both more exercised and more repaired).

#### Test reach: results (2026-11-19; `test_reach_output.txt`; the first run crashed on an empty early prometheus graph; guard added, rerun unchanged otherwise)
**Depth** (share of non-test functions a test reaches within 1 / 2 / 3 / 5 / 10 calls): dpdk 2.9 / 4.5 / 5.4 / 5.9 / **6.3%**; mesa 1.4 / 2.7 / 4.0 / 5.7 / **7.1%**; libgit2 19.1 / 31.4 / 38.9 / 45.2 / **47.9%**; redis 3.3 / 5.6 / 7.7 / 10.8 / **13.0%**; libxml2 0.1 / 0.4 / 0.4 / 0.4 / 0.4%; prometheus 16.6 / 24.0 / 27.2 / 29.5 / **29.8%**; sphinx 5.8 / 9.5 / 10.5 / 11.6 / **11.8%**.
**Repaired against size-matched, 5 calls** (observed minus expected, 95% interval): dpdk +0.3 [-0.9, +1.7]; mesa +0.0 [-0.9, +1.2]; libgit2 **+5.0** [+2.5, +7.6]; redis **-9.1** [-9.5, -8.6] (0.2% observed against 9.3%); libxml2 0 (no test reach at all); prometheus -2.2 [-5.2, +0.9]; sphinx **+5.9** [+4.0, +8.0].
| hypothesis | verdict |
|---|---|
| TR1 10-call share at least twice the 3-call share in dpdk, mesa, redis | **not supported**: 6.3 against 5.4, 7.1 against 4.0 (1.8 times), 13.0 against 7.7 (1.7 times); reach plateaus by about 5 calls |
| TR2 repaired functions less reachable in at least 5 of 7 (4 with intervals excluding 0) | **not supported**: 3 of 7, 2 with intervals excluding 0 |
| TR3 pooled observed/expected at most 0.90 | **not supported**: 0.99 |
Surprise bar (more reachable in at least 5 of 7): not met (4 of 7).
**Reading.** (1) **Depth is not what limits the tests**: reach saturates within about 5 calls (dpdk 5.9 against 6.3% at 10), so the unreached 90+% of code in dpdk, mesa, redis and sphinx is not linked by any path in the graph from a test function; what is missing is edges, the connection from tests to code (registries, harness scripts, other-language suites, test files outside my path rule), not distance. (2) **Test reachability does not separate repaired from unrepaired functions of the same size**, pooled (0.99): none in dpdk and mesa; **opposite directions elsewhere**: libgit2 and sphinx repair the *more* test-reachable functions (+5 to +6 points), redis the far *less* (its C unit tests reach only utility code, not the server core where fixes land). **Not a general sensor from the current graph**; it is a per-repository fact. libxml2 is the extreme (its tests are outside my test-path rule), so it has no information. **Position:** to learn whether tests matter to repairs we must first extend the graph (harness and registry edges, other-language suites) and the test-path rule, then rerun this test and the test-selection test; the present graph cannot answer it.

#### Why tests do not reach the code in one call: an unregistered look at the scan database (2026-11-19, exploratory; dpdk and redis, latest scan)
Tests do make direct calls: dpdk's test files have 14,928 call records, 99% resolved to a target (9,263 into non-test code, 5,499 into other test code); the scanner records no loss there. What is small is the **share of the project** they call: tests call 1,649 of dpdk's 55,535 non-test functions directly (3.0%), 374 of redis's 11,691 (3.2%). By directory: dpdk `drivers/net` 31,453 functions (57% of all non-test code) with 21 called by tests (0.1%); `lib/eal` 15.8%; redis `deps/jemalloc` 15.2%, `src/server.c` and `src/module.c` 0. The graph holds 54 `reference`-kind edges in dpdk (function-pointer references) and 8 in redis. Reading: the unreached code is mostly **behind function-pointer tables (driver ops structs) or behind a network protocol (redis's Tcl suite)**, not behind a missing 1-hop call. The next edge class to build is struct-initializer and function-pointer assignment references.

## Function-pointer edges: does the graph's blindness change what we found? (hypotheses fixed 2026-11-19 before building; `tools/sensor/fnptr_edges.py`, `tools/sensor/fnptr_eval.py`)
**The change.** Add one edge class to the call graph: **indirect calls through a named struct field**. Registrations are collected from designated initializers (`.field = func`, `.field = &func`) and assignments (`x->field = func`); each call through a field (`p->field(...)`, `p.field(...)`) in function G gets an edge G to every function registered under that field name (the dispatch is by field name only, no type information; fields with more than 400 registered targets are dropped, positional initializers and calls through bare pointer variables are not handled). The extractor parses C files with tree-sitter at the scanned commit; the functions must exist in the scan graph; a name defined in several files resolves to the definition in the same file or, failing that, is skipped. Two builds of the graph per snapshot: **current** (as in every result so far) and **current + function-pointer edges**. **Stage 1** (DPDK, latest quarterly scan): edge count, correctness proxy, test reach. **Stage 2** (only if EP2 holds; DPDK, all scans): rerun the reverse triage (N1, top 20, trailer pairs) and the test reach under the extended graph.
- **EP1.** The new edges raise DPDK's test reach within 3 calls (non-test functions reached by any test function) from 5.4% to at least 20%.
- **EP2.** Correctness proxy: for at least 80% of new edges the number of arguments at the call site equals the registered function's parameter count (random pair of unrelated functions: about 20%, measured in the same run); and in a random hand-checked sample of 30 edges at least 24 are plausible dispatch targets (the field is a callback slot the function is registered in; judged on the registration line and the call line, both shown in the output).
- **EP3.** The extension adds at least 5,000 edges and at least 3% of the non-test functions gain a first caller path they lacked.
- **EP4 (stage 2).** The reverse triage's N1 top 20 on DPDK moves by less than 3 points in either direction (the repair-radius findings are robust to this blindness).
**Would surprise:** EP2 failing (field-name dispatch is too coarse to trust), or EP4 moving by 5 points or more.

#### Function-pointer edges: stage 1 results (2026-11-19; `fnptr_stage1_output.txt`; DPDK, latest scan, 5,333 C files, built in 3 seconds)
The extractor found 1,993 registered field names (14,132 registrations), dropped none for exceeding 400 targets, and produced **59,362 new edges**. **Correctness proxy:** the argument count at the call site equals the target's parameter count for **73.0%** of the edges (random call site against random function: 23.0%). **Hand-checked sample of 30 random edges** (registration line and call line read in the output; judged as: the call reaches a field of the same struct type that the function was registered in): **13 plausible, 17 not**. The plausible ones are the ethdev/dmadev `dev_ops` slots (e.g. `dev->dev_ops->mtu_set`, `->fill`); the wrong ones join **unrelated structs that share a field name** (`remove`, `cb`, `fn`, `init`, `read_reg`, `write_reg`, `dev_stop`): an ixgbe PHY call joined to e1000 or txgbe functions, a cryptodev `dev_stop` joined to a compress driver, an iavf table entry joined to an i40e function. **Test reach with the edges** (non-test functions within 1 / 2 / 3 / 5 / 10 calls of a test function): 3.0 / 12.2 / 25.1 / 48.4 / 66.2% (without: 2.9 / 4.5 / 5.4 / 5.9 / 6.3%).
| hypothesis | verdict |
|---|---|
| EP1 test reach within 3 calls at least 20% | **supported numerically**: 25.1% (from 5.4%), but see EP2: part of it is false edges |
| EP2 at least 80% arity match and at least 24 of 30 hand-checked plausible | **not supported**: 73.0% and 13 of 30 |
| EP3 at least 5,000 new edges | **supported**: 59,362 (the "3% gain a first path" half was not measured) |
| EP4 (stage 2) triage robust to the edges | **not run**: stage 2 was conditional on EP2 |
Surprise bar (EP2 failing: field-name dispatch too coarse to trust): **met**.
**Reading.** The blindness is real and large: indirect dispatch through ops tables is the route from the generic API into 31,000 driver functions, and a field-name rule recovers a lot of it quickly. But **matching by field name alone over-connects**: fewer than half of the sampled edges are real, because many unrelated structs reuse names like `init`, `remove`, `read_reg`. So the 25.1% test reach is an upper bound, not a measurement, and I did not rerun any earlier result on these edges. **Fix needed before stage 2:** resolve the struct type of the called field's base (`dev->dev_ops` is `struct eth_dev_ops`, `hw->phy.ops` is `struct ixgbe_phy_operations`) so registrations and calls match on (struct type, field); that is a type-resolution step, not a name lookup. The same-struct-type rule would also cut driver-to-driver crossovers.

## Function-pointer edges, type-resolved (hypotheses fixed 2026-11-19 before building; `tools/sensor/fnptr_typed.py`)
Stage 1 matched registrations and calls by field name and failed (EP2). This version matches on **(struct type, field)**. Pass 1 over all C and header files of the scanned commit: struct definitions with the declared type of each member, and typedef aliases. Pass 2: every registration (a designated initializer `.field = func` whose enclosing initializer has a known struct type, found from the declaration, array elements and nested designators; an assignment `expr->field = func`) and every indirect call `expr->field(...)` is given the struct type of `expr` by a static type lookup: identifier (parameters, local and file-scope declarations of the same file), member chain (`hw->phy.ops`), array element, dereference, parentheses; anything else (casts, call results, macros) is left unresolved and produces **no edge**. An edge joins a calling function to every function registered under the same (type, field). No other change. DPDK, latest scan.
- **TP1.** The argument count at the call equals the target's parameter count for at least 85% of the edges (stage 1: 73.0%; random 23%).
- **TP2.** In a random sample of 30 edges at least 26 are correct dispatch targets (the registration and the call concern the same struct type and the call site plausibly reaches that slot), judged on the registration and call lines printed in the output (stage 1: 13 of 30).
- **TP3.** At least 10,000 edges, and DPDK's test reach within 3 calls at least 12% (stage 1: 25.1%, no precision).
- **TP4.** At least 60% of the indirect field calls that have at least one registration under the field name get a resolved struct type (the rest are lost, not guessed).
- **Stage 2** (only if TP2 holds): reverse triage (N1, top 20, trailer pairs) on DPDK under the extended graph moves by less than 3 points in either direction; test reach and test-selection reported.
**Would surprise:** TP4 below 40% (static typing too weak without the compiler), or TP2 below 20 of 30.

#### Function-pointer edges, type-resolved: results (2026-11-19; `fnptr_typed_output.txt`, `triage_reverse_fnptr_output.txt`; DPDK; built in 5 seconds per scan, 41 scans)
Latest scan: 5,333 C files, 11,689 struct types, 563 typedefs; 14,131 registrations of which 13,222 typed (94%); 5,436 indirect field calls, 4,764 with a registered field name, of those 3,770 typed (**79%**); **12,016 new edges** (stage 1 by field name: 59,362). **Argument count equals parameter count for 100%** of the edges (random 22%). **Hand-checked sample of 30:** all 30 are dispatches through the same struct type the function was registered in (`eth_dev_ops.rx_queue_release`, `rte_bus.scan`, `rte_pci_driver.remove`, the e1000 and ixgbe `mac.ops` and `phy.ops` slots, `rtl_hw_ops`, `sfc_flow_item.parse`); **one is imprecise at the level of the table instance** (an iavf call through `ci_tx_path_info.pkt_burst` is joined to an i40e function: type-correct, but the iavf table never holds it). Largest edge sets: `e1000_phy_operations.read_reg` 792 and `write_reg` 714 (any chip's implementation of the slot: the dispatch is real, the fan-out is the type's). **Test reach with the typed edges** (non-test functions within 1 / 2 / 3 / 5 / 10 calls of a test): 2.9 / 5.2 / **8.1** / 15.2 / 28.4% (call edges only: 2.9 / 4.5 / 5.4 / 5.9 / 6.3%; name-matched edges: 3.0 / 12.2 / 25.1 / 48.4 / 66.2%).
**Stage 2, reverse triage on DPDK under the extended graph (all 41 scans):** N1's top 20: **79.0%** (all pairs) and **55.8%** (cause elsewhere), both **identical** to the call-edge-only graph; top 5 58.8 against 58.5% and 29.4 against 28.7%; MRR 0.404 both.
| hypothesis | verdict |
|---|---|
| TP1 argument match at least 85% | **supported**: 100% |
| TP2 at least 26 of 30 sampled edges correct | **supported**: 30 of 30 (one instance-imprecise, noted) |
| TP3 at least 10,000 edges and test reach within 3 calls at least 12% | **half supported**: 12,016 edges; reach 8.1% (not 12%) |
| TP4 at least 60% of the indirect field calls typed | **supported**: 79% |
| Stage 2 EP4: triage moves by less than 3 points | **supported**: 0.0 points at the top 20 |
Surprise bars (TP4 below 40% or TP2 below 20 of 30): not met.
**Reading.** (1) **Static type resolution fixes the precision problem** (13 of 30 correct by name, 30 of 30 by type) and recovers most of the dispatch (79% of the calls typed) with no compiler. (2) **The type-correct edges raise DPDK's test reach only from 5.4% to 8.1% within 3 calls and 28.4% within 10**, so a good share of the drivers is reachable from tests only by long paths; the name-matched 25.1% was mostly false edges. (3) **The repair-radius triage did not change at all** (79.0% and 55.8% unchanged at the top 20): in DPDK the findings are robust to this class of missing edge; the ranking is dominated by same function, same file and directory proximity, which the edges do not touch. **Not shown:** that other findings (the forward repair radius itself, the test-selection result) are equally robust; they were not rerun. DPDK only; other C projects have other dispatch idioms (macros, positional initializers, bare function-pointer variables) that this extractor leaves out.

## Forward repair radius on DPDK under the type-resolved function-pointer edges (hypotheses fixed 2026-11-19 before running)
Same pairs and the same `blast_radius.py run` / `report` as the DPDK result above (1.45 [1.41, 1.48] within 2 calls, either direction, against same-file functions of similar size; baseline re-measured in this run with the unchanged graph), repeated with `BLAST_FNPTR` pointing at the 41 typed edge sets (12,016 edges in the latest scan). Nothing else changes.
- **FR1.** The within-2-calls ratio under the extended graph is within 0.10 of the re-measured baseline (the radius is robust to this missing edge class).
- **FR2.** The observed share of fixed functions within 2 calls (either direction) rises by at most 2 points.
- **FR3.** For different-file fixes (1,561 pairs) the share within 2 calls rises by at least 2 points (the new edges are cross-file by nature, so any gain shows there).
**Would surprise:** the within-2-calls ratio moving by 0.2 or more in either direction.

#### Forward repair radius on DPDK under the function-pointer edges: results (2026-11-19; `fnptr_forward_radius_output.txt`; the baseline re-measured in the same run reproduced 9,867 measured pairs and 6,963 with a fixed function outside the changed set)
Within 2 calls (either direction), ratio against same-file functions of similar size, observed % vs expected %: **all pairs: baseline 1.45 [1.41, 1.48] (51% vs 35%); with the edges 1.43 [1.40, 1.47] (52% vs 36%).** Within 1 call: 1.68 -> 1.67. Callers1: 1.84 -> 1.83; callees1: 1.69 -> 1.68. Same-file fixes (5,402): 1.48 -> 1.47. **Different-file fixes (1,561): 1.20 [1.09, 1.31] (22% vs 18%) -> 1.18 [1.08, 1.28] (24% vs 20%)**; callers1 2.43 -> 2.39, callees1 1.24 -> 1.26.
| hypothesis | verdict |
|---|---|
| FR1 ratio within 0.10 of the baseline | **supported**: 1.43 against 1.45 (-0.02) |
| FR2 observed share within 2 calls rises by at most 2 points | **supported**: +1 (51% to 52%) |
| FR3 different-file share within 2 calls rises by at least 2 points | **supported, but empty**: 22% to 24%, and the baseline's expected share rose just as much (18% to 20%), so the ratio fell slightly (1.20 to 1.18) |
Surprise bar (moving by 0.2 or more): not met.
**Reading.** The new edges (12,016 at the latest scan, correct by the 30-of-30 check) add connectivity to the observed fixed functions and to the same-size same-file baseline in equal measure, so **the repair radius does not change** (1.45 to 1.43; intervals overlap almost entirely). Together with the unchanged reverse triage (79.0% and 55.8% at the top 20), **DPDK's findings are robust to this class of missing edge.** The edges do help the one thing they were built for, linking generic API code to driver code and tests: the test reach within 10 calls rose from 6.3% to 28.4%. **Not shown:** robustness to other missing edge classes (macros, positional initializers, bare function-pointer variables, Tcl and other-language tests), or to this edge class in other C projects (kernel, Mesa, redis); that would need the extractor run there. DPDK only.

## Which fixes cluster with the repair radius, and do the categories help the triage? (hypotheses fixed 2026-11-19 before running; `tools/sensor/fix_taxonomy.py`, `tools/sensor/triage_by_kind.py`)
Three taxonomies from earlier in this log, applied to DPDK and Mesa `Fixes:` pairs (the 9,867 DPDK pairs of the forward radius, and Mesa measured the same way): **(1) mechanism class** of the fix from its subject and body (the Linux keyword classes: lifetime, concurrency, null deref, bounds/overflow, uninitialized, error handling, build/compile; the rest "other"); **(2) fix shape** from the fix's C/H diff (comment only, large 100+ lines, removes code, adds a guard, rewrites a condition, adds sync or release, replaces a call or argument, changes a type or declaration, adds code, small edit, other edit); **(3) the third taxonomy, fix type (regression, other-fix, extrinsic, latent), exists only for the crucible events of curl; every `Fixes:` pair is by construction a regression-class fix, so it cannot vary here and is replaced by the available third axis, the type of the **causing** change by its subject verb (feature, restructure, optimization, fix, other)**. Per category: pairs, same-function share, cross-file share, median lag, radius within 2 calls and within 1 call (same estimator as before, interval over pairs); reverse triage (N1, top 20, as before, 730 days) per category; a **category lag prior** for the triage (N1L: the same ranking with, inside each tier, candidates ordered by closeness of their age to the median log-age of the fix's mechanism class and shape, fitted on one half of the pairs and used on the other, both ways).
- **FT1.** Mechanism classes with at least 100 measured pairs (pooled) have radii (within 2 calls) whose largest-to-smallest ratio is at least 1.3.
- **FT2.** "Adds a guard" and "small edit" have the highest same-function shares among shapes with at least 100 pairs (at least 55%); "large" and "adds code" the highest cross-file shares.
- **FT3.** Fixes of feature-type causes have a lower same-function share than fixes of fix-type or restructure causes (as in Linux).
- **FT4.** Reverse triage works in every category of at least 50 pairs (N1 top 20 at least 55%), and the best and worst categories are within 25 points.
- **FT5.** N1L is at least 2 points above N1 in the top 20, pooled.
- **FT6 (descriptive, no threshold).** The (mechanism, shape) cells of at least 40 pairs with the largest radius, to see which fixes cluster with it.
**Would surprise (categories carry nothing):** all radii within a factor of 1.1 and FT5 below 1 point.

#### Which fixes cluster with the repair radius: results (2026-11-19; `fix_taxonomy_output.txt`, `triage_by_kind_output.txt`; DPDK 9,867 and Mesa 7,410 measured pairs, 11,195 with a fixed function outside the changed set; the triage on the 1,568 pairs of the earlier reverse-triage run)
**By mechanism class** (fix subject and body; **75% of pairs are "other": the keyword classes cover only a quarter of these fixes**): radius within 2 calls (against same-file functions): error handling 1.56, lifetime 1.53, build/compile 1.50, null deref 1.51, uninitialized 1.48, concurrency 1.40, bounds/overflow 1.37, other 1.54; same-function share 44% (bounds) to 59% (concurrency); median lag 66 d (build) to 226 d (lifetime). Mesa alone: null deref 2.60 [1.78, 3.83] (n 39) and build 1.95; DPDK alone 1.28 to 1.52.
**By fix shape** (diff): small edit 1.66 (22% of pairs, lag 106 d); **changes a type or declaration 1.88** [1.63, 2.11]; **replaces a call or argument 1.73**; rewrites a condition 1.58; adds a guard 1.58 (same-function only **38%**, the lowest); removes code 1.57; adds sync or release 1.48; adds code 1.47 (cross-file 22%); other edit 1.44; **large (100+ lines) 1.27** [1.21, 1.34] with the **highest same-function share (62%)** and the longest lag among the big classes (200 d); comment only 1.27 [0.98, 1.64] (n 129; cross-file 26%).
**By the type of the causing change** (the subject verb of the commit the fix names): **fix 2.00 [1.87, 2.14] (same-function 75%, cross-file 8%, lag 111 d); optimization 1.81 (74%)**; restructure 1.77 (59%); other 1.66; **feature 1.36 [1.32, 1.40] (same-function 41%, cross-file 21%, lag 197 d; half of all pairs)**. The order is the same in DPDK (feature 1.30, fix 2.06) and Mesa (feature 1.56, fix 1.89).
**Cells** (mechanism x shape, 40+ pairs with a fixed function outside the changed set): highest radius **build/compile x replaces a call or argument 2.42** [1.69, 3.91], **error handling x replaces a call 2.02**, other x changes a type or declaration 1.82, build x removes code 1.79; lowest other x large 1.29, concurrency x small edit 1.26 (interval reaches 0.78), error handling x adds code 1.32.
**Reverse triage by category** (N1 top 20, pooled 74.2%): mechanism: null deref 87.0% (n 23), lifetime 85.1%, bounds 82.0%, uninitialized 79.3%, error handling 76.0%, build 75.8%, other 72.9%, concurrency 71.2%; shape: replaces a call 82.7%, rewrites a condition 82.2%, adds a guard 80.2%, other edit 78.1%, small edit 74.9%, removes code 75.6%, changes a type 74.5%, adds code 66.0%, **large 51.6% (n 64)**, comment only 45.5% (n 11). **Category lag prior (N1L)**: top 20 71.9% against 74.2%; top 5 49.7% against 56.4%; MRR 0.338 against 0.411.
| hypothesis | verdict |
|---|---|
| FT1 mechanism radii span at least a factor 1.3 | **not supported**: 1.37 to 1.56, factor 1.14 (the radius is one pattern across mechanisms, as in Linux) |
| FT2 guard and small edit have the highest same-function share; large and adds code the highest cross-file share | **not supported**: highest same-function are large (62%), other edit (59%), rewrites a condition (58%); guard is the lowest (38%); highest cross-file are comment only (26%), adds code (22%), adds a guard (19%), large only 15% |
| FT3 feature-caused fixes less same-function than fix- or restructure-caused | **supported strongly**: 41% against 75% and 59% |
| FT4 triage at least 55% in every category of 50+ pairs, spread at most 25 points | **not supported**: 14 of 15 categories at 66% or more, but large fixes 51.6%; spread 33.5 points (85.1 to 51.6) |
| FT5 category lag prior at least 2 points above N1 | **not supported, and it hurts**: -2.2 points (top 5 -6.7): recency is the better tie-break inside a tier |
| FT6 cells | descriptive, above |
Surprise bar (all radii within a factor 1.1 and FT5 under 1 point): not met on the radius (cause type 1.36 to 2.00, shape 1.27 to 1.88), met on FT5 (it is negative).
**Reading.** (1) **What clusters with the radius is the change that caused the fix, not the kind of fix**: fixes of fixes and of optimizations are tight (75% in the same function, radius 1.8 to 2.0, 8% cross-file) while fixes of features are dispersed (41% same function, radius 1.36, a long lag); this replicates the Linux reading and holds in both projects. **The fix's own category carries little**: mechanism classes are within 1.37 to 1.56 (and 75% of fixes are unclassified), while shape matters at the ends (large fixes: lowest radius, highest same-function share, hardest to triage; type and declaration changes and call replacements: highest radius). (2) **Triage works for every kind of fix except the large ones**: from 66% to 87% for every category, but large fixes (100+ lines, 4% of fixes) drop to 51.6%; the interval is wide (n 64), and a large fix names many functions, which dilutes the site. (3) **A per-category lag prior does not help**: the cause age depends on the project and on the cause (feature causes 197 d, fix causes 111 d), which the fix's category barely predicts; recency stays the better tie-break. The better lever for a lag prior would be the *cause type*, which is unknown when triaging. **Caveats:** shapes from a regex on the diff, mechanism from subject keywords (25% coverage); two projects; cause type from the first verb of the subject; categories overlap (large fixes are also the "other"); associations, not mechanisms.

#### How much of the work is sweeps, fixes, named-cause repairs and radius? A descriptive census (2026-11-19, exploratory, not pre-registered; `work_census_output.txt`; DPDK and Mesa; function edits = hunk-header functions of C/H changes, unverified)
| | DPDK | Mesa |
|---|---|---|
| non-merge commits / touching C/H functions / function edits | 46,419 / 35,908 / 189,837 | 233,419 / 160,281 / 687,372 |
| sweeps (more than 60 functions): share of commits / of function edits | 0.7% / **20.9%** | 0.5% / **18.0%** |
| fix-like organic commits (subject keyword or `Fixes:`): share of commits / of edits | 39.1% / 17.9% | 18.3% / 9.5% |
| with a `Fixes:` trailer: share of organic commits / of edits | 35.8% / 15.6% | 6.0% / 2.5% |
| named-cause pairs measured: repaired functions as share of all edits | 12.2% (23,068) | 1.8% (12,245) |
| of the repaired functions: in the cause's own changed set / outside it | 30% / 70% (8.6% of all edits) | 41% / 59% (1.0% of all edits) |
| outside-set repairs within 2 calls: observed vs expected in the same files; **excess** | 8,359 vs 6,602; **1,757 = 0.93% of all edits** (11% of outside-set repairs) | 3,092 vs 2,087; **1,005 = 0.15% of all edits** (14%) |
**Reading.** Sweeps are under 1% of commits but about a fifth of all function edits. Roughly a sixth of DPDK's edits are named-cause repairs (Mesa's low 1.8% is mostly its trailer habit: 6% of commits carry `Fixes:`, against 36% in DPDK). **The radius's excess over chance, the share of work that lands near a change beyond what its own file would give, is about 1% of function edits in DPDK and 0.15% in Mesa (11 to 14% of the repairs that fall outside the cause's own functions)**: a ranking signal, not a main driver of workload. Caveats: hunk-header function names (about 13% were never edited, unverified); only trailer-named fixes are counted as repairs (unnamed fixes exist; fix-like subjects are 39% of DPDK's organic commits against 36% with trailers); the baseline is same-file functions of similar size, which removes the file-level part of the locality, so it understates how much repair happens near the change.

## How much repair work has an earlier cause? Adding the fixes that name no cause (hypotheses fixed 2026-11-19 before running; `tools/sensor/work_census_blame.py`)
The census above counted only fixes with a `Fixes:` trailer. **Unnamed fix-like commits** (subject with fix, fixes, fixed, bug or regression; not a revert; no `Fixes:` trailer; fewer than 60 functions) are sampled (2,500 per repository, seeded), their cause is derived by blame as in the language study (`git blame -w -M` of the removed lines at the parent; the commit owning most removed lines is the cause; cause must be older than the fix), and the same measurement is run (`lang_validation.measure`: the repair radius within 2 calls against same-file functions of similar size, quarterly scans; sweeps of more than 60 cause or 30 fix functions dropped). DPDK and Mesa.
- **UC1.** At least 60% of the sampled unnamed fix-like commits obtain a blame-derived cause.
- **UC2.** The radius within 2 calls of the blame-derived pairs is at least 1.3 with an interval lower bound above 1.2, in each repository.
- **UC3.** Within 0.15 of the trailer-named radius of the same repository (DPDK 1.45, Mesa 1.60), so the pattern does not depend on the trailer habit.
- **UC4.** Accounting: with the unnamed fixes added (sample scaled to all unnamed fix-like commits), pairs with a named or blame-derived cause hold at least 20% of DPDK's function edits and at least 8% of Mesa's; the radius excess (observed minus expected landings within 2 calls) stays under 3% of all function edits in both.
**Would surprise:** UC2 below 1.15 (the pattern is a feature of trailer-named fixes) or UC1 below 40% (most unnamed fixes have no blameable cause).

#### Census with blame-derived causes: results (2026-11-19; `work_census_blame_output.txt`; the first launch printed nothing because the script lacked its `main()` call; fixed and rerun)
| | DPDK | Mesa |
|---|---|---|
| unnamed fix-like commits (subject fix, fixes, fixed, bug, regression; no trailer; 1 to 60 functions) | 969 = 1.9% of all function edits | 17,207 = **6.1%** |
| sampled / blame cause found | 969 / 801 (**83%**) | 2,500 / 2,131 (**85%**) |
| measured (after dropping 392 / 544 with no function name in a commit hunk header, 13 / 92 sweeps) / with a fixed function outside the changed set | 194 / 115 | 922 / 418 |
| same-function share of measured | 49% | 65% |
| **radius within 2 calls, blame-derived** (trailer-named in brackets) | **1.40 [1.14, 1.71]** (1.45) | **1.63 [1.48, 1.80]** (1.60) |
| within 1 call | 1.70 [1.29, 2.26] | 2.00 [1.74, 2.30] |
| median lag | 330 d | 226 d |
| scaled: edits of unnamed fixes with a blame cause / their radius excess, as share of all function edits | 1.5% / 0.01% | **5.2%** / 0.13% |
| **named + blame-caused repairs, share of all function edits** | **12.2% + 1.5% = 13.7%** | **1.8% + 5.2% = 7.0%** |
| radius excess, named + blame | 0.93% + 0.01% | 0.15% + 0.13% |
| hypothesis | verdict |
|---|---|
| UC1 blame cause for at least 60% | **supported**: 83% and 85% |
| UC2 radius at least 1.3 with lower bound above 1.2, each repository | **half**: Mesa 1.63 [1.48, 1.80] supported; DPDK 1.40 [1.14, 1.71] not supported on the lower bound (only 115 pairs) |
| UC3 within 0.15 of the trailer-named radius | **supported**: -0.05 and +0.03 |
| UC4 caused repairs at least 20% of DPDK's and 8% of Mesa's edits; excess under 3% | **not supported**: 13.7% and 7.0%; the excess part is supported (0.94%, 0.28%) |
Surprise bars (UC2 below 1.15 or UC1 below 40%): not met (DPDK's lower bound is 1.14, its point estimate 1.40).
**Reading.** (1) **The radius does not depend on the `Fixes:` habit**: blame-derived causes of unnamed fixes give the same radius (1.40 against 1.45; 1.63 against 1.60), and blame finds a cause for 83 to 85% of them. (2) **Counting unnamed fixes changes the picture of the project, not of the radius**: DPDK is a trailer project (almost all fixes are named; unnamed ones are 1.9% of edits), Mesa mostly is not (its unnamed fixes carry 6.1% of edits, three times its named ones). With both, **7 to 14% of all function edits are repairs of an earlier change**, and the radius's excess over chance is **about 1% (DPDK) and 0.3% (Mesa) of function edits**. (3) Caveats: the unnamed set uses the narrow subject rule (fix, bug, regression), narrower than the keywords of the first census, so DPDK's unnamed share is a floor; half of the blamed pairs (392 of 801; 544 of 2,131) are lost in the measurement for lack of a function name in a hunk header, so the radius rests on 194 and 922 pairs (115 and 418 outside the changed set); the work shares scale the blame rate to all unnamed fix-like commits (the 17,207 are not all genuine fixes); blame names where the fixed lines were last changed, not necessarily the cause.

## Accounting for all the work: a complete partition of function edits (hypotheses fixed 2026-11-19 before running; `tools/sensor/work_partition.py`)
**Goal.** Put every function edit of DPDK and Mesa (hunk-header function names of non-merge commits that touch C or H files; 189,837 and 687,372) into exactly one category, and say which of the changes were later repaired. **Categories, first match wins:** (1) sweep (more than 60 functions); (2) revert (subject starts with Revert); (3) fix with a named cause (`Fixes:` trailer); (4) fix without a named cause, a cause found by blame; (5) fix without a cause found (fix-like = the broad subject rule of the first census: fix, fixes, fixed, bug, regression, crash, leak, overflow, race, deadlock, uaf, null, or a trailer); (6) tests only (every C/H file touched is a test file); (7) comment or whitespace only (diff); (8) formatting, docs or licence by subject (typo, spelling, whitespace, style, checkpatch, indent, licence, docs, comment); (9) adds code (added lines at least three times the removed); (10) removes code (removed at least three times the added); (11) modifies code (the rest), split by the causing-change verb of the subject (feature, restructure, optimization, other). **Blame** for all commits of categories 4 and 5 (not a sample). **Cause side:** a commit is *cited* if it is the named or blame-derived cause of at least one later fix; shares of commits and of function edits per category that are cited. **Hand check:** 40 random commits of categories 9 to 11 per repository, read by subject, to see how many are fixes the keyword rule missed.
- **RM1.** Fix categories (3 to 5) hold at most 30% of function edits in both repositories.
- **RM2.** Sweeps, reverts, tests-only, comment-only and formatting/docs together (1, 2, 6, 7, 8) hold at least 30% of function edits in both.
- **RM3.** Hand check: at most 4 of the 40 sampled commits per repository are fixes the rule missed.
- **RM4.** Among organic non-fix commits (categories 6 to 11) the share of function edits in cited commits is between 10% and 40% in both repositories.
- **RM5.** Per function edit, the cited rate of "adds code" commits and of "modifies code" commits is within a factor of 2 of each other (size explains the rest).
**Would surprise:** fix categories above 40% of edits, or adds + removes + modifies below 25% of edits.

#### Complete partition of function edits: results (2026-11-19; `work_partition_output.txt`; totals reconcile to 46,419 commits / 189,837 edits (DPDK) and 233,419 / 687,372 (Mesa); Mesa's blame over 18,755 commits took 22 minutes, the diff features 2)
Share of function edits (share of commits), and the share of each category's edits in commits later **cited** as the cause of a fix (named or blame):
| category | DPDK edits (commits) / cited | Mesa edits (commits) / cited |
|---|---|---|
| touches no C/H function | 0 (22.6%) | 0 (31.3%) |
| sweep (over 60 functions) | **20.9%** (0.5%) / 44% | **18.0%** (0.3%) / 52% |
| revert | 0 (0%) | 0.4% (0.4%) / 8% |
| fix, named cause | **15.6%** (27.5%) / 17% | 2.4% (4.1%) / 10% |
| fix, cause by blame | 1.9% (2.0%) / 22% | **5.9%** (6.9%) / 15% |
| fix, no cause found | 0.2% (0.5%) / 13% | 0.6% (1.2%) / 7% |
| tests only | 2.0% (1.9%) / 31% | 0.1% (0.2%) / 1% |
| comment or whitespace only | 0.2% / 0% | 0.1% / 3% |
| formatting, docs, licence (subject) | 0.6% / 4% | 1.0% / 10% |
| **adds code** | **26.8%** (24.7%) / 45% | **21.5%** (20.4%) / 24% |
| removes code | 4.0% (3.1%) / 16% | 5.9% (5.0%) / 8% |
| modifies, feature verb | 6.4% (3.7%) / 35% | 6.6% (4.5%) / 20% |
| modifies, restructure verb | 13.6% (7.7%) / 26% | **21.5%** (12.5%) / 16% |
| modifies, optimization verb | 1.5% / 22% | 1.0% / 13% |
| modifies, other verb | 6.1% (4.0%) / 25% | 14.7% (11.5%) / 17% |
Grouped, share of function edits (DPDK / Mesa): **sweeps 20.9 / 18.0**; **fixes of all kinds 17.8 / 9.0** (cause known 17.5 / 8.3); **mechanical other** (reverts, tests only, comment only, formatting) 2.8 / 1.7; **organic code changes** (adds, removes, modifies) **58.5 / 71.3**. The organic changes that were later cited as the cause of a fix: **34.0% / 18.4% of their edits**.
**Hand check** (40 random commits of adds, removes and modifies per repository, read by subject): DPDK about 3 fixes the keyword rule missed ("cap memcpy at field size", "avoid panicking in absence of ethdev shared data", "skip memzone freeing if port created"); Mesa about 8 ("handle an out-of-bounds sampler/image index better", "added divide by zero checks", "Returns a GL_INVALID_VALUE error ... when buffer size is negative", "do not overwrite loads_push_constants when declaring shader args", "always emit PGM_RSRC1_HS when emitting the TCS epilog state", "ignore stage flags that are expanded", "disable some more code so that it compiles quietly", "Guard XCB_PRESENT_OPTION_SUBOPTIMAL ..."). Hidden fixes: DPDK 3 of 40 (8%, interval about 2 to 20%), Mesa 8 of 40 (20%, about 9 to 36%), of the organic code changes (58.5% and 71.3% of edits): **about 1 to 12% (DPDK) and 6 to 26% (Mesa) of all function edits are fixes the subject rule did not find** (my reading of subjects, a judgment).
| hypothesis | verdict |
|---|---|
| RM1 fix categories at most 30% of edits | **supported**: 17.8% and 9.0% (before hidden fixes: add up to about 12% and 26%) |
| RM2 sweeps, reverts, tests-only, comment-only, formatting at least 30% | **not supported**: 23.7% and 19.7% |
| RM3 at most 4 of 40 hidden fixes per repository | **DPDK supported (about 3); Mesa not (about 8)** |
| RM4 cited share of organic non-fix edits 10 to 40% | **supported**: 34.0% and 18.4% |
| RM5 cited rate per edit, adds vs modifies, within a factor 2 | **supported**: 44.7% vs 27.4% (1.63); 24.4% vs 17.1% (1.43) |
Surprise bars (fix categories over 40% of edits; adds + removes + modifies under 25%): not met.
**Reading.** Of all function edits, **about a fifth are sweeps, about a tenth to a sixth are recognisable fixes (more if the hidden ones are counted, up to about a quarter in Mesa), a few percent are mechanical, and 58 to 71% are organic code changes**: added code is the largest single category (27% and 22%), then restructuring (14% and 22%). **A third (DPDK) and a fifth (Mesa) of the edits in organic changes are later cited as the cause of a fix**, so about 20% and 13% of *all* function edits (34.0% x 58.5%; 18.4% x 71.3%) are changes that were later repaired; sweeps are cited more than anything else (44% and 52% of their edits, because they touch so much), and edits in added code are cited about 1.4 to 1.6 times as often as edits in modified code. Caveats: categories come from subject keywords, hunk-header functions and a three-to-one added/removed rule; hidden fixes in the remainder are a manual estimate from 40 subjects per project; "cited" means named or blamed as the cause of a later fix (a lower bound: unfound causes and fixes without keywords add more); DPDK has no `Revert` subjects in this rule.

#### A typical quarter (2026-11-19, descriptive, not pre-registered; `typical_quarter.py`, `typical_quarter_output.txt`; median of the last 16 quarterly scans; components are medians, so they do not add exactly)
| | DPDK (55k functions) | Mesa (84k) |
|---|---|---|
| commits / distinct functions edited | 776 / 2,368 (4.3% of functions) | 4,280 / 6,560 (7.8%) |
| edited by organic commits / sweeps / fixes / mechanical | 1,477 / 610 / 530 / 74 | 5,172 / 1,482 / 801 / 72 |
| edited twice or more in the quarter | 432 | 1,902 |
| **births** (new functions) | **1,103**: new file, new name 544; existing file, new name 437; moved or renamed 131 | **3,659**: 1,062; 1,225; 810 |
| **deaths** | **346**: whole file removed 28; function removed from a kept file 134; moved or renamed 128 | **2,016**: 288; 546; 732 |
| fix edits / in functions fixed 2+ times in the history / fixed 5+ times | 577 / 301 (52%) / 81 (14%) | 898 / 549 (61%) / 178 (20%) |
| organic-edited functions also fixed in the same quarter / sweep-edited ones | 80 of 1,477 (5.4%) / 15 of 610 (2.5%) | 352 of 5,172 (6.8%) / 48 of 1,482 (3.2%) |
Whole history: functions fixed 2+ times hold 60% (DPDK) and 61% (Mesa) of fix edits; the top 1% of fixed functions hold 8%, the top 10% hold 31 to 32%. 24 random sweep subjects per project: renames (`rename bonded to bonding`, `rename LIST_ENTRY() to list_entry()`), API conversions (`replace logging helpers`, `standardize on negative errno values`, `all: rename PIPE_SHADER_GEOMETRY to MESA_SHADER_GEOMETRY`), reformatting (`unify the indent coding style`, `add .clang-format`), branch merges, generated headers.
