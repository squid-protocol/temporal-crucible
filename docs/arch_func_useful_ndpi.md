# ARCH-U4 — function archetype vs function size: ndpi (SCORED)

- DB `.claude/worktrees/frec/dbs/ndpi_out/ndpi_galaxy_master.db` · fix-class events with a date: 121; skipped: none; median date 2021-05-15
- scored (later half, trained, >= 1 positive and >= 1 negative): **51** events, 4719 candidate functions, 117 positives

| claim | mean AUC lift over loc | one-sided lo (α=0.0025) | 90% CI | verdict |
|---|---:|---:|---|---|
| **ARCH-U4** | -0.0030 | -0.0188 | [-0.0123, +0.0064] | **replicated null (equivalence)** |

Mean within-event AUC: loc 0.8648 · loc × d_f(archetype) 0.8618 · d_f(archetype) alone 0.4512

## Descriptive: per-line hit density by function archetype (all events' candidates)

| archetype | candidate kLOC | hit functions | hits per kLOC | ratio to global |
|---|---:|---:|---:|---:|
| C Struct Operations | 16.9 | 25 | 1.48 | 2.46 |
| Encapsulated Accessors | 3.0 | 4 | 1.36 | 2.25 |
| Parameter Forwarders | 7.5 | 6 | 0.80 | 1.33 |
| Many-Argument Workhorses | 214.5 | 141 | 0.66 | 1.09 |
| Stateful Encapsulated Methods | 20.7 | 12 | 0.58 | 0.96 |
| Compute Cores | 71.9 | 35 | 0.49 | 0.81 |
| Defensive Guards | 6.5 | 3 | 0.46 | 0.77 |
| I/O & Config Routines | 49.9 | 11 | 0.22 | 0.37 |
| Interface Declarations | 0.9 | 0 | 0.00 | 0.00 |
| Type Conversions | 2.3 | 0 | 0.00 | 0.00 |
| State Mutators | 0.0 | 0 | 0.00 | 0.00 |

| class | events | mean lift |
|---|---:|---:|
| security-fix | 51 | -0.0030 |

Runtime 4s · bootstrap 5000 rounds over events, seed 2982.
