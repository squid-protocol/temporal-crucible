# Would GitGalaxy have outlined the scope of a sweep? (work branch `turn/forecast`; exploratory, not registered)

**Test.** For 767 sweeps (the same call or macro name swapped in at least 5 functions in one quarter, 13 repos), predict the set of functions that were swept using only the snapshot before the sweep, and compare with the functions actually swept. Predictions: **A** = callers of the old name in the engine's resolved call graph (possible when the old name is a function defined in the repo: 431 sweeps); **B** = functions that contain the old name by text search (`git grep` at that commit, mapped to function line ranges from the scan). `tools/turn/scope_test.py`, `scope_report.py`.

| prediction (medians over sweeps) | sweeps | precision | recall | recall >= 0.8 | precision >= 0.8 | median set size |
|---|---|---|---|---|---|---|
| A: GitGalaxy call-graph callers of the old name | 417 | 0.83 | 1.00 | 88% | 53% | 25 |
| B: text search, same sweeps | 431 | 0.74 | 1.00 | 96% | 44% | 30 |
| A union B | 431 | 0.74 | 1.00 | 97% | 44% | 30 |
| B on all sweeps, including names the engine cannot resolve | 757 | 0.62 | 1.00 | 96% | 38% | 41 |

By sweep size (callers vs swept): 5-20 functions precision 0.74 (260 sweeps), 20-60 0.89 (114), 60-200 0.95 (34), 200 or more 0.99 (9); recall is 1.00 in every band.
Scope features: median 7 files touched (interquartile 3-12); the three biggest files hold a median 70% of the swept functions; the predicted and actual file sets overlap at Jaccard 0.80; swept functions are not hubs (7% in the top in-degree decile; 10% is chance).

## Reading
* **Every swept function is a caller of the old name** (recall 1.00 for both methods), so the call graph and a text search both give a complete upper bound on the work.
* **The engine is more precise than text search** on the sweeps it can resolve (0.83 vs 0.74): it does not count comments, declarations, strings or definitions, and it works at function and file units. In large sweeps nearly every caller is swept (0.95-0.99).
* **The engine cannot help when the old name is not a repo function** (standard-library and builtin names, unresolved macros: 336 of 767 sweeps); text search then still finds the scope (precision 0.62 across all sweeps).
* **What GitGalaxy adds beyond a grep:** function and file units with sizes, who sits where in the call graph (swept functions are leaf-side, not hubs), and ripple analysis. Ripple (callers of the swept functions) and effort (lines per function) were not tested here.
* The unswept 17% of callers (median) are the exceptions or stragglers; no feature predicting which callers are skipped was tried.
Caveats: precision is against sweeps already detected (threshold of at least 10 functions in a quarter for detection, at least 5 here); a sweep spread over several quarters is scored on its largest quarter; names are matched as text (the last component of a dotted or scoped name).
