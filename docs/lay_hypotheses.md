# LAY — does a layered fingerprint (calls, control-flow shape) find copies the coarse fingerprint misses? — registered 2026-11-06, before any L2/L3 feature or ranking was computed

**Why.**
- UT found that the coarse `sfs` fingerprint (L1: size, complexity, about 32 signal densities) retrieves only
  **12.5%** of the forks' copies of OpenSSL CVE-fixed functions, and **none** in C++-rewritten BoringSSL.
- The proposed fix is layering. **L2 behaviour:** the set of functions a function calls (`calls_out_to`, already in
  the engine). **L3 shape:** its control-flow skeleton.
- This benchmark tests the layers on UT's pairs.
- **Scope note (owner, 2026-11-06).** The owner's earlier `sfs` run on COBOL vs its Java port found no matches,
  because the port goes through a runtime layer rather than a 1:1 keyword translation. Cross-language
  **port traceability is out of scope.** The translator should emit that mapping itself. LAY concerns renamed, forked
  and rewritten code within a language family: C → C, and C → C++ for BoringSSL.

## Benchmark (UT's data and definitions)

**Queries.**
- OpenSSL functions changed by a post-2014-06-20 CVE fix (`latent`, rules v2).
- Each one's pre-fix version is taken from the latest quarterly snapshot before the fix (UT's query table).
- Deduplicated by (path, name, fork).

**Truth.**
- For each (query, fork): the fork function with the same name whose token Jaccard with the pre-fix body is ≥ 0.5.
- These are UT's **name-identified copies**: 104 in UT's run.
- Queries without such a copy are excluded.

**Candidates.** All functions of the fork head with ≥ 6 lines: UT's fork tables, engine `da852aa54`.

## Methods (none uses the query's or candidate's own name)

| method | similarity |
|---|---|
| **L1** | negative Euclidean distance between `sfs` vectors (UT's twin space) |
| **L2** | Jaccard of the two functions' `calls_out_to` sets (callee names, lower-cased; the function's own name removed) |
| **L3** | Jaccard of control-flow skeleton 3-shingles (see below) |
| **FUSED** | reciprocal-rank fusion of L1, L2 and L3: Σ 1/(60 + rank), the standard k = 60 |
| *TOKEN (reference only)* | token-bag Jaccard of bodies with the function's own name removed. **Not a claim:** truth is token-defined, so this is near-circular; it is reported as a ceiling |

**Control-flow skeleton.** The tree-sitter pre-order sequence of the function body's node types in {`if_statement`,
`else_clause`, `for_statement`, `while_statement`, `do_statement`, `switch_statement`, `case_statement`,
`return_statement`, `goto_statement`, `break_statement`, `continue_statement`, `compound_statement`}, each tagged with
its nesting depth (capped at 6). It is shingled into overlapping 3-grams.

**Metric.**
- recall@1 and recall@10: the share of queries whose true copy ranks first, or within the top 10, among all
  candidates of that fork.
- Ties are broken pessimistically: the true copy is placed last among equal scores.

## Claims (paired bootstrap over queries, 5,000 rounds, seed 2982, α = 0.01/3 one-sided)

| id | claim | supported iff |
|---|---|---|
| **LAY-H1** | the call layer beats the coarse fingerprint | recall@1(L2) − recall@1(L1) > 0, lo > 0 |
| **LAY-H2** | the fused layered fingerprint beats it | recall@1(FUSED) − recall@1(L1) > 0, lo > 0 |
| **LAY-H3** | …**including across the C → C++ rewrite** | recall@10(FUSED) − recall@10(L1) on BoringSSL queries > 0, lo > 0 |

- **Not evaluable:** < 30 queries for H1 and H2; < 15 BoringSSL queries for H3.
- **Descriptive:** all methods' recall@1 and @10, per fork; the TOKEN ceiling.

## Priors

- **H1 likely.** Callee sets are distinctive for crypto code.
- **H2 likely.**
- **H3 uncertain.** BoringSSL renamed many internal helpers in its C++ port, which also hurts L2.

---

## Results — 2026-11-06 (scorer `700bd88` committed before running; report `lay.md`; aggregates only)

**Data.** 90 queries with a name-identified copy of ≥ 6 lines: 73 LibreSSL, 17 BoringSSL.

| claim | difference | lo (α 0.01/3) | verdict |
|---|---:|---:|---|
| **LAY-H1** recall@1 call set (L2) − coarse (L1) | **+23.3 pts** | +5.6 | **SUPPORTED** |
| **LAY-H2** recall@1 fused (L1+L2+L3) − coarse | **+34.4 pts** | +20.0 | **SUPPORTED** |
| **LAY-H3** recall@10 fused − coarse, BoringSSL (C++) | **+35.3 pts** | +5.9 | **SUPPORTED** (n = 17) |

| subset | L1 @1 / @10 | L2 | L3 | **FUSED** | TOKEN (ceiling) |
|---|---:|---:|---:|---:|---:|
| all (90) | 46% / 71% | 69% / 87% | 44% / 53% | **80% / 89%** | 92% / 100% |
| LibreSSL (73) | 49% / 73% | 75% / 84% | 53% / 63% | **77% / 86%** | 90% / 100% |
| BoringSSL (17) | 29% / 65% | 41% / 100% | 6% / 12% | **94% / 100%** | 100% / 100% |

**Reading.**
- **Layering works.** The call set alone lifts top-1 retrieval from 46% to 69%. Fusing the three layers reaches
  **80%**, without using any names. That is within 12 points of a near-circular text ceiling.
- **Across the C → C++ rewrite**, fusion finds the BoringSSL copy first 94% of the time, against 29% for the coarse
  fingerprint.
- **The layers are complementary.** The control-flow skeleton (L3) is weak alone, and useless on BoringSSL (6%),
  where C++ restructured control flow. Yet fusion still beats every single layer.
- **Why L1 here (46%) differs from UT's 12.5%.**
  - UT measured `sfs`'s strict acceptance rule: reciprocal nearest neighbour plus a distinctiveness ratio, at an
    estimated 1% false-discovery rate.
  - LAY measures **ranking**: is the true copy at the top among all candidates?
  - So the coarse fingerprint often ranks the copy first, but rarely passes the strict twin test. The layered version
    is needed to make confident calls.

**Caveats.**
- Truth comes from names (same-name copies, by construction), so renamed copies are not represented. UT found none
  among accepted twins.
- BoringSSL has only n = 17.
- Fusion weights are the standard RRF, not tuned.
- One fork family. A second benchmark (vendored zlib, SQLite or Lua copies in other projects) is the out-of-sample
  test.
- **Ownership.** Building this into `sfs` or the engine is the owner's decision. This entry only measures it.
