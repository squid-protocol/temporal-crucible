# CGT — call networks over a codebase's life (SCORED)

**Type:** confirmatory (CGT-1..5), plus labelled post-hoc checks
**Registered:** 2026-11-08 20:52 (34e16f7, `docs/cgt_hypotheses.md`); scorer committed 20:55 (d0859d7,
`tools/cgt_eval.py`) before its one run.
**Data:** 390 quarterly snapshots (curl 105, OpenSSL 110, libarchive 70, harfbuzz 62, nDPI 43), 385 quarter pairs;
2,399 sampled commits scanned at commit and parent (gitgalaxy 8f96d76ba, history off). Raw output
`gitgalaxy/cgt-study/cgt_result.json` (outside the repo).

## Registered verdicts

| id | claim | result | verdict |
|---|---|---|---|
| **CGT-1a** | static most of the time (median quarterly rewiring < 2%) | median 0.1–1.4% of edges among persisting functions; 5 of 5 repos | **✓** |
| **CGT-1b** | change in jumps (top decile ≥ 40% of rewiring) | curl 51%, OpenSSL 46%, libarchive 77%, nDPI 47%; harfbuzz 34%; 4 of 5 | **✓** |
| **CGT-1c** | burstier than churn (Gini(R) − Gini(C) > 0, lo > 0) | curl +0.19 (lo +0.07), libarchive +0.25 (lo +0.003); OpenSSL −0.06, harfbuzz −0.02, nDPI +0.12 (lo −0.13); 2 of 5 | **✗** |
| **CGT-2a** | release quarters rewire more beyond churn | residual difference +0.15, p 0.028 (bar 0.005); 150 release quarters of 385 | **✗** |
| **CGT-2b** | quarters adding C files rewire existing code more | Spearman +0.05, p 0.10 | **✗** |
| **CGT-3a** | regression fixes rewire more than CVE fixes at equal size | raw 39% vs 28%; CMH OR 1.24, p 0.17 | **✗** |
| **CGT-3b** | CVE fixes rewire less than other fixes at equal size | **opposite direction:** OR 1.52 (CVE fixes rewire *more*), z +1.85 | **✗** |
| **CGT-4** | rewired files attract later fixes beyond churn (prior: null) | OR 2.02 over (repo × churn quintile), p < 1e-200; 11,124 rewired file-quarters | **✓** |
| **CGT-5** | name-free call network identifies a project across ≥ 5-year eras (bar 90%) | 390 of 390 (100%); keyword mix (descriptive) 386 of 390 | **✓** |

## Descriptive

- Totals: rewiring among persisting functions is a fifth of growth (curl 8,643 vs 43,858 edges; OpenSSL 33,659 vs
  145,567): networks mostly *grow*; existing wiring rarely changes.
- CGT-3 rewiring rates by class (≥ 1 internal call edge added or removed): regression 39%, CVE fix 28%, control (non-fix
  commits) 27%, other fix 23%, **extrinsic 14%**. Extrinsic vs other-fix OR 0.43 (z −4.4): platform, compiler and
  dependency fixes are the ones that leave the call graph alone. Median C diff: 8–15 lines in every class.
- Releases found per repo: curl 111, harfbuzz 74, nDPI 21, OpenSSL 11, libarchive 11 (tag conventions differ).

## Post-hoc checks (EXPLORATORY: not verdicts, found after scoring)

- **CGT-4 and file size.** Adding file size (functions in the file, quintile) to the strata cuts the odds ratio from
  2.02 to **1.34** (z 11.2, p < 1e-29). About half of the registered effect was size; the rest survives. Prior fixes
  (recidivism, the programme's strongest predictor) are not yet controlled.
- **CGT-5 is easy here.** Five unrelated repos, each scanned by its own engine; the keyword mix scores 99% too. The
  result shows the call network is a stable identity across decades, not that it is better than other signals at it.

## Reading

- **The owner's picture holds in part.** Call networks are static most quarters (1a) and change in jumps (1b), but in
  three of five repos the jumps are no burstier than the code volume (1c). Rewiring follows how much code changes,
  mostly; curl and libarchive are the exceptions.
- **Jumps do not line up with releases or new files** at the registered bar. Release quarters lean positive (p 0.03).
- **Fixes do change call graphs, and CVE fixes are not the quiet ones.** A quarter of CVE fixes add or remove an
  internal call, more than other fixes of the same size. FORT's "CVE fixes add guards" is about statements; at the call
  level they also reroute (e.g. into a new check or helper). The quiet class is extrinsic work.
- **Rewiring marks files that need more fixes later**, beyond churn, and half of that beyond file size too. Unusual
  for this programme, where structure usually reduces to size and churn; it needs the recidivism control and an
  unseen repo before it counts as more than a lead.

## Follow-ups (for unseen data only)

- CGT-4R: rewiring vs later fixes with churn, file size **and prior-fix count** controlled, on repos not used here
  (e.g. libxml2, PostgreSQL, libgit2), registered first.
- CGT-3R: CVE fixes vs other fixes, rewiring, on unseen repos; split into added vs removed edges (new check helper vs
  removed call).
- CGT-5H: identification among *related* codebases (forks, the DOOM ports, OpenSSL vs BoringSSL vs LibreSSL), where it
  is not trivial.
- CGT-6: GitGalaxy's own PRs by type (deferred).
