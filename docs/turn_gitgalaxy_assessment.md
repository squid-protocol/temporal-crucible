# What GitGalaxy is good for: an assessment from the TURN discovery and forecast work

**Status: exploratory, 2026-11-16. Not registered, not reviewed.** Work branch `turn/forecast` (builds on PR #186, `turn/registration-draft`). Every number below comes from a document or script on these two branches; the provenance table at the end says which. Thirteen repositories, one engine, quarterly snapshots; the claims are discovery-grade.

## 1. Purpose and short answer

The question was how to leverage GitGalaxy (the engine that turns a source tree into a function table with size, complexity, arguments, keyword-family counts and call edges) once there is a full history of every repository analysed by that one engine. We tried to use it for two things: to describe how repositories change, and to forecast errors, fixes and CVEs.

**Short answer.** The evidence supports GitGalaxy as an instrument for describing change, tracking function identity through time, and scoping mechanical work. It does not support it as a defect predictor beyond what size, churn and prior fixes already give, and the label problem documented in this crucible makes any such claim fragile even where a lift appears.

| Role | Evidence | Verdict |
|---|---|---|
| Uniform multi-language function census | 13 repos, six languages, same fields, 2-7 minutes per repo for 70-110 quarterly snapshots | Strong |
| Function identity across renames and moves (the ledger) | moves 98.9% right, renames 84.4% right on six unseen repos | Strong, distinctive |
| Scoping a migration (sweep) | call-graph callers: recall 1.00, precision 0.83 (text search 0.74) on 417 sweeps | Good; grep gets the same recall |
| Describing how change happens | growth, hazard, wiring, hubs, edit kinds, sweeps | Strong, mostly descriptive |
| Detecting edit categories by keyword family | engine sees 96-100% of grow, shrink, rewrite edits; 33-67% of renames | Useful with limits |
| Predicting fixes, CVEs, regressions beyond size, churn, prior fixes | edit kinds add -0.003 to +0.002 AUC; recidivism shrinks with cleaner labels | Not supported |

## 2. What was built and measured

* **A function ledger** (persistent lineage ID per function across snapshots; structure proposes a link, body text or comments verify it). Packaged in structural-fingerprint-scanner, branch `ledger`. Held-out accuracy on six repos never used to set a bound: moves (same name, new file) 7,056 of 7,132 right (98.9%), 8 wrong (0.11%); renames 711 of 842 right (84.4%), 50 wrong (5.9%, or 2.9% without one libxml2 reorganisation quarter); quarterly chains and direct jumps disagree in 0-2.0% of functions over four years (`docs/turn_discovery_2026-11-15.md` section 12).
* **Thirteen repositories scanned quarterly**: curl, redis, libgit2, libxml2, expat (C); impacket, sqlmap, scapy, sphinx (Python); ripgrep (Rust); tigerbeetle (Zig); commons-io (Java); prometheus (Go). Seven were the discovery set, six held out.
* **A tree-sitter edit classifier** (C, Python, Rust, Zig, Java, Go) applied to the surviving functions the ledger links, and a **sweep detector** (the same call or macro changed in at least max(10, 1%) of a quarter's edited functions).
* **A per-repo scorer** with bootstrap intervals, a forecast ladder, fix-label audits, and the crucible's own fix labels (raw keyword label, v3c, regression class).

## 3. Evidence by capability

### 3.1 A uniform census at history scale
Quarterly scans of 69-109 snapshots took 137 s (expat, 92 snapshots) to 393 s (libgit2, 69 snapshots); a 14-snapshot monthly scan of impacket took 47 s. Because every repo passes through the same engine, per-repo ranges could be stated for the following (all discovery, 13 repos; `turn_discovery_2026-11-15.md` sections 7, 13, 14):
* births in new files 44-73%; deaths that are whole-file removals 35-78%;
* median quarterly deaths under 1% of functions in mature repos (4.3% in the young fast repo);
* share of functions still identical to their birth state: about 90% after a quarter, 59-89% after a year, 46-80% after two; the chance of a first change is highest in the first quarter (4-19%) and falls to 1-5% by quarter 8;
* functions born with no callers still have none a year later in 95-100% of cases in 12 of 13 repos; hubs stay hubs (94-99% in most repos);
* path-and-name identity overcounts deaths by 28-463% against lineage identity.

### 3.2 Identity through time
The ledger depends on the engine's per-function measurements (lens vectors, call edges, start line, size, docstring). Its stages are identity, same name in the git-mapped file, unique name, structure plus relative order, and structural twins; stages that propose by structure keep a link only if body text or comments agree. Comments are an independent witness: they agree with body-verified links 99% (similarity at least 0.85) to 91% (0.5-0.7) of the time, and with call-graph-extension links only 27% of the time, so that stage was dropped. Errors concentrate in near-duplicate siblings (JUnit test methods, API wrappers left behind by a file split) and not at random. Consequence for downstream use: moves are near-perfect, renames need a confidence flag, and any ledger-dependent result should be reported with and without comment-only and ambiguous links.

### 3.3 Mass migrations ("sweeps")
Mechanical change is a large share of in-place change: 4% (ripgrep) to 44% (libgit2) of code edits to surviving functions, median about 22% across the 13 repos (curl 4% in the 2000s, 36% in 2025). Properties:
* 84-98% of old-to-new migrations (counted by distinct pair) land in one quarter; test-framework moves take 4-7 quarters (commons-io `fail` to `assertThrows` over 7 quarters, 209 functions);
* 44% belong to repeated-rename chains (`git_buf_free` to `git_buf_dispose` to `git_str_dispose`);
* organic edits change signatures more often than sweep edits in 12 of 13 repos;
* the apparent "retrofit" of allocation, cleanup and print keyword families is a sweep effect: removing sweep edits from the drift removes the retrofit gap in curl (+0.196 to -0.026), libgit2 (+0.081 to -0.003) and libxml2 (+0.174 to -0.045) (`turn_discovery` sections 11, 14);
* fewer than 1% of labelled fix commits are sweeps in any class (other-fix 0.9%, regression 0.8%, extrinsic 0.6%, latent 0.9%), so the crucible's dependent variable is not contaminated by them; sweep edits show no consistent effect on later fixes (`turn_sweeps_and_fixes.md`).

### 3.4 What the engine sees of an edit
For edits to surviving C functions (libgit2 / curl / redis): grow, shrink and big-rewrite edits change keyword-family counts in 96-100% of cases; signature-only edits in 65-77%; swap/rename edits change resolved call edges in 77 / 58 / 73% and keyword counts in 33 / 67 / 63%, and neither in 7 / 13 / 15% (the callee is a standard-library or unresolved-macro name). The engine therefore detects what changed structurally and where, and tree-sitter is needed to say what the edit was (`turn_sweep_forecast.md`).

### 3.5 Six kinds of edit
K-means (k=6) on 12 edit features, fitted on curl, redis and libgit2, found in all five C repos the same kinds in similar shares: tweak 35-48%, swap/rename 16-39% (90% inside a sweep), signature only 10-24%, grow with logic 9-20%, shrink 1-8%, big error-handling rewrite 0.2-2.2%. The mix regresses to a repo-specific average: the long-run mix predicts next quarter's mix better than last quarter's mix in all five (error 0.17-0.48 vs 0.21-0.56). Edits beyond the 99th percentile of the discovery repos: 0.5-1.5% (`turn_fix_catalog_and_archetypes.md`).

### 3.6 Scoping a migration
The most direct product signal. For 767 sweeps of at least 5 functions (431 where the old name is a function defined in the repo), the engine's call graph predicted the set of functions swept using only the snapshot before: recall 1.00 and median precision 0.83 on 417 resolvable sweeps, against 0.74 for a text search mapped to function ranges. Precision rises with size (0.74 for 5-20 functions, 0.95-0.99 above 60). A sweep covers a median 90% of the old name's callers. Median 7 files touched, the three biggest holding 70% of the swept functions; swept functions are leaf-side, not hubs (7% in the top in-degree decile, where 10% is chance). The engine cannot scope the 336 sweeps whose old name is a standard-library, builtin or unresolved macro name; a text search still finds those (`turn_sweep_scope.md`).

## 4. Where GitGalaxy did not help

* **Defect prediction.** The mix of edit kinds adds -0.003 to +0.002 AUC beyond size and churn under all three labels (raw, v3c, regression-only), at file and function grain. Size and churn alone give AUC 0.71-0.89: the size wall (`turn_edit_kinds_vs_fixes.md`, `turn_function_recidivism.md`).
* **Recidivism.** The signal sits at file level and shrinks with label cleaning: curl +0.030, +0.017, +0.004 AUC (raw, v3c, regression); redis +0.037, +0.016, 0.000. The function's own prior fixes add 0.000-0.004 beyond the file; correct lineage identity adds 0.000-0.002 over naive identity at this horizon. This agrees with the crucible's own result that cleaning the label collapsed pooled recidivism on the CGR eight (+0.082 to +0.009) with curl the exception (+0.333 to +0.071).
* **Function-level next-change forecasts.** AUC 0.5-0.8 on six held-out repos, small and inconsistent skill over the repo's recent rate; event rates are bursty, so the repo-wide rate carries most of the predictable signal (`turn_forecast_firstlook.md`).
* **Forecasting sweeps.** The new name first appears in the sweep quarter itself in 76% of cases; one third of the 25 largest sweeps per repo had a deprecation message beforehand; a name-pattern alert caught 46% of resolvable large sweeps with about 0% precision (`turn_sweep_forecast.md`). Which API will be renamed and when is largely not forecastable from structure.
* **Intent and macros.** The engine reads no commit text and does not resolve standard-library or macro callees.

What fix work looks like by class is detectable (CVE fixes: bounds checks 1.5x, early returns 1.8x, pointer changes 1.5x, removing a free 3.3x, median 14 lines vs 8; extrinsic fixes: casts 2.0x, fewer new guards) but it comes from diffing fix commits with tree-sitter, not from a property of the engine's snapshot features; the engine's keyword features did not separate fix classes in the earlier crucible work either (`turn_fix_catalog_and_archetypes.md`).

## 5. Recommendations: features to build or lean on

Ordered by strength of evidence. Effort: S (days), M (weeks), L (a quarter).

1. **Migration scope and progress report (S-M).** Input: an old and a new name (or a detected sweep). Output: callers by function and file with lines of code, who remains unswept, percent complete across snapshots, leaf-or-hub position, and callers of the swept functions (ripple). Evidence: section 3.6. Not yet tested: ripple, effort in lines, which callers a migration skips.
2. **Mechanical-versus-organic change metric (S).** Report churn with sweep edits separated. Evidence: sweeps are 16-44% of edits, carry no consistent defect signal, and explain the retrofit artefact. Any process predictor built on churn should use the organic part.
3. **Ledger in the scan (M).** Persistent function IDs as a scan output, with a normalised body hash or shingle set and `start_line` always stored, so matching does not need git access. Evidence: section 3.2.
4. **External callee nodes (M).** Add standard-library, builtin and macro callees to the call graph (even as unresolved names). Evidence: 336 of 767 sweeps are invisible to the call graph for want of this; 7-15% of rename edits show neither a keyword nor a call-edge change.
5. **A repo change profile (S, descriptive).** Mix of edit kinds, first-change curve, new-file share, sweep share. Not yet shown to differ across repos or to mean anything for outcomes; present as description.
6. **Edit classification as an engine output (L).** Ship a tree-sitter edit classifier or a function-delta output so tools can ask "what changed" without a second pipeline. Evidence: section 3.4; tree-sitter explained what the engine could only locate.

## 6. What not to claim

* A defect, vulnerability or "risk" score beyond size, churn and prior fixes.
* That recidivism or prior-fix counts are a robust predictor; the label-cleaning results above, and the crucible's bias analysis (announcement propensity can manufacture lift), say the effect depends heavily on the label.
* That edit-kind or keyword-mix features find CVEs or regressions.
* That sweeps can be predicted in advance beyond their size.

## 7. How to test whether it is useful

The statistics above show the engine describes and scopes well; they cannot show a maintainer would use it. A pilot is the real test: produce the migration scope report for a real recent migration (for example curl's `free` to `curlx_free`, or libgit2's `git_buf_free` to `git_buf_dispose`), predicted from the snapshot before, and compare with what the maintainers actually changed and how long it took. Success criteria set in advance: recall of the swept functions at least 0.95; precision at least 0.80; the report identifies the unswept callers a maintainer agrees are real stragglers.

## 8. Limits

Thirteen repos, one engine; three of the C repos fitted the archetypes and the discovery thresholds; keyword fix labels (raw, v3c) are known to carry artefacts and the regression arm has few events (19-961 test fixes per repo); fix files are matched to snapshots by path, so renamed files lose their history; function-level fix mapping and edit classification exist for C only; sweep detection uses discovery thresholds (10 functions or 1%); engine callers count only resolved calls; the LAWS panel is not in the local pool, so nothing here is a confirmatory test; one split and one model per forecast; no hyperparameter search.

## 9. Open questions

Does the migration report hold up on real maintainer migrations? Which callers does a migration skip, and can the call graph or keyword families predict that? Do edit-kind mixes differ across repos enough to be a useful profile? Do the function-level results survive outside C? Is there an upstream signal (deprecations, language or library versions, release milestones) that forecasts sweeps? What do the same measurements show on the LAWS panel?

## 10. Provenance

| Claim | Document | Script |
|---|---|---|
| ledger accuracy, held-out | `turn_discovery_2026-11-15.md` s12 (PR #186 branch) | `tools/turn/heldout_eval.py`; ledger in sfs branch `ledger` |
| growth, hazard, wiring, hubs, per-repo ranges | `turn_discovery` s7, s13, s14 | `turn_score.py`, `set1.py`, `score_report.py` |
| sweeps, retrofit | `turn_discovery` s10, s11, s14, s15 | `sweeps.py`, `ts_edits.py`, `ts_edits2.py`, `kw4.py` |
| label audit, sweep exposure | `turn_sweeps_and_fixes.md` | `sweep_audit.py`, `sweep_exp.py` |
| fix catalog, six kinds | `turn_fix_catalog_and_archetypes.md` | `fix_catalog.py`, `archetypes.py` |
| edit kinds vs fixes | `turn_edit_kinds_vs_fixes.md` | `arch_frame.py`, `arch_model.py`, `arch_predict.py` |
| sweep forecast, engine view of edits | `turn_sweep_forecast.md` | `sweep_forecast.py`, `intent.py`, `swap_check.py` |
| function recidivism | `turn_function_recidivism.md` | `fix_funcs.py`, `fn_frame.py`, `fn_model.py` |
| sweep scope | `turn_sweep_scope.md` | `scope_test.py`, `scope_report.py` |
| forecast first look | `turn_forecast_firstlook.md` | `forecast.py` |
| crucible context (ceiling, label collapse) | `ceil.md`, `curl_rerun.md`, `hr1_bias_analysis.md`, `repowise_assessment.md` | `tools/ceil_eval.py` |
