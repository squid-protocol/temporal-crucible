# FLT-H1..H3 — fleet vs interactive Claude code in the GitGalaxy repo (SCORED)

- functions born in snapshots ≥ 2026-10-05: 1,538; attributed: fleet 636, interactive 899; dropped: {'no PR in first-parent subject': 3}

| claim | result | verdict |
|---|---|---|
| **FLT-H1** | all of gitgalaxy/: AUC **0.640** (fleet 636 vs interactive 899); placebos fleet 0.709, interactive 0.678; margin -0.069 (lo -0.136) | **not supported** |
| **FLT-H2** | inside gitgalaxy/tools/ only: AUC **0.624** (fleet 343 vs interactive 639); placebos fleet 0.713, interactive 0.681; margin -0.089 (lo -0.176) | **not supported** |
| **FLT-H3** fleet code concentrates in tools/ | share in tools/: fleet **54%**, interactive **71%**; difference -0.17 (lo -0.24) | **not supported** |

## What separates fleet from interactive code (standardised mean difference, fleet − interactive; descriptive)

- state_safety_neg: +0.22
- arch_api: -0.21
- def_freeze_hits: +0.19
- def_encapsulation: +0.17
- struct_branch: +0.17
- complexity/loc: +0.16
- def_safety: -0.15
- struct_linear: -0.14
- bitwise_ops: +0.13
- state_flux: -0.11

| archetype | fleet | interactive |
|---|---:|---:|
| Stateful Encapsulated Methods | 38.8% | 24.5% |
| Generic / Templated Code | 20.6% | 26.9% |
| Compute Cores | 13.7% | 12.5% |
| Encapsulated Accessors | 10.7% | 10.7% |
| Many-Argument Workhorses | 7.2% | 9.2% |
| Defensive Guards | 5.0% | 9.7% |
| Type Conversions | 3.0% | 4.6% |
| Parameter Forwarders | 0.6% | 0.9% |
| I/O & Config Routines | 0.0% | 1.0% |
| Interface Declarations | 0.2% | 0.1% |
| Callbacks & Closures | 0.2% | 0.0% |

Median size: fleet 12 lines, interactive 11 lines. Top dirs — fleet: [('gitgalaxy/tools', 343), ('gitgalaxy/core', 211), ('gitgalaxy/recorders', 31)]; interactive: [('gitgalaxy/tools', 639), ('gitgalaxy/core', 133), ('gitgalaxy/standards', 90)]

Runtime 4s · seed 2982. H1/H2 bootstrap 2,000 rounds over out-of-fold scores (as GG).
