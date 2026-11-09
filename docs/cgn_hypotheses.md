# CGN — the shape of call networks over time: hubs, efficiency, bad shapes, concurrency, dead code — registered 2026-11-08, before any CGN statistic

**Why.** Owner's questions (2026-11-08), after CGT: do central nodes stay constant, and when do they change or appear?
Do systems optimise their call graphs over time? Are there bad network situations (cycles, duplication, design
quality) that go with bugs? Does tangled wiring make kinks harder to work out? Does concurrency code avoid the hubs
and sit at the network's edge? Two classic network laws are added: preferential attachment and dead-code death.
**Priors from this programme:** centrality did not predict CVE fixes and inverted in small files (CEN, DYNCEN);
recidivism is the strongest fix predictor; coupling centralisation was project-specific (CPL); young functions die
faster (NH); CGT-4: rewired files get later fixes beyond churn (OR 2.02, 1.34 with file size, post-hoc). Lehman's
law of increasing complexity predicts B1/B2 fail.

## Data and network (as CGT)

The same 390 quarterly snapshots and the same call network (`docs/cgt_hypotheses.md`: C/C++ functions with loc ≥ 3,
same-file then unique-name resolution, renames carried). **Yearly snapshots** = every fourth quarterly snapshot from
the first. Function attributes from the history databases: `loc`, `is_public`, `arch_concurrency`, `def_sync_locks`.
Fix labels: `events/<repo>_xc.json` (all classes) by `c_files`. A function's **birth** = its first snapshot.

## Claims

α = 0.01 per family, split evenly across the family's claims. Per-repo tests use one-sided p < 0.05 and "≥ 4 of 5
repos" as the pass rule unless stated. Seeds 2982.

**A. Hubs** (hub = top 1% of functions by in-degree in its snapshot, at least 3 functions)

| id | claim | supported iff |
|---|---|---|
| **CGN-A1** | hubs persist: a hub still alive 5 years later is still central | per repo, over all yearly snapshot pairs 5 years apart: ≥ 50% of surviving hubs are in the top 5% at t + 5 y, and in-degree Spearman over persisting functions ≥ 0.5; in ≥ 4 of 5 repos |
| **CGN-A2** | hubs are made early | pooled over repos, ≥ 50% of functions that ever become a hub do so within 8 quarters of their birth (functions born after each repo's first snapshot) |
| **CGN-A3** | preferential attachment: new calls go to already-central functions | per repo, new edges (t → t+1) into persisting functions: Mann–Whitney AUC of the targets' in-degree at t against all persisting functions' in-degree at t > 0.55 with p < 0.0033 (permutation); in ≥ 4 of 5 repos |

**B. Efficiency over time** (yearly snapshots)

| id | claim | supported iff |
|---|---|---|
| **CGN-B1** | networks grow more modular | Newman modularity Q of the undirected call network over the **directory** partition rises with time: Kendall τ > 0, p < 0.05, in ≥ 4 of 5 repos |
| **CGN-B2** | cross-file wiring falls | share of edges between different files falls with time: τ < 0, p < 0.05, in ≥ 4 of 5 |
| **CGN-B3** | the network centralises | share of all edges that end in a hub rises with time: τ > 0, p < 0.05, in ≥ 4 of 5 |

**C. Bad network shapes and later fixes** (file-years at yearly snapshots t; outcome: any xc fix touching the file
in (t, t + 365 d]; strata = repo × file-size quintile (functions in file) × churn quintile (lines changed in the year
before t) × prior fix (any fix in the year before t); CMH one-sided, OR > 1, p < 0.0025 each; file-years outside each
repo's label window dropped)

| id | claim (exposure) |
|---|---|
| **CGN-C1** | **cycles:** the file is in a file-level strongly connected component of size ≥ 2 (files that call each other round a loop) |
| **CGN-C2** | **duplicated wiring:** the file has a function whose internal callee set (≥ 3 callees) is identical to that of a function in another file |
| **CGN-C3** | **coupling:** the file is in its snapshot's top quintile of distinct other files it calls or is called by (prior: null, as centrality) |
| **CGN-C4** | **kinks are harder to work out in tangled code:** among fixes landing in a file, the share that are regressions is higher when the file is top-quintile coupled at the snapshot before the fix (exposure) than when not; strata repo × file-size quintile; CMH, OR > 1 |

**D. Concurrency** (latest snapshot of each repo; concurrency function = `arch_concurrency` > 0 or `def_sync_locks` > 0;
strata repo × loc quintile)

| id | claim | supported iff |
|---|---|---|
| **CGN-D1** | concurrency code avoids the hubs | outcome in-degree ≥ the repo's 90th percentile; CMH OR < 1, p < 0.005 |
| **CGN-D2** | concurrency code sits at the network's edge | outcome k-core number (undirected) ≥ the repo's median core; CMH OR < 1, p < 0.005 |

**E. Dead code**

| id | claim | supported iff |
|---|---|---|
| **CGN-E1** | orphans die: non-public functions nobody calls are deleted sooner | at yearly snapshots, non-public functions with in-degree 0 vs non-public functions with in-degree ≥ 1: absent 2 years later (path carried by renames); strata repo × loc quintile × age band (< 1, 1–3, 3–6, ≥ 6 years); CMH OR > 1, p < 0.01 |

## Not evaluable

A repo with < 6 yearly snapshots is dropped from A1/B (none expected). C/D/E: fewer than 30 exposed units pooled.

## Priors

A1 expected ✓; A2 uncertain; A3 expected ✓ (classic); B1/B2 uncertain (owner: optimise; Lehman: decay); B3 uncertain
(CPL); C1 weakly ✓; C2 uncertain; C3 null; C4 uncertain; D1 expected ✓ (owner); D2 uncertain; E1 expected ✓.

## Guards

Registration before scorer and run; one run; verdicts either way. Size, churn and prior-fix strata on every fix
claim; size strata on every function claim; age bands on E1; α split per family; same snapshots as CGT, so no claim
here replicates CGT.
