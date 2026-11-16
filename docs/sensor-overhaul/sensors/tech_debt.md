# Sensor design: the debt ledger (from research to sensor)

**Status: design, prototype, and a validated v2 trial (section 9); exploratory.** Replaces the sigmoid `risk_tech_debt` gauge. Prototype: `tools/sensor/debt_ledger.py` (output in `tech_debt_prototype_output.txt`); engine count check: `tools/sensor/debt_validity.py`.

## 1. The question the sensor answers
*What self-admitted work is open in this file or function, how old is it compared with how this project normally behaves, who wrote it and are they still around, and is it sitting where someone is working right now?*

It is a **worklist and a culture descriptor, not a risk gauge.** Debt density adds nothing to fix prediction (the crucible's comment-profile study: +0.003 AUC beyond size, churn and history), and we do not claim otherwise. Its value is that a debt marker is an admission by the author, discrete, locatable, ageable and actionable by construction.

## 2. What the research says (and what each finding means for the design)
| Finding | Source | Design consequence |
|---|---|---|
| About three quarters of debt comments are eventually removed, but projects range from 38% to 98%, and median lifetimes from months to decades | `debt_lifecycle_exploratory.md` (9 C projects) | **Repo-relative.** Age means something only against the project's own repayment history; no global scale |
| `XXX` lives longest (median 3.0 y vs 1.1 for TODO and FIXME); `FIXME` is removed most often (86%); `HACK` 67% | same | Separate marker classes. `XXX` reads as a standing warning, not a to-do |
| Bare markers (6 characters or fewer, no explanation) are 3-8% of items | same | Flag bare markers; they carry no action |
| About half of repayments are by the person who wrote the debt (46-60%; 75-89% in one-maintainer projects) | same | **Owner still active?** is a useful flag; debt of departed authors needs a different path |
| Debt is repaid in big commits; fix commits repay less often only because they are small (RR 0.77 raw, 1.07 size-stratified) | `drp.md` (four unseen repos) | Do not expect bug fixes to repay debt; the cheap moment to decide a marker is **when a large change touches its file** |
| Open debt at HEAD is often old: libxml2 82% over 10 years; curl's six items all over 10 years; redis median 0.5 years | `debt_lifecycle_exploratory.md` | A fossil class exists; show it separately from fresh debt |
| File commenting culture persists for years; comment density, header coverage and debt density differ several-fold between projects | `comment_profiles_exploratory.md` | Compare a file with its own repo and with its own history, never across repos |
| Debt density does not predict later fixes | `cpf.md` | **No outcome claim** on this sensor |

## 3. What the engine can already give, and what is missing
* **Counting is sound.** Engine `state_planned_debt` (TODO-type) plus `state_fragile_debt` (HACK, FIXME, XXX, BUG, KLUDGE and others, several human languages) agree with a text search of the same commit: per-file Spearman **+0.84 to +0.97 over all files** and +0.74 to +0.93 over files with any marker, in eight repos (libgit2 +0.92, libxml2 +0.95, redis +0.84, curl +0.94, sqlmap +0.90, scapy +0.95, sphinx +0.97, prometheus +0.94). The engine counts slightly more (it knows more marker words and counts occurrences, not lines): totals 146 vs 129 in libgit2, 636 vs 549 in libxml2.
* **Why the gauge looked weak (+0.32 with debt markers):** the formula mixes five things into one sigmoid: planned debt (weight 1), fragile debt (weight 3), "irc" (weight 0.5), unreferenced-by-name orphans (weight 2) and duplicate logic (weight 5). Only the first two are debt markers. The raw material is good; the composite loses it.
* **Attribution to functions exists:** marker hits in the comment stream are assigned to the function whose line range contains them (`detector.py`, positional comment pass).
* **Missing:** marker **line numbers** are used internally but not persisted (only counts per function and file reach the database); **age** (needs git history: blame or the lineage ledger); **author** of the marker; **marker class** below the planned/fragile split.

## 4. The sensor
**Units.** Open markers (count, and per kLOC); by class (planned, fragile, standing-warning `XXX`); bare versus explained; age in years; **fossil share**; markers in active files; owner-active share; net flow per quarter (added minus repaid).
**The repo's own yardstick.** From the project's history: the share of past debt repaid within 1 and 5 years, and the age by which 90% of its repaid debt was repaid (p90). An open marker older than that p90 is a **fossil**: this project has almost never repaid debt that old, so either it is a standing warning or it is forgotten.
**Ranking for the worklist.** Fossils first; then the file's activity (commits in the last year, i.e. someone is already editing it); then owner inactive; then bare. The top of the list is "old debt in a file being changed now": the cheapest moment to decide.
**Actions the list suggests.** Delete the stale note; convert it to a tracked issue; or reaffirm it as a standing warning (`XXX`).
**Gauges at repo level.** Open markers per kLOC; median age; fossil share; repayment habit (within 1 year, within 5 years, p90); balance trend.
**Companion sensors from the same stream** (separate, not blended): commented-out code (about 93% precise after gitgalaxy#8255; listable), header-comment coverage (about 95% precise on curl), comment neglect (code grew 20% or more in a year while comments did not), danger-language comments (born-with signal 1.45-1.55x CVE fixes, replication inconclusive; present as description).

## 5. Prototype results (open debt at HEAD, four repos)
Ages from `git blame` at HEAD; the yardstick from each repo's own tracked history; "active file" = at least 5 commits in the last year; "author inactive" = no commit in two years.
| repo | open markers | repo habit: repaid within 1 y / 5 y | repaid debt: median / 90% within | median age of open | fossils | author inactive | fossils in active files |
|---|---:|---|---|---:|---:|---:|---:|
| libgit2 | 80 (77 TODO, 2 XXX, 1 FIXME) | 60% / 70% | 0.05 y / 2.0 y | 11.6 y | **92%** | 56% | 12 |
| libxml2 | 505 (499 TODO, 6 FIXME) | 22% / 35% | 0.85 y / 19.8 y | 21.1 y | **76%** | 80% | 26 |
| curl | 6 (all XXX) | 48% / 83% | 1.06 y / 5.8 y | 1.5 y | **33%** | 33% | 2 |
| redis | 77 (51 TODO, 17 XXX, 8 HACK, 1 FIXME) | 54% / 77% | 0.02 y / 1.9 y | 0.5 y | **25%** | 18% | 11 |
Reading: in libgit2 the debt that gets repaid is repaid fast (median under a month, 90% within two years), but what is open is a different population (median 11.6 years, 92% older than the repo has ever taken to repay). The same count of open markers means very different things in libgit2, libxml2 (a slow-repaying culture where 76% are fossils against a 19.8-year yardstick), curl (six old `XXX` notes in a header) and redis (young). A global threshold would misread all four. Example worklist rows: libgit2 `repository.c:2972` "TODO: reinitialize the templates", 14.2 years old, author inactive, file edited 15 times last year; curl `typecheck-gcc.h:617` "XXX: must not evaluate expr...", 18.6 years old, file edited 8 times last year.
Caveats: ages come from the marker line's last modification (rewordings reset it), so ages are a lower bound (curl's lifecycle study dates all six open items to over 10 years from first introduction, whereas blame dates three of them to recent edits of the same lines; the ledger across snapshots would give the original age); the yardstick uses the study's heuristics for what counts as a comment line; C family only; four repos.

## 6. Engine work to make this a product
1. Persist marker records: file, line, class, normalized text hash (small).
2. Age and author: from `git blame` on marker lines at scan time when history is available (as-of mode for historical scans), or from the lineage ledger across snapshots.
3. Repo yardstick: compute once per repo from history (repaid share within 1 and 5 years, p90), cache.
4. Split the composite: the ledger replaces the debt part; unreferenced functions and duplicate logic become their own sensors.
5. Say "not measured" when history is unavailable (the age, owner and yardstick parts), and still give counts.

## 7. Acceptance status (guide section 5)
| Test | Status |
|---|---|
| Not degenerate | open: marker counts are sparse (59% of files at zero); the repo-level gauges are not |
| Construct validity | **pass for the counts** (+0.84 to +0.97 with text search); age and fossil logic not yet validated against maintainer judgement |
| Not redundant | counts are independent of the other keyword gauges |
| Actionable | by construction (ranked list with file, line, age, owner, activity) |
| Outcome | not claimed; debt density does not predict fixes |
| Population replication | open: run the prototype on the master database repos with history |

## 8. Open questions
* Do maintainers want fossils surfaced, or do they treat old notes as documentation? (The `XXX` standing-warning reading suggests some are.)
* Is "file edited now" the right trigger, or should big refactors and sweeps open a "while you are here" list?
* Which marker words beyond TODO, FIXME, XXX, HACK are worth tracking across languages?

## 9. Trial v2: checking the sensor's flags against what actually gets repaid
`tools/sensor/debt_trial.py` tracks every TODO / FIXME / XXX / HACK comment through the whole non-merge history of the nine C projects of the lifecycle study (moves and rewordings continue an item; renames followed), so each marker has its **original age**, birth file and author. At every half-year date it takes the debt open then (72,163 item-observations) and records what the sensor would have shown: age, the repo yardstick **computed only from debt already repaid by that date** (no leakage), marker class, bare or explained, text length, the file's commits in the last year, and whether the author still has commits in the last two years. The outcome is the one a debt sensor can honestly claim: **was the marker repaid within two years** (items whose file was deleted are excluded). `tools/sensor/debt_trial_report.py`; output `debt_trial_output.txt`.

**A. The fossil flag means something.** Repaid within two years: fossils 6.9%, other open debt 22.0% (all repos). In 8 of 9 projects fossils are repaid less (curl 30.8% vs 48.1%, openssl 10.7% vs 54.3%, libgit2 6.2% vs 23.9%, libxml2 2.5% vs 10.9%); ndpi is the exception (15.2% vs 11.4%).
**B. The repo-relative yardstick is not a better predictor than plain age.** AUC for "will not be repaid in two years": raw age 0.636, age percentile within the repo 0.614, fossil flag 0.592, a fixed five-year threshold 0.592. The repo-relative form wins in 3 projects (curl, libxml2, openssl) and loses in 5. Keep it as the **explanation** (what is normal for this project) and for honest cross-repo reading, not as a better ranker.
**C. What predicts stuck debt: file activity and owner, not marker class.** Forward-in-time AUC for "repaid within two years" (fit on the earlier half of dates, scored on the later half, mean of nine repos): age alone 0.512; plus the repo yardstick 0.541; plus marker class and bare 0.544; **plus file activity and owner 0.613**; plus text length 0.609. Odds ratios per standard deviation: file commits in the last year **1.36**, author still active **1.42**, age **0.56**; marker class (`XXX` 0.97, FIXME/HACK 1.02), bare (0.96) and text length (0.93) do essentially nothing.
**D. The "cheap moment" is real.** Among fossils, repaid within two years: file with no commits that year **2.6%**, 1-9 commits 5.3%, **10 or more commits 12.6%**; author still active **10.0%** vs inactive **3.4%**. By class, all about the same (TODO 11.5%, FIXME/HACK 12.3%, XXX 11.7%; bare 10.4% vs explained 11.7%): the marker word does not say what will happen to it.
**E. Original age matters.** The blame-based prototype dated curl's `lib/urldata.h` XXX note to 0.2 years (a later edit of the line); tracking gives 22.1 years. Counts at HEAD match the lifecycle study (curl 6, libgit2 85, libxml2 505, redis 83).

### The ranked worklist and how it compares with repowise's
**Yes, the sensor now outputs a ranked, located, explained list, built the same way in spirit as repowise's "fix first".** Each row: file and line, marker, original age, a **stuck probability** (the model above: older, quieter file, owner gone), the file's commits last year, and the fossil flag. The ranking key is stuck probability times file activity (stuck items sitting where somebody is already working), which combines the two validated tendencies (C, D); it is a heuristic, and it has not been tested that surfacing the list changes what gets repaid.
| | repowise "fix first" | debt ledger v2 |
|---|---|---|
| Items ranked | findings from 59 detectors across families | debt markers only (one family) |
| Rank basis | severity x marker weight, ranked by impact and effort ("refactoring targets") | stuck probability x file activity |
| Validated against | bug fixes (AUC 0.737, a tie with lines of code) | **repayment**, the outcome a debt sensor claims (AUC 0.613; fossils repaid 6.9% vs 22.0%) |
| Located | file and function | file and line (resolved for 33-88% of markers from tracked text; the engine should persist positions) |
| Reason shown | detector and thresholds | age, fossil flag, activity, owner |
| Effort estimate | yes | **no** (no validated proxy yet) |
| Triage status and stable IDs | acknowledged, false positive, resolved; IDs survive edits | **no** (needs persisted marker IDs) |
What to add to match it: an effort proxy, persisted marker IDs with triage status, and the same list shape for the other sensors (complexity, mutation, concurrency, unreferenced functions).

### Design changes from the trial
1. **Use original age** (tracked through moves, rewordings and renames), not blame; needs the lineage across snapshots or a history walk, not a per-line blame.
2. **Rank by stuck probability and file activity;** drop marker class and bare from the ranking (they stay as filters and descriptors).
3. **Keep the repo yardstick as an explanation**, show raw age next to it, and never claim it predicts better.
4. **Owner status is a first-class field** (author still active in the last two years); it is the second strongest key.
5. **Persist marker positions and IDs in the engine** so lines resolve for every marker.
6. **No outcome claims beyond repayment**; debt density still does not predict fixes.
Caveats: C family and nine projects; marker detection uses the lifecycle study's comment heuristics; two-year horizon; one outcome; AUC 0.613 is modest, so the list is a prioritisation aid, not a forecast.
