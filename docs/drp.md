# DRP — do fix commits repay self-admitted debt less often than other commits? (SCORED)

Registration `docs/drp_hypotheses.md` (owner OK 2026-11-11). Repos libgit2, libxml2, postgres, redis. Commit bootstrap 2000 within repo, seed 2982; one-sided α = 0.01/2. Aggregates only.

- units: 65,168 non-merge commits changing in-scope C/C++ lines; fixes 26,108 (40.1%); repaying commits 1,731 (2.7%); repaying fix commits **611**

| id | strata | repay rate: fix commits | other commits | MH RR | one-sided upper bound (α = 0.005) | call |
|---|---|---:|---:|---:|---:|---|
| **DRP-R** | repo | 2.34% | 2.87% | **0.77** | 0.86 | **SUPPORTED** |
| **DRP-S** | repo × commit size | — | — | **1.07** | 1.20 | **not supported** |

Power rule: ≥ 30 repaying fix commits pooled.

## Descriptive (no verdicts)

| repo | commits | fixes | repay rate: fix / other | RR raw | RR size-stratified | bulk repayers (≥ 5 lines) |
|---|---:|---:|---|---:|---:|---:|
| libgit2 | 9,239 | 2,255 | 1.37% / 2.29% | 0.60 | 0.85 | 4 |
| libxml2 | 5,788 | 3,125 | 2.88% / 3.60% | 0.80 | 1.21 | 20 |
| postgres | 40,711 | 17,369 | 2.68% / 3.35% | 0.80 | 1.10 | 49 |
| redis | 9,430 | 3,359 | 0.71% / 1.33% | 0.54 | 0.73 | 2 |

- Repay rate by size bin (fix / other): 1–2 0.0% / 0.3%; 3–8 0.2% / 0.6%; 9–32 1.0% / 1.1%; 33–128 2.6% / 2.7%; 129–512 7.6% / 6.1%; > 512 20.6% / 14.7%
- Repay rate by fix class: extrinsic 1.80% (n 1,220), latent 5.13% (n 39), other-fix 2.24% (n 20,867), regression 3.90% (n 1,767), regression-linked 2.30% (n 2,215)

Runtime 114s · seed 2982.

## Reading (hand-written, not generated)

- **The pattern replicates, and commit size explains it completely.** On four repos never used for this, fix commits
  repay debt less often than other commits: RR 0.77, upper bound 0.86 (DRP-R supported). Within commit-size bins the
  gap disappears: RR 1.07, upper bound 1.20 (DRP-S not supported). This is the reading the registration named: fixes
  repay less debt only because they are small.
  - Repaying debt is mostly something large commits do. Repay rates climb from 0–0.3% for 1–2-line commits to 15–21%
    for commits over 512 lines, for fixes and non-fixes alike.
  - Among large commits, fixes repay slightly *more* often (20.6% vs 14.7% over 512 lines).
- **It holds in every repo, raw (0.54–0.80) and size-stratified (0.73–1.21).** No repo shows a strong
  "fixes avoid debt" effect once size is matched.
- **This also corrects the exploratory study (#147).** Its "debt is repaid in clean-ups, not fixes" is better read as
  "debt is repaid in big commits; fixes are usually small".
- **Process.** The scorer was committed before running (`7ae3bfb`). It ran once.
