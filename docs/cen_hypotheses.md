# CEN-H1 / CEN-H2 — does mid-size-file centrality find bug fixes? — registered 2026-11-06, before any centrality statistic on these repos

**Origin.** B-H1..B-H3 (2026-09-13, `bh_eval.md`) reported two exploratory "context cells", registered for repo #3 but
never claimed or run. In curl's 49–108-line band:
- PageRank lift over LOC +0.145 (lo +0.020);
- popularity (in-degree) +0.132 (lo +0.025).

They were never given an exact statistic or label set. This entry fixes both and runs them.

**Repos (unseen for centrality).**
- **openssl:** 110 quarterly as-of snapshots, engine `da852aa54`.
- **harfbuzz:** 62 snapshots, same engine, files `language IN ('c','cpp')`.
- **libarchive:** 72 snapshots, same engine, files `language = 'c'`.
- curl supplied the lead and nDPI's N-FIRST was a centrality finding, so both are excluded.

**Outcome.** A file at quarterly snapshot t is positive if a **bug-fix commit** touches it in (t, t + 180 d].
Bug-fix commit = any XC-labelled commit (`events/{repo}_xc.json`, rules v2) of class latent, regression or other-fix;
extrinsic excluded. That is the program's nearest analogue of B-H's `Fixes #` / `Bug:` / regression labels.

**Statistic (the B-H1 cell).**
- Candidates are files with `total_loc` in **49–108**, at each snapshot. Rows are pooled over snapshots.
- lift = AUC(score) − AUC(`total_loc`), ties ½.
- Snapshot-cluster bootstrap, 5,000 rounds, seed 2982.

| id | score | supported iff (per repo) |
|---|---|---|
| **CEN-H1** | `pagerank_score` | lift > 0 with one-sided lo > 0 at α = 0.01 / 2 |
| **CEN-H2** | `popularity` | same |

- **Power.** < 20 positives in the band = not evaluable.
- **Equivalence null.** Two-sided 90% CI inside [−0.02, +0.02].
- **Overall.** A claim holds iff SUPPORTED on every evaluable repo.

**Descriptive (no verdicts).** The same lift in the other three bands (≤ 22, 23–48, > 108); an effort-aware recall@20
within the band.

**Priors.**
- CEN-H1 / H2 **uncertain, leaning not supported**: the curl cells were two of many and were never replicated.
- If they hold, centrality's live claim is "in mid-size files, the files many others depend on get more bug fixes".

---

## Results — 2026-11-06 (scorer `9149c2f` committed before running; reports `cen_{openssl,harfbuzz,libarchive}.md`)

Mid band (49–108 lines), lift = AUC(score) − AUC(`total_loc`):

| claim | openssl (1,258 positives) | harfbuzz (381) | libarchive (281) | overall |
|---|---|---|---|---|
| **CEN-H1** PageRank | −0.044, CI [−0.072, −0.014] ✗ | −0.051, CI [−0.095, −0.006] ✗ | +0.035, CI [−0.077, +0.151] ✗ | **not supported** |
| **CEN-H2** popularity | **+0.061**, lo +0.008 ✓ | −0.072, CI [−0.109, −0.034] ✗ | +0.000, CI [−0.050, +0.054] ✗ | **not supported** |

**Headline → the curl mid-band centrality cells do not replicate.**
- PageRank points the wrong way on two of three repos.
- Popularity (how many files include this one) helps on openssl only.
- Centrality is closed as a predictive lead for this program. It stays a descriptive map of how files depend on each
  other.
