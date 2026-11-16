# Function-level recidivism with the ledger's identity (work branch `turn/forecast`; exploratory, not registered)

Fix hunks were mapped to functions (old-file line ranges against the tree-sitter function ranges of the pre-fix file; `tools/turn/fix_funcs.py`), tied to lineage IDs, and counted per function-quarter under three labels: raw keyword label (`_xc`), v3c (`_xc2`, audited 0.80), regression class only. Four C repos (curl, libgit2, redis, libxml2), function-quarters every fourth snapshot (62k-106k rows per repo), covariates from the previous four quarters, outcome the next four, Poisson with function size as exposure, forward-in-time split (fit on each repo's earlier half). Models: churn and age; + the file's prior fixes; + the function's own prior fixes (last four quarters and ever); + both; + the function's fixes counted under naive path-and-name identity instead of lineage; + edit kinds. Bootstrap by function (100 draws).

## Result
AUC for "any fix in the next year" (later half of each repo):
| label | repo | churn+age | + file | + function | + function and file | + naive identity | + edit kinds |
|---|---|---|---|---|---|---|---|
| raw | curl | 0.741 | 0.771 | 0.746 | 0.772 | 0.772 | 0.773 |
| raw | redis | 0.768 | 0.805 | 0.781 | 0.809 | 0.808 | 0.810 |
| raw | libxml2 | 0.691 | 0.701 | 0.694 | 0.704 | 0.704 | 0.703 |
| raw | libgit2 | 0.698 | 0.713 | 0.703 | 0.715 | 0.713 | 0.716 |
| v3c | curl | 0.741 | 0.758 | 0.744 | 0.757 | 0.757 | 0.758 |
| v3c | redis | 0.777 | 0.793 | 0.780 | 0.795 | 0.795 | 0.796 |
| v3c | libxml2 | 0.710 | 0.712 | 0.712 | 0.714 | 0.714 | 0.712 |
| v3c | libgit2 | 0.774 | 0.785 | 0.776 | 0.786 | 0.785 | 0.786 |
| regression | curl | 0.734 | 0.738 | 0.734 | 0.739 | 0.739 | 0.739 |
(regression-only: libxml2 0.772 to 0.774, libgit2 and redis have 19 and 70 test fixes and do not move.)
* **The recidivism signal lives at file level.** Adding the file's prior fixes to churn and age gains +0.002 to +0.037 AUC (largest: redis raw +0.037, curl raw +0.030). Adding the function's own prior fixes beyond the file gains +0.000 to +0.004.
* **It shrinks as the label is cleaned.** File-level gain, raw to v3c to regression: curl +0.030, +0.017, +0.004; redis +0.037, +0.016, 0.000; libxml2 +0.010, +0.002, +0.002; libgit2 +0.015, +0.011, 0.000. This matches the crucible's finding that label noise inflates recidivism: about half of it goes under v3c, nearly all of it under the regression-only label.
* **Correct identity barely matters at this horizon.** Lineage identity over naive path-and-name identity adds +0.000 to +0.002 AUC. Functions that had a fix rarely change name or file before the next window, so the identity bias that mattered for births, deaths and lifetimes does not matter for recidivism.
* **Edit kinds add nothing** (-0.001 to +0.001), consistent with the file-year result.
* Fitted rate ratios per log unit for the function's own prior fixes (v3c, with churn and age): last four quarters 1.05-1.11, ever 1.08-1.29.

Caveats: C only; function mapping depends on the pre-fix file's function ranges and on matching (path, name) at the interval's start snapshot, so fixes in renamed files or functions born within the interval are not attributed; sizes of the later-half test sets vary (libgit2 167 v3c fixes; regression arm very small); one split per repo; exploratory.
