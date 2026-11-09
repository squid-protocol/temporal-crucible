# CGN — hubs, efficiency, bad shapes, concurrency and dead code in call networks (SCORED)

**Type:** confirmatory
**Registered:** 2026-11-08 21:08 (6b77908, `docs/cgn_hypotheses.md`); scorer committed 21:09 (e7a0b59,
`tools/cgn_eval.py`) before its one run. Same 390 snapshots and networks as CGT. Raw output
`gitgalaxy/cgt-study/cgn_result.json` (outside the repo).

## Registered verdicts

**A. Hubs**

| id | result | verdict |
|---|---|---|
| **A1** hubs persist 5 years | surviving hubs still in the top 5% after 5 years: curl 92%, OpenSSL 96%, libarchive 98%, harfbuzz 100%, nDPI 76%; in-degree rank correlation 5 years apart 0.81–0.94; 5 of 5 | **✓** |
| **A2** hubs are made early | 58% of 486 hubs born after the first snapshot became hubs within 2 years of birth | **✓** |
| **A3** preferential attachment | new calls into existing functions target the 70th–83rd in-degree percentile (null 50th), p 0.0005 in 5 of 5 | **✓** |

**B. Efficiency over time** (yearly snapshots, Kendall τ against time)

| id | result | verdict |
|---|---|---|
| **B1** more modular by directory | rises only in harfbuzz (τ +0.62); falls in OpenSSL (−0.67) and libarchive (−0.75); flat in curl and nDPI; 1 of 5 | **✗** |
| **B2** less cross-file wiring | falls only in OpenSSL (τ −0.75); **rises** in curl (0.53 → 0.74 of edges), libarchive (0.55 → 0.84) and nDPI; 1 of 5 | **✗** |
| **B3** centralises (more edges end in hubs) | rises in curl (τ +0.75), OpenSSL (+0.26), libarchive (+0.93), harfbuzz (+0.58); falls in nDPI; 4 of 5 | **✓** |

**C. Bad network shapes and later fixes** (file-years; strata repo × file size × churn × prior fix)

| id | result | verdict |
|---|---|---|
| **C1** files in call cycles | OR **1.20** (z 5.8), 11,028 exposed file-years | **✓** |
| **C2** duplicated wiring | OR 0.86: *fewer* later fixes | **✗** |
| **C3** highly coupled files (prior: null) | OR **1.76** (z 17.9), 10,135 exposed | **✓** |
| **C4** larger regression share of fixes in coupled files | OR 0.96 (z −0.8), 23,313 fix-file units | **✗** |

**D. Concurrency** (latest snapshots; only 48 concurrency/lock functions across the five C libraries)

| id | result | verdict |
|---|---|---|
| **D1** avoids the hubs | OR 0.61, p 0.20 | **✗** (underpowered) |
| **D2** sits at the periphery (k-core below median) | OR **0.24** (z −5.1) | **✓** (48 exposed) |

**E. Dead code**

| id | result | verdict |
|---|---|---|
| **E1** uncalled non-public functions are deleted sooner (size and age matched) | OR **1.08** (z 4.0), 71,903 exposed | **✓** (small effect) |

## Reading

- **Hubs are the stable skeleton.** Central functions stay central for years, mostly become central young, and new
  calls flow to them (rich get richer). Networks centralise over time (B3).
- **No sign of optimisation; mixed signs of decay.** Directory modularity falls in OpenSSL and libarchive, and
  cross-file wiring rises in three of five. That is closer to Lehman's law of increasing complexity than to systems
  tidying their networks. OpenSSL is the exception for cross-file wiring (its 3.x refactors).
- **Bad shapes do go with later fixes**, beyond file size, churn and the file's own fix history:
  - files caught in call cycles get fixes more often (1.2×);
  - highly coupled files much more (1.76×), against the prior. Earlier, centrality did not predict *CVE* fixes; here
    the outcome is any fix, with prior fixes held fixed.
  - **Duplicated wiring is the opposite** (0.86×): repeated callee sets look like routine, stable code (wrappers, table
    handlers), not copy-paste trouble.
- **"Harder to work out kinks" is not supported:** fixes in coupled files are no more often regressions.
- **Concurrency code sits at the periphery** of the network, not its core. In these C libraries it is rare
  (48 functions), so D1's null is a power problem.
- **Dead code dies slightly faster.** Uncalled private functions are deleted a little more often than called ones of
  the same size and age.

## Caveats

- C1/C3 strata use file size by function count; coupling also rises with file length within a quintile.
- Same snapshots as CGT and as earlier fix studies on these repos: C1/C3 need an unseen repo before they count as more
  than leads.
- D rests on 48 functions.

## Follow-ups (for unseen data only)

- CGN-CR: cycles and coupling vs later fixes on unseen repos (libxml2, PostgreSQL, libgit2), with LOC strata and
  CGT-4's rewiring in the same model (which carries the signal?).
- Concurrency in code that has it (Go, Java, Rust; the GitGalaxy weekly scans for Python async).
- Decay vs optimisation by era: do modularity drops follow contributor turnover or rapid-growth periods?
