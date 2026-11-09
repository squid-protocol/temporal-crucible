# CGK — what kind of code sits where in the call network, and where do the three fix classes land? — registered 2026-11-08, before any CGK statistic

**Why.** Owner's questions (2026-11-08), after CGN: how do the engine's keyword signals correlate with hubs and with
the network's edges? Do hub functions have a specific structure? Do the programme's fix classes (regression, latent
= CVE fix, extrinsic) relate to network position? CGN found hubs are a stable, rich-get-richer skeleton, coupling and
cycles go with later fixes, and concurrency code sits at the periphery.

## Data

The CGT/CGN networks (`docs/cgt_hypotheses.md`), **latest snapshot of each repo** for K and H; for F, the snapshot
just before each fix. Function attributes from the history databases: `loc`, `complexity`, `is_public` and the 26
lattice signals (`lattice_shapes.json`, a27d2c93f817ac25), all present in all five databases. Presence = value > 0.

**Roles (per snapshot):** **hub** = top 10% of functions by in-degree (in-degree > 0); **orchestrator** = top 10% by
out-degree (out-degree > 0); **periphery** = undirected k-core number below the snapshot's median. Lattice rung k =
number of lattice signals present; **low rung** = k ≤ 3.

## Claims (strata repo × loc quintile unless stated; CMH; seeds 2982)

**K. Keywords and position** (latest snapshots)

| id | claim | supported iff |
|---|---|---|
| **CGK-K1** | hubs are simpler per line | complexity / loc ≥ the repo median: hub vs non-hub OR < 1, p < 0.0033 |
| **CGK-K2** | orchestrators are more complex per line | same outcome, orchestrator vs not, OR > 1, p < 0.0033 |
| **CGK-K3** | hubs are more often public | `is_public`, hub vs non-hub, OR > 1, p < 0.0033 |
| **CGK-KS** (screen) | which signals go with which role | for each of 26 signals × 3 roles (78 tests): presence vs role, two-sided CMH; a cell is **enriched / depleted** iff p < 0.01 / 78. Reported in full; no single cell is a headline claim |

**H. Hub structure**

| id | claim | supported iff |
|---|---|---|
| **CGK-H1** | hubs are built from low-rung "bricks" | low rung (k ≤ 3): hub vs non-hub OR > 1, p < 0.01 |
| *descriptive* | hub lattice families and archetypes against size-matched non-hubs | per-family CMH ORs, archetype shares |

**F. Fix classes and network position** (unit = a fix × a C/C++ file it touches, the file present in the snapshot
before the fix; strata repo × file size quintile (functions in file); class vs `other-fix`; two-sided CMH; each cell
significant iff p < 0.01 / 11)

| exposure (file at the snapshot before the fix) | latent (CVE) | regression | extrinsic |
|---|---|---|---|
| hosts a hub (any function in the top 1% by in-degree) | **F1** | **F2** | **F3** |
| top-quintile coupling (distinct files called or calling) | **F4** | *(CGN-C4, not retested)* | **F5** |
| in a file-level call cycle (SCC ≥ 2) | **F6** | **F7** | **F8** |
| peripheral (median core of its functions below the snapshot median) | **F9** | **F10** | **F11** |

Priors (stated, not tested as directions): CVE fixes in hub-hosting, central files (shared parsers, buffer helpers);
extrinsic fixes peripheral (platform wrappers at the edge) or, against that, in hub wrappers; regressions in cycles.

## Not evaluable

< 30 exposed units in a claim or cell.

## Guards

Registration before scorer and run; one run; verdicts either way. Size strata everywhere; Bonferroni on the screen
and the F grid. Same repos as CGT/CGN: descriptive of these codebases until replicated.
