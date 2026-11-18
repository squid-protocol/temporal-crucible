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
