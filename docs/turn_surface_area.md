# What are the surface-area (formerly risk-exposure) measurements good for? (work branch `turn/forecast`; exploratory, not registered)

The engine's file-level vector of 13 `risk_*` columns (cognitive load, safety score, tech debt, verification, API exposure, concurrency, state flux, dead code, spec match, stability, churn, documentation, secrets risk) was shown not to measure risk and has been renamed. This asks what they do measure, whether the mix describes anything, and whether to keep, change or drop them. Tools: `tools/turn/surface_area/`; logs: `docs/turn_surface_area_logs/`.

## Data and an engine caveat
* **13 repos, quarterly snapshots (every eighth plus the last): 33,886 file-snapshots, 6,081 code files in the last snapshots.** These scans ran through the installed `galaxyscope` entry point, which imports the stale `/nvme-data/projects/gitgalaxy` copy (a fix branch with no as-of history mode; its `signal_processor.py` differs from `origin/main` by 207 lines and its `chronometer.py` by 287). The formulas read below are from `origin/main`; the values in these 13-repo scans came from the older code. Within the 13 repos the engine is consistent.
* **Check on the newer engine:** the population master database `master_db_v2.12.0-b64f42bf.db` (1.45 million files, 643 repos), sampled at up to 300 random code files per repo (77,706 files, 580 repos), reproduces every descriptive result below.
* **History-aware scans:** the scan tool in `historical-call-graph-gif` exports each commit as a plain tree with no `.git`, so the engine cannot compute churn or stability whatever the history flag says (constant in all 13 scans). A real test needs a detached git worktree, the main engine (extracted from `origin/main` with `git archive`), and `GITGALAXY_HISTORY_ASOF=1`. Done here for 7 repos with fix labels (every fourth snapshot, 143 scans, 5-40 s each).

## What they are
Each is a weighted density of the engine's keyword families per line, netted against a mitigation (locks against concurrency, freezes against mutation), squashed to 0-100 by a sigmoid.

## Descriptive findings (13 repos; master database in brackets)
1. **Sparse or saturated.** Zero on most files: concurrency 91% [84%], secrets 99.9% [99.8%], dead code 82% [94%], tech debt 59% [63%]. Pinned at 100: documentation 58% [63%], state flux 27% [21%]. Resolution is lost at the extremes.
2. **Mostly a relabelling of one or two keyword densities.** Concurrency vs `arch_concurrency` rho 0.94 [0.97]; dead code vs `state_graveyard` 1.00 [1.00]; secrets vs `threat_private_info` 1.00 [1.00]; cognitive load vs branch density 0.74 [0.75]; API exposure vs `arch_api` 0.71 [0.67]; **`safety_score` vs mutation density (`state_flux`) 0.83 [0.77]**, so it is mostly a mutation measure.
3. **Not just size, and not redundant with each other.** Size correlation (median over repos) from +0.51 (cognitive load) to +0.05 (secrets); median pairwise rank correlation +0.02 [+0.07]; PCA participation ratio 4.4 [5.4] for 10 [12] metrics.
4. **Construct validity is mixed.** Concurrency tracks lock and thread keywords (+0.83 [+0.91]); cognitive load tracks function complexity (+0.75 [+0.77]); **API exposure tracks real centrality (PageRank and blast radius +0.63 [+0.57]) and separates header files (AUC 0.90 [0.88])**; safety score tracks safety keywords weakly (+0.27 [+0.19]); dead code is unrelated to unreferenced functions (+0.01 [+0.01]); documentation and verification have the right sign (risk rises as documentation or tests fall; verification AUC for test files 0.08 [0.07]).
5. **The mix describes file role.** K-means (k=6) on within-repo ranks gives profile types: small test files (low everywhere), big complex core files, exposed big core files, interface and header files, debt-heavy small files, tiny simple files. Agreement with role (test, header, docs, vendor) AMI 0.22 [0.14]; with language 0.06 [0.03], repo 0.04 [0.02], size quartile 0.07 [0.06]. The types recur across languages and repos.
6. **Very stable over two years** (same-file rank correlation 0.95-1.00, as stable as size, 0.99).
7. **Churn and stability are one process axis, not structure** (master database, 27,957 files with history in 494 repos): churn vs stability rho -0.88; churn vs raw commit frequency +0.97; vs ownership entropy +0.55 and silo risk +0.67; vs size +0.29; vs every keyword-based metric |rho| <= 0.11. They are unpredictable from keyword densities (R2 0.05-0.08), which the structural metrics are not (R2 0.4-0.9 for most).

## Do they predict later fixes or change? (7 repos with fix labels, file-intervals, forward-in-time split)
**Without history (stale engine, 13-repo scans, 35,139 file-years):** adding the 10 structural metrics to size gains AUC +0.013 (raw label), +0.010 (v3c), +0.004 (regression); beyond size and prior fixes +0.003 to +0.006. Within size quartiles AUC 0.58-0.63 for tech debt, verification, state flux, cognitive load (range across repo-quartiles 0.3-0.8). Relation to later size change |rho| <= 0.08.
**With history (main engine, as-of scans, 35,287 file-intervals; churn nonzero on 69% of files, stability on 99%):**
| label | size | + churn and stability | + 9 structural | size + prior fixes | + churn and stability | + 9 structural | + all |
|---|---|---|---|---|---|---|---|
| raw | 0.784 | 0.799 | 0.797 | 0.815 | 0.817 | 0.819 | 0.823 |
| v3c | 0.816 | 0.832 | 0.826 | 0.833 | 0.839 | 0.838 | 0.844 |
| regression | 0.815 | 0.834 | 0.814 | 0.821 | 0.836 | 0.819 | 0.834 |
* Churn and stability gain +0.015 to +0.019 AUC over size alone under all three labels; beyond prior fixes +0.002 (raw), +0.006 (v3c), **+0.015 (regression label)**. The structural nine gain +0.013, +0.010 and -0.001 over size. Process beats structure, most clearly under the cleanest label.
* Within size quartiles (v3c, median over repo-quartiles): churn 0.65, raw churn frequency 0.65, ownership entropy 0.61 (stability 0.41, i.e. 0.59 inverted), against 0.58-0.63 for the structural metrics.
* **Later change:** churn correlates +0.26 [-0.13, +0.47] with relative size change over the next interval within size quartile (stability -0.17; ownership entropy +0.18); the structural metrics stay at 0.00-0.08. Churn is the only one of the 13 with a visible relation to later change.
* Churn counts commits, so its link to "fix" labels may partly reflect that busy files collect more fix-worded commits.

## Does measured reach beat the file-level API-exposure score? (ripple test)
670 sweeps (at least 10 functions swept, 13 repos); candidates: callers of the swept functions (one and two hops), functions in the same files, and a random sample of the rest (1.94 million functions); outcome: edited outside the sweep in the sweep quarter or the next.
* Edit rates: 1-hop callers 23.6%, same file not callers 18.6%, 2-hop callers 17.7%, everything else 12.4%.
* Pooled odds ratios (bootstrap over sweeps): 1-hop caller **1.28 [1.10, 1.65]**; 2-hop caller 1.04 [0.88, 1.25]; same file 1.58 [1.45, 1.68]; size 1.62 per log unit; fan-in 1.12; **file `api_exposure` rank 0.72 [0.66, 0.79]** (more exposed files are edited less, given the rest).
* AUC for a follow-on edit (5-fold grouped by sweep): size, fan-in and same file 0.644; plus the API score 0.646; plus measured reach 0.644; plus both 0.646. Neither adds anything.
* Sweep level: median 17 functions swept, 19 one-hop callers in 7 files, 16 two-hop callers; a median 20% of the one-hop callers are edited; rank correlation swept size vs callers +0.47, callers vs callers edited +0.81.
So measured reach marks a set with about twice the base edit rate and sizes the work, but does not rank functions better than size and file; the file-level API-exposure score does not predict ripple.

## Reading and recommendations
* The vector is useful as a **file-role fingerprint**: stable, language-independent, separating tests, headers and large core files. That is a descriptive use that the outcome studies do not contradict.
* Several metrics are **one family's density in a sigmoid**; show concurrency, dead code and secrets as counts or filters, and rename `safety_score` (it measures mutation).
* **Churn and stability carry the only independent information** (process, not structure) and the only link to later change; collapse them into one "recent activity" axis and make history-aware scans (worktree, as-of mode) the default for any scan meant for history.
* **Surface area as measured reach** (callers, ripple, blast radius) is better defined than the sigmoid and sizes sweeps well, but its predictive value is no better than size and file; present it as scope planning.
* **Do not claim risk** from any of them: gains over size are about 0.01 AUC for structural metrics, 0.015-0.02 for process metrics.
Caveats: 13-repo scans used the stale engine; the history-aware test covers 7 repos and one engine version; label artefacts as in `turn_edit_kinds_vs_fixes.md`; the ripple outcome is any organic edit, not proven causation; others in the ripple test are a random sample (up to 3,000 per sweep).
