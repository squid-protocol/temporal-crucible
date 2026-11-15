# Sweeps and fixes: label audit and a quasi-natural experiment (work branch `turn/forecast`; exploratory, not registered)

Seven repos with fix labels (`events/<repo>_xc2.json`, FIXLIKE v3c) and sweep data: libgit2, libxml2, redis, prometheus, sphinx, ripgrep, curl. Classes: other-fix, regression, extrinsic, latent. Tools: `tools/turn/sweep_audit.py`, `audit_report.py`, `sweep_exp.py`.

## 1. Are the fix labels contaminated by sweeps? No.
For each labelled fix commit, the call names added and removed in its diff were compared with the names swept in that quarter. A "sweep fix" has at least two of its changed names swept that quarter and they are at least half of all its changed names.
Result: **0.0-1.7% of fix commits per repo (other-fix 100 of 11,260 = 0.9%; regression 15 of 1,925 = 0.8%; extrinsic 8 of 1,297 = 0.6%; latent 2 of 226 = 0.9%)**; by commit-file mass 0.0-1.3%.
Sampled hits are mostly generic names (`error`, `warning`, `cl_assert`, `free`, `Errorf`) shared with ordinary fixes, so this is an upper bound. The dependent variable of the crucible's fix studies is not sweep-contaminated.
Caveat: the rule needs sweep names to match call tokens in the diff; a migration that renames something other than a call (types, macros without parentheses) would be missed.

## 2. Does sweep exposure predict later fixes beyond size, prior fixes and organic churn?
File-years as in CEIL (covariates over four quarters, outcome over the next four; every fourth snapshot; Poisson, log code size as exposure, cluster-robust by file). Rate ratios per log(1+count):

| repo | file-years | later fixes | prior fixes | organic edits | sweep edits | swept vs unswept, matched (MH) |
|---|---|---|---|---|---|---|
| libgit2 | 8,140 | 1,567 | 3.91 [3.26,4.69] | 0.91 [0.81,1.03] | 0.87 [0.75,1.00] | 1.32 [1.02,1.68] |
| libxml2 | 3,205 | 3,119 | 1.55 [1.30,1.84] | 1.01 [0.88,1.15] | 1.13 [1.05,1.22] | 2.85 [2.32,3.45] |
| redis | 5,116 | 2,127 | 1.88 [1.61,2.19] | 1.10 [0.98,1.24] | 0.84 [0.77,0.92] | 1.26 [0.96,1.60] |
| prometheus | 4,100 | 1,982 | 1.52 [1.33,1.74] | 1.14 [1.03,1.26] | 0.78 [0.71,0.86] | 1.02 [0.87,1.27] |
| sphinx | 3,835 | 3,751 | 2.27 [2.01,2.56] | 0.83 [0.75,0.93] | 0.92 [0.81,1.04] | 1.04 [0.87,1.26] |
| ripgrep | 580 | 201 | 0.93 [0.66,1.30] | 0.91 [0.73,1.15] | 0.48 [0.18,1.24] | 0.24 [0.00,1.26] |
| curl | 7,899 | 6,337 | 1.36 [1.23,1.50] | 1.08 [0.97,1.21] | 0.98 [0.93,1.03] | 1.16 [1.00,1.32] |

Reading:
* Prior-year fixes are the only consistent predictor (1.4-3.9x per log unit in six of seven repos); organic edit counts add little beyond them (0.83-1.14, intervals mostly include 1).
* **Sweep edits show no consistent effect on later fixes**: below 1 in redis (0.84) and prometheus (0.78), about 1 in curl, sphinx and libgit2, above 1 only in libxml2 (1.13). So sweep churn is not a defect signal, and there is no evidence that sweeps cause fixes.
* The matched swept-vs-unswept ratio is heterogeneous (libxml2 2.85, libgit2 1.32, others near 1) and disagrees with the continuous-control model, which says the strata are too coarse: swept files are API-heavy and differ from unswept files in ways size, prior fixes and organic churn do not capture. "Sweeps are quasi-random" is not supported; selection is by API use.
Caveats: fix files are matched to snapshot paths by name (renamed files lose their history); sweeps use discovery thresholds; labels are keyword-based; ripgrep is too small; this is exploratory and uses the crucible's CGR-style frame, not the registered one.

## 3. What follows
Sweep edits should be separated from organic churn in any process predictor (they inflate churn without carrying defect signal); the dependent variable needs no sweep correction; the natural-experiment design needs a stronger exposure than "file has a sweep edit", for example sweeps on APIs the file does not choose to use, or sweeps whose old name is removed from the whole repo at once.
