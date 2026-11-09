# CGK — what kind of code sits where in the call network, and where the fix classes land (SCORED)

**Type:** confirmatory (K1–K3, H1, F grid) plus a registered screen (KS)
**Registered:** 2026-11-08 21:20 (5230366, `docs/cgk_hypotheses.md`); scorer committed 21:21 (bb2ce50,
`tools/cgk_eval.py`) before its one run. Latest snapshots of curl, OpenSSL, libarchive, harfbuzz, nDPI; 2,435 hubs
and 3,079 orchestrators (top 10% by in- / out-degree). Raw output `gitgalaxy/cgt-study/cgk_result.json`.

## Registered verdicts

| id | claim | result | verdict |
|---|---|---|---|
| **K1** | hubs are simpler per line | **opposite:** hubs are *more* often above-median complexity per line, OR 1.50 (z +8.2) | **✗** |
| **K2** | orchestrators are more complex per line | **opposite:** OR 0.73 (z −6.4) | **✗** |
| **K3** | hubs are more often public | OR **6.16** (z 38.9) | **✓** |
| **H1** | hubs are built from low-rung bricks (≤ 3 signals) | **opposite:** OR 0.33; hubs sit at rungs 5–9 | **✗** |

## The screen (KS): 26 signals × 3 roles, Bonferroni 0.01/78, size-stratified

Signal names as the engine displays them (gitgalaxy#8009/#8024):

| role | enriched | depleted |
|---|---|---|
| **hub** (called by many) | public / exported surface (`arch_api`, OR 10.3), structural keywords (`struct_linear`), arguments, branches, pointers, error exits (`state_bailout_hits`), immutability (`def_freeze_hits`), generics | globals, private scope (`def_encapsulation`, OR 0.11), class / struct declarations, unsafe constructs (`state_safety_neg`), `state_heat_triggers` |
| **orchestrator** (calls many) | pointers (OR 5.2), `state_heat_triggers`, state mutation (`state_flux`), casts, defensive checks (`def_safety`), immutability, class / struct declarations | public surface, branches, error exits, bitwise operations, function declarations |
| **periphery** (below-median core) | globals, private scope, bitwise operations, casts, memory allocation, unsafe constructs, error exits | public surface, branches, pointers, class / struct declarations, `state_heat_triggers` |

## Hub structure (descriptive)

- Rungs: hubs peak at 6–7 signals (non-hubs at 7–8 but with a long low tail: 591 non-hub functions at rung ≤ 3, 22
  hubs).
- Archetypes: hubs are mostly **Parameter Forwarders** (749), **Compute Cores** (597), **Many-Argument Workhorses**
  (422) and **Defensive Guards** (180); non-hubs are led by Stateful Encapsulated Methods and Encapsulated Accessors.

## Fix classes vs the touched file's network position (vs other fixes; two-sided, 0.01/11)

| file position | latent (CVE) | regression | extrinsic |
|---|---|---|---|
| hosts a hub | 1.16 n.s. | 1.06 n.s. | **1.35 enriched** |
| top-quintile coupled | 1.20 n.s. (p 0.054) | *(CGN-C4: 0.96)* | **0.71 depleted** |
| in a file call cycle | 1.15 n.s. (p 0.059) | 0.92 n.s. | **0.70 depleted** |
| peripheral | 0.93 n.s. | 1.08 n.s. | **1.49 enriched** |

## Reading

- **Hubs are not simple utilities.** The most-called functions are public, argument-heavy, branchy, pointer-handling
  functions with error exits: entry points and shared workhorses (parameter forwarders, compute cores, defensive
  guards). They are more decision-dense per line than functions of the same size.
- **Orchestrators are the opposite:** functions that call many others are straight-line, stateful sequences
  (pointers, state changes, casts, safety checks) with fewer branches: glue and setup code.
- **The periphery is private and low-level:** globals, private scope, bit-twiddling, memory allocation, unsafe
  constructs. (CGN-D2: concurrency code is peripheral too.)
- **Only one of the three fix classes maps onto the network.** Extrinsic (platform, compiler, dependency) fixes land
  in *peripheral files that host hubs*: compatibility and wrapper modules called from everywhere but wired to little
  else. They avoid coupled and cyclic files. CVE fixes and regressions land where other fixes land; CVE fixes lean
  toward coupled and cyclic files without reaching the bar.

## Caveats

Latest snapshots only (one per repo); five C libraries; signals depend on each history database's engine. The KS
screen is many cells; each call stands only at its Bonferroni bar.

## Follow-ups (for unseen data only)

- Extrinsic fixes in peripheral hub-hosting files: replicate on unseen repos (the platform-layer signature).
- CVE fixes vs coupling and cycles: a powered test on unseen repos (both leaned positive, p ≈ 0.05).
- The hub / orchestrator profile on other languages (does "hubs are decision-dense entry points" hold in Java or
  Python?).
