# ARCH-Z1..Z4 — archetype atypicality: openssl (SCORED)

- DB `.claude/worktrees/frec/dbs/openssl_out/openssl_galaxy_master.db` · 110 quarterly snapshots · scored: **75** · 252 on-master security fixes, window (t, t+180 d]

| ranking | mean recall@20 |
|---|---:|
| LOC-desc | 0.271 |
| LOC-asc | 0.128 |
| composition fit z | 0.149 |
| file-cluster distance | 0.267 |

| claim | vs LOC-desc mean [lo] | vs LOC-asc mean [lo] | verdict |
|---|---|---|---|
| **ARCH-Z1** | -0.123 [-0.238] | +0.021 [-0.058] | **not supported (inconclusive)** |
| **ARCH-Z2** | -0.004 [-0.150] | +0.139 [+0.037] | **not supported (inconclusive)** |

| claim | size-stratified AUC − 0.5 | lo | 90% CI | verdict |
|---|---:|---:|---|---|
| **ARCH-Z3** | +0.0016 | -0.0493 | [-0.0281, +0.0300] | **not supported (inconclusive)** |
| **ARCH-Z4** | +0.0308 | -0.0193 | [+0.0006, +0.0624] | **not supported (inconclusive)** |

## Secondary (descriptive / exploratory)

- composition fit z: Spearman ρ with total_loc **+0.206**; mean raw AUC 0.534; size-stratified AUC 0.502 (sign flipped, i.e. *typical* first: 0.498)
- file-cluster distance: Spearman ρ with total_loc **+0.108**; mean raw AUC 0.548; size-stratified AUC 0.531 (sign flipped, i.e. *typical* first: 0.469)

Pooled rows 98,647, positives 663. Runtime 4s · bootstrap 5000 rounds, seed 2982, α = 0.0025.
