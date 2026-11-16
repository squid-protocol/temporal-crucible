# Can sweeps be forecast? (work branch `turn/forecast`; exploratory, not registered)

767 migrations (old name replaced by a new name in the same functions, one quarter) across 13 repos. 378 are "resolvable": both names are functions defined in the repo, so GitGalaxy's call graph can count callers. Tools: `tools/turn/sweep_forecast.py`, `intent.py`, `swap_check.py`.

## What kind of change a "swap or rename" is
Defined from the tree-sitter diff (callee and macro names added about equal names removed, length unchanged, nothing else structural; 90% inside a sweep). How the engine records those edits (libgit2 / curl / redis): resolved call edges change in 77 / 58 / 73%, keyword-family counts in 33 / 67 / 63%, neither in 7 / 13 / 15% (unresolved stdlib or macro names). By contrast grow, shrink and rewrite edits change keyword counts in 96-100%. So it is mainly a call-graph change with a keyword-family change alongside in many cases.

## Is the intent legible?
By name pair alone, simple rules classify 59% of migrations (API rename with shared prefix 19%, wrapper/namespace/version suffix 19%, test or assertion framework 9%, stdlib to project wrapper 7%, naming convention 5%); 41% need context. Commit subjects often state it ("Fix last references to deprecated git_buf_free", "RDMF: redisLog -> serverLog", "Fixing DeprecationWarning (logger.warn)", "[Python 2 to 3] Main six fixes"); for generic names (`free`, `Equals`) the commit search is too noisy to read.

## Forecasting tests
* **Size is nearly determined once a sweep happens.** Across the 378 resolvable migrations the median share of the old name's callers that were swept is 0.90 and 79% swept at least half of them (Spearman between callers and functions swept 0.51 overall; libgit2 0.92, curl 0.93, sphinx 0.77, redis 0.28, libxml2 0.23, tigerbeetle -0.27). The caller count is the ceiling for how much work a migration can be; whether it happens is another question.
* **No lead time.** The new name is first defined in the sweep quarter itself in 76% of cases (1-3 quarters earlier 3%, 4 or more earlier 21%; median 0): new names usually arrive together with the migration, so "a new name appeared" is not an early warning.
* **Deprecation precursor in one third.** A commit mentioning "deprecat" and the old name in the four quarters before the 25 largest sweeps per repo: 91 of 277 (33%; curl 16/25, sphinx 15/25, prometheus 13/25, redis 1/25).
* **Families are renamed repeatedly.** 44% of migrations belong to a chain (the old name was recently a new name, or the new one is replaced later), for example git_buf_free to git_buf_dispose to git_str_dispose.
* **Name-pattern alert is not a forecaster.** An alert for "a new function whose name resembles an existing function with at least 10 callers" caught 46% of the resolvable large sweeps (161 of 352) but had precision of about 0% (157 of 767,845 candidate pairs became migrations within four quarters).

## Reading
Which API will be renamed, and when, is largely not forecastable from names or adoption timing in this data. What is forecastable is the size of the work once a migration is announced (about 90% of the old name's callers), and roughly a third of large sweeps carry an explicit deprecation signal beforehand. A sweep forecaster would need an upstream signal (deprecation notices, language or library version changes, release milestones), not structure.
Caveats: 378 of 767 migrations are resolvable; engine callers count only resolved calls; the deprecation search covers only the 25 largest sweeps per repo and uses commit subjects and messages; the alert test uses simple name morphology; exploratory.
