# What fix work looks like, and six kinds of edit (work branch `turn/forecast`; exploratory, not registered)

## 1. Fix-edit catalog (tools/turn/fix_catalog.py, cat_report.py)
10,323 labelled fix commits in curl, libxml2, libgit2 and redis (FIXLIKE v3c labels; classes latent 220, regression 1,628, extrinsic 1,188, other-fix 7,287). For each changed C file the file before and after the fix was parsed with tree-sitter; the tables compare what the commit adds or removes, as a share of commits and a lift over other-fix (95% bootstrap interval).

| the fix ... | latent (CVE) | regression | extrinsic | other-fix | lift: latent | regression | extrinsic |
|---|---|---|---|---|---|---|---|
| adds a bounds/size/limit check | 55.5% | 32.0% | 21.5% | 36.8% | 1.51 [1.32,1.68] | 0.87 [0.80,0.94] | 0.58 [0.52,0.65] |
| adds any new if-condition | 70.5% | 44.7% | 31.7% | 51.0% | 1.38 [1.27,1.50] | 0.88 [0.83,0.92] | 0.62 [0.58,0.67] |
| adds a null check | 23.6% | 20.2% | 14.9% | 22.1% | 1.07 [0.81,1.33] | 0.92 [0.82,1.01] | 0.68 [0.58,0.77] |
| adds a return | 30.9% | 14.1% | 12.5% | 16.9% | 1.83 [1.45,2.20] | 0.83 [0.72,0.95] | 0.74 [0.64,0.86] |
| changes pointer syntax | 39.1% | 24.8% | 23.2% | 25.8% | 1.52 [1.27,1.76] | 0.96 [0.88,1.05] | 0.90 [0.82,1.00] |
| removes a free/release call | 5.9% | 2.5% | 1.2% | 1.8% | 3.34 [1.73,5.23] | 1.39 [0.97,2.01] | 0.67 [0.36,1.06] |
| adds a cast | 6.4% | 10.4% | 20.3% | 10.0% | 0.64 [0.33,1.01] | 1.05 [0.90,1.24] | 2.04 [1.79,2.33] |
| replaces an unsafe call with a safer one | 1.4% | 0.2% | 0.6% | 0.3% | 3.97 [0.00,9.94] | 0.72 | 1.72 |

Size of the work (median lines added+deleted; 90th percentile): latent 14 (140), regression 8 (82), extrinsic 9 (91), other-fix 8 (74); one file touched at the median in every class.
Reading: CVE fixes are more often bounds checks, new guards, early returns and pointer changes, and removing a free/release (double-free, use-after-free pattern); not distinctively null checks. Extrinsic fixes are casts and fewer guards (type and portability repairs). Regression fixes look like ordinary fixes at this resolution; the callee names over-represented in each class are repo-specific (libxml2 RelaxNG, curl DEBUGASSERT, Windows `CloseHandle` for extrinsic) and not general. The CVE guard result agrees in direction with the crucible's FORT-H1 (CVE fixes add guards 1.88x).
Caveats: file-level before/after diffs (a larger file diff folds several functions together); latent n=220; C only; the unsafe-to-safe swap is too rare to rank (3 latent commits).

## 2. Six kinds of in-place edit (tools/turn/archetypes.py)
K-means (k=6) on 12 features of each code edit to a surviving C function (length change, signature change, signed deltas of if-conditions, gotos, casts, pointer syntax, returns, calls, #if, names added/removed, in a sweep), fitted on curl, redis and libgit2, then assigned in the held-out expat and libxml2.
* **C0 small tweak** (35-48% of edits in every repo): no structural change.
* **C2 swap/rename** (16-39%): names added about equal names removed, 90% inside a sweep (libgit2 39%).
* **C3 signature-only** (10-24%).
* **C4 grow with logic** (9-20%): about +8 lines, +1.7 conditions, +4 calls, pointer changes.
* **C5 shrink/simplify** (1-8%): -2.75 length units, -4 conditions, -8 calls.
* **C1 big error-handling-style rewrite** (0.2-2.2%): +2.7 gotos, +3.2 conditions, +2.7 pointer changes, +4.6 calls; rare.
The mix is similar across all five repos, and held-out repos find their own clusters at distance 1.3-1.9 (in standardised units) from these. Edits beyond the 99th percentile of the discovery repos: 0.5% (libgit2), 0.8% (redis), 1.5% (curl), 0.5% (expat), 1.5% (libxml2).
Caveats: k-means with one k; clusters are descriptive, not tested against any outcome yet (linking archetypes to later fixes needs each edit's file, which the stored edits lack); C only.

## Not done
Function-level recidivism with the ledger's identity needs fix hunks mapped to functions across time, not yet built.
