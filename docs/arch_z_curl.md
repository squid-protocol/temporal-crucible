# ARCH-Z1..Z4 — archetype atypicality: curl (SCORED)

- DB `.claude/worktrees/forward-asof/dbs/curl_out/curl_galaxy_master.db` · 105 quarterly snapshots · scored: **63** · 186 on-master security fixes, window (t, t+180 d]

| ranking | mean recall@20 |
|---|---:|
| LOC-desc | 0.205 |
| LOC-asc | 0.158 |
| composition fit z | 0.140 |
| file-cluster distance | 0.197 |

| claim | vs LOC-desc mean [lo] | vs LOC-asc mean [lo] | verdict |
|---|---|---|---|
| **ARCH-Z1** | -0.065 [-0.166] | -0.018 [-0.086] | **not supported (inconclusive)** |
| **ARCH-Z2** | -0.008 [-0.143] | +0.039 [-0.073] | **not supported (inconclusive)** |

| claim | size-stratified AUC − 0.5 | lo | 90% CI | verdict |
|---|---:|---:|---|---|
| **ARCH-Z3** | +0.0334 | -0.0139 | [+0.0036, +0.0630] | **not supported (inconclusive)** |
| **ARCH-Z4** | -0.0318 | -0.0949 | [-0.0676, +0.0039] | **not supported (inconclusive)** |

## Secondary (descriptive / exploratory)

- composition fit z: Spearman ρ with total_loc **+0.177**; mean raw AUC 0.584; size-stratified AUC 0.533 (sign flipped, i.e. *typical* first: 0.467)
- file-cluster distance: Spearman ρ with total_loc **+0.329**; mean raw AUC 0.552; size-stratified AUC 0.468 (sign flipped, i.e. *typical* first: 0.532)

Pooled rows 32,789, positives 573. Runtime 11s · bootstrap 5000 rounds, seed 2982, α = 0.0025.
