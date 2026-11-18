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
