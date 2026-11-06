# ARCH-Z1..Z4 — archetype atypicality: ndpi (SCORED)

- DB `.claude/worktrees/forward-asof/dbs/ndpi_out/ndpi_galaxy_master.db` · 43 quarterly snapshots · scored: **26** · 121 on-master security fixes, window (t, t+180 d]

| ranking | mean recall@20 |
|---|---:|
| LOC-desc | 0.188 |
| LOC-asc | 0.152 |
| composition fit z | 0.155 |
| file-cluster distance | 0.179 |

| claim | vs LOC-desc mean [lo] | vs LOC-asc mean [lo] | verdict |
|---|---|---|---|
| **ARCH-Z1** | -0.034 [-0.228] | +0.003 [-0.103] | **not supported (inconclusive)** |
| **ARCH-Z2** | -0.010 [-0.184] | +0.026 [-0.077] | **not supported (inconclusive)** |

| claim | size-stratified AUC − 0.5 | lo | 90% CI | verdict |
|---|---:|---:|---|---|
| **ARCH-Z3** | -0.1460 | -0.2388 | [-0.1992, -0.0920] | **not supported (inconclusive)** |
| **ARCH-Z4** | -0.0842 | -0.1376 | [-0.1149, -0.0536] | **not supported (inconclusive)** |

## Secondary (descriptive / exploratory)

- composition fit z: Spearman ρ with total_loc **-0.354**; mean raw AUC 0.293; size-stratified AUC 0.354 (sign flipped, i.e. *typical* first: 0.646)
- file-cluster distance: Spearman ρ with total_loc **+0.185**; mean raw AUC 0.464; size-stratified AUC 0.416 (sign flipped, i.e. *typical* first: 0.584)

Pooled rows 7,007, positives 452. Runtime 1s · bootstrap 5000 rounds, seed 2982, α = 0.0025.
