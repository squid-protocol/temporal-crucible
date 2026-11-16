# Sensor design: activity (replaces `hist_churn` and `hist_stability`)

**Status: design with evidence; exploratory.** Replaces the two history columns (persisted as `risk_churn`, `risk_stability`; named `hist_churn`, `hist_stability` on `main`). Test: `tools/sensor/activity_horizons.py` (output: `activity_horizons_output.txt`); as-of scans: `tools/turn/surface_area/hist_scan.py`.

## 1. The question the sensor answers
*How active is this file, how long has it been settled, and who is looking after it?* The intent in the engine's own docs was a short-term to long-term pair: churn (how often it changes lately) and stability (how long it has been untouched). The aim here is to keep that intent and make the pieces actually independent.

## 2. What the docs say, and what the code does
| Source | Says |
|---|---|
| Wiki `docs/wiki/02-15-chronometer.md` | The Chronometer measures **churn** (frequency of changes) and **stability (age)** from Git history; it sweeps only the past 12 months, halts once it has mapped 50% of active files or 5,000 files or 15 seconds, and also provides an author map (ownership entropy, silo risk) |
| `docs/vector_formulas.md` 12a | **stability** = (repo newest time minus the file's last-modified time) / (repo timeline) x 100, capped at 100; 50 if not git-tracked |
| `docs/vector_formulas.md` 12b | **churn** = commits in the 12-month sweep / sqrt(weeks since the file's last modification, minimum 1) |
| `docs/vectors.md` | `hist_stability` and `hist_churn` are the **PROMOTE** pair: the one layer the record supports as carrying defect lift beyond size; but "ablated to zero on every recorded row" because every scan sets `GITGALAXY_DISABLE_GIT_HISTORY` (temporal-crucible#29) |
So both columns depend on the same term, **how recently the file last changed**: churn divides by it, stability is it. That is why they collapse into one axis, whatever the intent.
**Two things to correct in the docs.** (1) The "ablated in every recorded scan" statement does not match the v2.12.0 master database, where sampled files carry churn in 21% and stability in 36% of cases (243 and 488 of 580 repos). (2) History-aware scans of historical commits work on `main` (`GITGALAXY_HISTORY_ASOF=1`, detached git worktree); the installed `galaxyscope` loads a stale copy without it, and `historical-call-graph-gif` exports plain trees with no `.git`.

## 3. What the research says
| Finding | Source |
|---|---|
| Churn is the strongest single structure-adjacent feature pooled (AUC 0.859, on par with a line count); change entropy (Hassan, `HCM1_LD_30`) is the only feature to beat a line count out of selection (AUC 0.868 vs 0.830); recidivism is the most replicated result but label-dependent | quoted in `vectors.md` from `incremental_value.md`, `centrality_bands.md`, `bh_eval.md` |
| With history on (7 repos, 143 as-of scans): churn and stability add +0.015 to +0.019 AUC over size under all three fix labels, and +0.015 beyond prior fixes under the regression-only label; only churn relates to later change (rho +0.26) | `docs/turn_surface_area.md` |
| The two columns are one axis: within-repo rank correlation -0.86, PC1 93%, participation ratio 1.1 of 2. **Engine churn is the 365-day commit count (rho 0.96; 1.00 with `raw_churn_freq`); engine stability is days since the last change (rho 0.97)** | `activity_horizons_output.txt` |
| Real horizons separate, partly: 8 horizon features have participation ratio 2.9; the three recent windows (30, 90, 365 days) are one axis (1.6 of 3); authors in the last year is just commit count (rho 0.91); top-author share is its own axis (rho 0.30 with commits) and equals engine `silo_risk` (0.96); file age is independent of everything (|rho| <= 0.15) | same |
| **The 365-day window is the best horizon.** Within size quartiles, AUC for later fixes: 365-day commits 0.661, authors 0.645, 90-day 0.604, lifetime commits 0.605, 30-day 0.562, age 0.466, dormancy 0.629 (inverted; 0.371 raw). Relation to later size change: 365-day +0.26, 90-day +0.23, 30-day +0.15, dormancy -0.22, age -0.07 | same |
| **More horizons add nothing to prediction.** AUC with size plus prior fixes: engine pair 0.817 / 0.840 / 0.835 (raw / v3c / regression); the eight horizons 0.816 / 0.836 / 0.835; everything together no higher | same |

## 4. Comparison with repowise
| | GitGalaxy today | repowise ("change history" family, 10 detectors) |
|---|---|---|
| Windows | one 12-month sweep, plus a recency term shared by both columns | **90 days** (churn, entropy, congestion), **180 days** (prior defects, entropy half-life), per-function line age (code-age volatility) |
| Frequency | commits / sqrt(weeks since last change) | `churn_risk`: lines added in 90 days relative to the file's own lines (rewriting), repo percentile; `function_hotspot` at function grain |
| Spread of change | none | `change_entropy` (Hassan), `co_change_scatter` (shotgun surgery), `hidden_coupling` (co-change with no import edge) |
| Ownership | ownership entropy, silo risk (persisted) | `ownership_risk` (minor contributors, no dominant owner), `knowledge_loss` (sole author gone), `developer_congestion`; **activity-gated so abandoned-but-stable files stay silent** |
| Defects | none | `prior_defect` (fix commits in 180 days, same keyword rule as the benchmark label, shipped at neutral weight for explanation) |
| Use | two 0-100 values, one axis | blended into the 1-10 file score with a hard cap `min(3.5, 1 + structure)`; history alone can never push a file below 9.0 ("busy, not broken") |
| Their own caveat | | `prior_defect` correlates +0.59 with change entropy and +0.38 with churn; Popt gain within noise |
**Lessons.** (1) Repo-relative percentiles, not project-timeline ratios. (2) Activity-gate the ownership readings (the survivor effect). (3) Function-level history is the useful drill-down. (4) Change entropy and co-change scatter are the extra axes worth adding; our own record says change entropy is the one history feature that beat lines of code. (5) History is context, not a verdict: they cap it; we keep it as a separate sensor and never blend. (6) Their `prior_defect` shares its label rule with the benchmark, the label-sharing problem the crucible documents; do not copy that into a sensor.

## 5. The sensor
Three non-redundant axes plus context, all in plain units, each with a repo percentile:
1. **Recent activity** = commits in the last 365 days (best-supported window), with the last-90-day count shown as the "hot now" read. Drop the 30-day window (weakest) and the sqrt-recency formula. Zero commits in 365 days is shown as *dormant for N years* (days since last change, plain units), not as a second gauge: dormancy is the other end of the same axis (rho -0.77 with the 365-day count).
2. **Age and lifetime** = years since the file's first commit and commits ever. Descriptive and independent (rho <= 0.15 with activity); not predictive (AUC 0.47); it answers "is this old and settled or new". Replaces the project-relative `hist_stability` ratio.
3. **Ownership concentration** = top author's share of the last year's commits, with *owner still active* (a top author with a commit in the last two years) and the number of authors as context (authors is commit count, rho 0.91). **Activity-gated:** report only for files active in the last year, so dormant stable files are not flagged. Engine `silo_risk` is the same quantity (0.96).
4. **Candidates needing engine work, untested here:** change entropy (Hassan, `HCM1_LD_30` exists in the Chronometer as of temporal-crucible#29) and co-change scatter; function-level line age.
**Net churn.** Sweeps are 16-44% of edits and carry no consistent defect signal; recent activity should be shown with its **mechanical share** (edits that belong to a detected sweep) so a rename wave is not read as activity.

## 6. Drill-downs (worklists)
* **Hot files by repo percentile** (where change is happening now), with mechanical share and owner concentration.
* **Hot and concentrated:** active file, top author above a threshold, or owner no longer active (knowledge-loss read); shares the debt ledger's *author inactive* flag.
* **Dormant but depended on:** no commit for N years and high reach (links to the reach sensor): the quiet files everything stands on.
* **Settled newcomers vs old and busy:** the age by activity split, as a map of the repo.

## 7. What it does not claim
No risk or defect claim. The measured relation is +0.015 to +0.019 AUC over size, equal to a single 365-day commit count; richer horizons add nothing. Churn counts commits, so busy files also collect more fix-worded commits (label sharing). Activity describes where change is, not whether it is a problem.

## 8. Engine work
1. **Replace the 12-month sweep with a whole-history walk** (one `git log --name-only` per scan is seconds per repo): needed for lifetime commits, age and author history; remove the 50%-of-files and 5,000-file halting, which truncates coverage on large repos.
2. **Persist** `commits_365d`, `commits_90d`, `days_since_last_change`, `first_commit_age_years`, `lifetime_commits`, `top_author_share_365d`, `owner_active`, `authors_365d`; keep `risk_churn`/`risk_stability` as deprecated aliases.
3. **As-of mode on by default for historical scans**; fix `historical-call-graph-gif` to scan from detached worktrees; correct the "ablated in every scan" text in `docs/vectors.md`.
4. **Report "not measured"** for non-git directories and shallow clones (the engine already neutralizes the latter).
5. Add change entropy and co-change scatter to the persisted set; add the mechanical share from the sweep detector.

## 9. Acceptance status (guide section 5)
| Test | Status |
|---|---|
| Not degenerate | open: engine churn is zero on 79% of files in the master sample (only repos with history); with a whole-history walk this should change |
| Construct validity | **pass**: engine columns equal the 365-day commit count (0.96) and days since last change (0.97) |
| Not redundant | **fails today** (the two columns are one axis, rho -0.86); the proposed trio is independent except activity vs dormancy, which is folded into one axis |
| Stable / state | state sensor by design (recent activity changes quarter to quarter); age is a trait |
| Role discrimination | not tested |
| Actionable | by construction (worklists above) |
| Outcome | reported: +0.015 to +0.019 AUC over size; not claimed |
| Population replication | partial: redundancy and size relations replicated on 27,957 files in 494 repos (churn vs stability -0.88); outcome tests are 7 repos only |

## 10. Open questions
* Is 365 days the right unit for fast and slow repos? (Tigerbeetle and sphinx move faster than libxml2.) Repo percentiles soften this; a per-repo window is the alternative.
* Does change entropy add information beyond commit count in our 13 repos? (Their record says yes for bug labels; untested here.)
* Should "owner active" use the top author or any of the top three?
