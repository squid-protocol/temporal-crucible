# Sensor design: activity (replaces `hist_churn` and `hist_stability`)

**Status: design with evidence and a back-tested mock-up (section 11); exploratory.** Replaces the two history columns (persisted as `risk_churn`, `risk_stability`; named `hist_churn`, `hist_stability` on `main`). Test: `tools/sensor/activity_horizons.py` (output: `activity_horizons_output.txt`); as-of scans: `tools/turn/surface_area/hist_scan.py`.

## 1. The question the sensor answers
*How active is this file, how long has it been settled, and who is looking after it?* The intent in the engine's own docs was a short-term to long-term pair: churn (how often it changes lately) and stability (how long it has been untouched). The aim here is to keep that intent and make the pieces actually independent.

## 2. What the docs say, and what the code does
| Source | Says |
|---|---|
| Wiki `docs/wiki/02-15-chronometer.md` | The Chronometer measures **churn** (frequency of changes) and **stability (age)** from Git history; it sweeps only the past 12 months, halts once it has mapped 50% of active files or 5,000 files or 15 seconds, and also provides an author map (ownership entropy, silo risk) |
| Wiki `docs/wiki/08-06-deep-churn.md` | **Deep Churn** = relative commit volatility, "highlights active hotspots"; commit volume divided by the square root of the file's "age in weeks", log-normalised against the repository maximum; Future Work: weigh commit size and separate trivial formatting commits from substantive changes |
| Wiki `docs/wiki/08-10-file-stability.md` | **File Stability** = where a file sits on the repository timeline (RECENT / SETTLED / ESTABLISHED BASELINE), "not treating older code as inherently problematic"; Limitations: one rogue formatting commit resets the timeline; Future Work: ignore massive automated formatting commits |
| `docs/vector_formulas.md` 12a | **stability** = (repo newest time minus the file's last-modified time) / (repo timeline) x 100, capped at 100; 50 if not git-tracked |
| `docs/vector_formulas.md` 12b | **churn** = commits in the 12-month sweep / sqrt(weeks since the file's last modification, minimum 1) |
| `docs/vectors.md` | `hist_stability` and `hist_churn` are the **PROMOTE** pair: the one layer the record supports as carrying defect lift beyond size; but "ablated to zero on every recorded row" because every scan sets `GITGALAXY_DISABLE_GIT_HISTORY` (temporal-crucible#29) |
So both columns depend on the same term, **how recently the file last changed** (the wiki pages call it the file's "age", but the code input is time since the last modification, not since creation; the wiki's own Future Work items, separating formatting commits and weighing commit size, are what the mechanical share and the sweep detector address): churn divides by it, stability is it. That is why they collapse into one axis, whatever the intent.
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

## 4. Related tools and the research behind the ideas
Other tools that report file history (repowise, CodeScene) fold change frequency, ownership concentration and change spread into a per-file score. We do not copy their windows, weights or names; the ideas they draw on are older and public: relative churn (Nagappan and Ball), ownership concentration (Bird et al.), change entropy (Hassan), co-change coupling (D'Ambros et al.), prior-fix history (Ostrand and Weyuker; Kim et al.), and the survivor effect (a dormant file with no recent commits should not be read as neglected ownership). What our measurements say about these ideas: **the 365-day commit count carries the prediction; shorter and longer windows add nothing; ownership concentration is independent but not predictive.** Design stance (guide section 4.1): history is context, kept as its own sensor and never blended; ownership readings are **activity-gated** because dormant stable files should stay quiet; references are repo percentiles; the mechanical share separates sweeps from organic edits; and one risk we avoid on purpose is sharing a label rule between the predictor and the outcome (the label-sharing problem the crucible documents). What is distinctive in our version: rename-aware histories, the mechanical share, and the back-test record.

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

## 11. Mock-up and back-test (curl, libxml2, libgit2)
`tools/sensor/activity_mockup.py` builds the proposed panel for every history-aware snapshot (curl 26, libxml2 28, libgit2 16) with **rename-aware history** (`git log -M --name-status`): 365-day and 90-day commits, days since the last change, age and lifetime commits, top-author share and whether that author is still active, mechanical share (sweep detector), reach (PageRank), and a role tag. It then checks each axis and each worklist against what happened next. Outputs: `activity_mockup_<repo>_output.txt`, `activity_combined_output.txt`; combined lists: `tools/sensor/activity_combined.py`.

**Independence (curl).** The proposed axes are nearly orthogonal: activity vs age +0.09, vs ownership share -0.06, vs mechanical share +0.27, vs reach +0.25 (activity does track size, +0.63). The engine pair is -0.85. Dormancy stays tied to activity (-0.73), so folding it into the activity axis was right.

**Prediction: later fix (v3c), forward split, AUC**
| repo | size | + engine churn/stability | + panel (5 axes) | size + prior fixes | + panel |
|---|---:|---:|---:|---:|---:|
| curl | 0.813 | 0.828 | **0.843** | 0.836 | 0.853 |
| libxml2 | 0.860 | 0.874 | **0.883** | 0.875 | 0.881 |
| libgit2 | 0.790 | 0.767 | **0.798** | 0.786 | 0.797 |
The panel beats the engine pair by +0.015, +0.009 and +0.031 and size by +0.030, +0.023 and +0.008. **Which axis earns it** (one added to size; curl / libxml2 / libgit2): reach (PageRank) +0.018 / +0.016 / +0.012; recent activity +0.015 / +0.013 / -0.009; dormancy +0.011 / +0.009 / -0.008; mechanical share +0.005 / +0.003 / -0.011; ownership +0.001 / +0.001 / 0.000; age +0.001 / 0.000 / -0.003. Two axes carry the prediction, **reach and recent activity**; age, ownership and mechanical share are descriptive. libgit2 is a repo where recent activity does not help in the later half (the engine pair even hurts, -0.023), also under the raw label; it is real, not a rename artefact (the result is unchanged after following renames).

**Worklists: later fix (v3c) rate vs all active files, pooled over snapshots, interval by resampling snapshots**
| list | curl | libxml2 | libgit2 | reading |
|---|---|---|---|---|
| L1 hot now (top decile of 365-day commits) | x2.47 [2.19, 2.71] | x1.82 [1.54, 2.08] | x2.21 [1.76, 2.73] | consistent; source files only: x1.79 / x1.52 / x1.43 |
| L2 hot and concentrated (top author 60%+ and owner inactive or 90%+) | x1.00 | x1.48 | x0.63 [0.45, 0.93] | direction varies: describes who looks after a file, not risk |
| L3 dormant but depended on (2+ years quiet, reach top decile) | n = 21 | n = 35 | n = 80 | too few to test (curl has one dormant file); later-change lifts x1.09 / x2.40 [0.92, 5.42] / x1.15 |
| L4a hot, mostly organic edits | 68.4% | 60.0% | 22.7% | |
| L4b hot, mostly mechanical edits | 67.2% | 70.2% | 20.0% | **no difference**: the mechanical share does not separate fix-prone hot files |
**Combined: activity x reach** (source files, active in the last year; rate vs all active source files, curl / libxml2 / libgit2): hot only x1.97 / 1.85 / 2.06; **hot and high reach x2.08 / 1.97 / 2.56**; reach only x1.15 / 1.43 / 1.47; **high reach but quiet x0.62 / 0.95 / 0.76** (below base). Reach adds to activity a little (most in libgit2) and is no risk read on its own: **quiet foundations are not where fixes land**, which is the same activity-gating lesson repowise builds into its ownership markers.

**What the HEAD panels show.** curl's hot list at 2025-12-29 is led by `lib/vtls/openssl.c`, `lib/http.c`, `lib/url.c` (26 years old; the last two 60-68% mechanical edits), plus three CI workflow files in the top six when roles are not separated; libgit2's dormant-but-depended-on list is a real worklist of foundation files untouched for 2-3.5 years with reach above the 96th percentile (`src/util/runtime.c`, `thread.c`, `posix.c`, `libgit2/object_api.c`, `buf.c`, `util/win32/utf-conv.c`); libxml2 has 52 files dormant 2+ years of 146; curl has one.

### Design changes this forces
1. **Rename-aware history is mandatory.** Path-following history made every file moved by libgit2's 2022 source reorganisation look 3.5 years old (`repository.c`, a 2008 file, read as new); with `-M` it reads 15.0 years and the dormancy list becomes believable. The engine's file mtime cannot do this.
2. **Role tag, default to source.** In curl 44% of files are tests or docs and CI workflows lead the hot list; lists should default to source with the role shown, and the lift for source-only lists is lower (x1.4 to x1.8) than for all files.
3. **Fold dormancy into the activity axis** (rho -0.73); keep age, ownership and mechanical share as context, not predictors.
4. **Pair activity with reach in the product.** The strongest simple worklist is hot x high reach; reach stays its own sensor, and "quiet but central" is shown as stable foundations, explicitly not a risk list.
5. **Show "not measured" for reach on files outside the call graph** (YAML, shell, docs all rank at the same tied percentile).
6. **For dormant files show the last author's status**, not a top-author share (it reads 0%).
7. **L2 stays a description.** Its direction changes between repos (x1.00, x1.48, x0.63); present it as ownership context.

### Caveats
Three repos and a forward split on 16-28 snapshots; the later-fix outcome counts files touched by fix commits, so hot files are fix-prone partly by construction (the AUC gains over size are the fair test); "any later commit" is saturated (85% of active curl files) and not informative; labels have the known artefacts; L3 is underpowered; reach is PageRank over the engine's resolved call graph only.

## 12. Engine command (2026-11-17)
`gitgalaxy activity` (engine PR #8575, wiki 08-27) implements sections 5 and 6: the readings per file (365 and 90 day commits, dormancy, age and lifetime commits, authors, top-author share, owner active), rename-following history, the hot / ownership-context / dormant worklists, and quiet foundations with a scan. **Check:** `tools/sensor/activity_engine_check.py` recomputes every reading the mock-up's way and compares file by file: identical for all 8 readings on 24,149 files (curl, libgit2, libxml2); output `activity_engine_check_output.txt`. It checks the implementation, not the rename logic (shared). Not in the command: mechanical share (did not separate fix-prone hot files), change entropy, co-change scatter, persistence in the scan database (section 8 items 2 and 5), retiring the old gauges. A "source" role from `reach.role()` includes build files and licences, so the command filters by the engine's language table.
