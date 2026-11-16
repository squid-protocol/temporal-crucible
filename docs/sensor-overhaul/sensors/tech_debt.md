# Sensor design: the debt ledger (from research to sensor)

**Status: design plus a working prototype; exploratory.** Replaces the sigmoid `risk_tech_debt` gauge. Prototype: `tools/sensor/debt_ledger.py` (output in `tech_debt_prototype_output.txt`); engine count check: `tools/sensor/debt_validity.py`.

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
