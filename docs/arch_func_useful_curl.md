# ARCH-U4 — function archetype vs function size: curl (SCORED)

- DB `.claude/worktrees/rescan-engine-32619e4a5/dbs/curl_out/curl_galaxy_master.db` · fix-class events with a date: 1293; skipped: none; median date 2021-03-29
- scored (later half, trained, >= 1 positive and >= 1 negative): **435** events, 26370 candidate functions, 1302 positives

| claim | mean AUC lift over loc | one-sided lo (α=0.0025) | 90% CI | verdict |
|---|---:|---:|---|---|
| **ARCH-U4** | -0.0091 | -0.0205 | [-0.0155, -0.0030] | **replicated null (equivalence)** |

Mean within-event AUC: loc 0.7917 · loc × d_f(archetype) 0.7826 · d_f(archetype) alone 0.3060

## Descriptive: per-line hit density by function archetype (all events' candidates)

| archetype | candidate kLOC | hit functions | hits per kLOC | ratio to global |
|---|---:|---:|---:|---:|
| Parameter Forwarders | 18.8 | 54 | 2.87 | 3.66 |
| Encapsulated Accessors | 24.5 | 45 | 1.83 | 2.34 |
| Type Conversions | 15.8 | 29 | 1.83 | 2.34 |
| Defensive Guards | 12.7 | 19 | 1.49 | 1.90 |
| C Struct Operations | 310.1 | 372 | 1.20 | 1.53 |
| Interface Declarations | 3.6 | 4 | 1.10 | 1.40 |
| Compute Cores | 285.9 | 284 | 0.99 | 1.27 |
| Stateful Encapsulated Methods | 166.3 | 147 | 0.88 | 1.13 |
| I/O & Config Routines | 28.3 | 20 | 0.71 | 0.90 |
| Many-Argument Workhorses | 1,997.8 | 1271 | 0.64 | 0.81 |

| class | events | mean lift |
|---|---:|---:|
| bugfix-bug | 23 | -0.0400 |
| bugfix-fixes | 208 | -0.0087 |
| regression | 94 | -0.0041 |
| security-fix | 110 | -0.0077 |

Runtime 34s · bootstrap 5000 rounds over events, seed 2982.
