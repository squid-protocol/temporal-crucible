# CGR — replication of CGT, CGN and CGK on eight unseen repositories in five languages (SCORED)

**Type:** confirmatory replication
**Registered:** 2026-11-08 21:38 (484aa93, `docs/cgr_hypotheses.md`, merged as #97); builder and scorer committed 21:40
(b649b21) before any scan or run.
**Data:** libgit2 (72 quarters), PostgreSQL (121), libxml2 (108), redis (65) in C; prometheus (Go, 55), commons-lang
(Java, 97), sphinx (Python, 75), ripgrep (Rust, 33). 626 snapshots, one engine (gitgalaxy 8f96d76ba), **0 scan
failures**. Fix labels: `tools/xc_harvest.py --exts` per language (walks and `events/*_xc.json` committed here).
Raw output: `gitgalaxy/cgr-study/cgr_result.json` (outside the repo).

## Verdicts (each claim in its originally observed direction; per-repo claims need ≥ 6 of 8)

| original claim | replication | verdict |
|---|---|---|
| CGT-1a static most quarters | median quarterly rewiring 0.0–3.0% | **✓ replicated** |
| CGT-1b change in jumps (top decile ≥ 40%) | 5 of 8 (libgit2 66%, commons-lang 65%, ripgrep 79%, sphinx 51%, libxml2 50%; PostgreSQL 29%, redis 36%, prometheus 39%) | **✗ not replicated** (bar 6) |
| CGT-1c burstier than churn (expected ✗) | 1 of 8 | ✗ (as expected) |
| CGT-2a / 2b releases, new files (expected ✗) | | ✗ / ✗ (as expected) |
| CGT-3a regressions rewire more than CVE fixes (expected ✗) | | ✗ (as expected) |
| CGT-3b CVE fixes rewire *more* than other fixes | libxml2 only (41 CVE fixes): 29% vs other fixes 37% | **✗ not replicated** |
| CGT-4 rewired files get later fixes beyond churn | OR **2.86** | **✓ replicated** |
| CGT-5 identity across eras | 603 of 603 (keyword mix 594 of 603) | ✓ (easy, as before) |
| CGN-A1 hubs persist 5 years | 57–97% still top 5%, ρ 0.84–0.98; 8 of 8 | **✓ replicated** |
| CGN-A2 hubs made early | | **✓ replicated** |
| CGN-A3 preferential attachment | new calls target the 67th–92nd percentile; 8 of 8 | **✓ replicated** |
| CGN-B1 / B2 modularity up / cross-file down (expected ✗) | | ✗ / ✗ (as expected) |
| CGN-B3 centralisation | 5 of 8 | **✗ not replicated** |
| CGN-C1 cycles → later fixes | OR **1.67** (z 21.5) | **✓ replicated** |
| CGN-C2 duplicated wiring → *fewer* fixes | OR 0.98, n.s. | **✗ not replicated** |
| CGN-C3 coupling → later fixes | OR **1.89** (z 22.4) | **✓ replicated** |
| CGN-C4 regression share higher in coupled files (expected ✗) | OR 1.09 (z 3.2) | **✓, against the original** |
| CGN-D1 / D2 concurrency avoids hubs / at the periphery | **reversed:** 1,215 concurrency functions are *more* often hubs (OR 1.70) and in the core (1.36) | ✗ / **✗ not replicated** |
| CGN-E1 orphans deleted sooner | OR 0.94 (deleted *less*) | **✗ not replicated** |
| CGK-K1 hubs more complex per line | OR 1.35 | **✓ replicated** |
| CGK-K2 orchestrators less complex per line | OR 0.75 | **✓ replicated** |
| CGK-K3 hubs more often public | OR 2.82 | **✓ replicated** |
| CGK-H1 hubs not built from low-rung bricks | OR 0.26 | **✓ replicated** |
| CGK-F extrinsic fixes: hub-hosting ↑, coupled ↓, cyclic ↓, peripheral ↑ | 1.50 ↑, 0.72 ↓, 0.56 ↓, 1.52 ↑, all at Bonferroni | **✓ replicated** |

## New claims

| id | result | verdict |
|---|---|---|
| **CGR-L1** language-neutral hub core (public surface, arguments, branches enriched in hubs in ≥ 6 of 8) | public surface 7 of 8; branches 5 of 8; arguments 1 of 8; all three only in PostgreSQL | **✗** |
| **CGR-L2** pointer enrichment in hubs is C-specific | enriched in 3 of 4 C repos (libgit2 OR 29, libxml2 1.8, redis 1.4; PostgreSQL 1.1 n.s.), not in Java or Python; Go 1.5 and Rust 1.8 (descriptive) | **✓** |
| **CGR-L3** most screen signs hold across languages (≥ 60%) | 22 of 37 original significant cells (59%) keep their sign in the non-C repos | **✗** (just under the bar) |
| **CGR-M1** which network signal carries later fixes, jointly with size, churn and prior fixes | rewired OR **1.42**, coupled **1.60**, in a cycle **1.38**, each p < 10⁻³⁷; prior fix 2.10, size 1.53, churn 1.22; 57,057 file-years | **all three carry** |

## Reading

- **What replicates across eight new repos and five languages:**
  - **Hubs:** they persist for years, are made early and attract new calls (preferential attachment). They are
    public and decision-dense, not simple helpers.
  - **Defects:** rewiring, coupling and cycles each mark files that need more fixes the next year, even jointly and
    beyond size, churn and prior fixes.
  - **Platform fixes:** they land in peripheral, hub-hosting wrapper files.
  - **Mostly static:** call networks are quiet most quarters.
- **What does not:** the "jumps" picture (5 of 8 repos), centralisation, duplicated wiring as a safe sign, dead-code
  deletion, and the CVE-rewiring result (one repo, opposite direction).
- **Concurrency reverses across languages.** In C libraries concurrency code was peripheral (48 functions); across
  these repos, with Go, Java and Python code that really uses concurrency (1,215 functions), it is *more* central.
  The C result was a small-sample, language-specific artefact.
- **Language bias is real.** Pointer enrichment of hubs is a C property, as the owner suspected. Only 59% of the
  original keyword-screen signs carry to non-C code, and the "language-neutral hub core" holds only for public
  surface. Keyword profiles of network roles must be reported per language.
- **Literature:** the replicated laws are known (preferential attachment and hub persistence: Valverde & Solé 2005,
  Wang et al. 2009; coupling and cycles vs defects: Zimmermann & Nagappan 2008, Oyetoyan et al. 2013; change
  metrics: Bhattacharya et al. 2012). This replication extends them to five languages and to a joint model with prior
  fixes. The extrinsic-fix signature and the C-specific pointer profile remain the new results. M1 lacks the
  author-count and change-coupling controls; LAWS adds them.

## Caveats

Eight repos, one per language outside C; per-language claims are descriptive. Fix labels outside C come from
keyword rules not yet audited (LAWS Amendment 0 audits them). The defect models here do not cluster by file;
LAWS does.
