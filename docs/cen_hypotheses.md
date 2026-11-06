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

---

# DYN-H1 / DYN-H2 results (registered 2026-10-23 in HYPOTHESES.md; scored here 2026-11-06 with `9149c2f`)

**Data.**
- nDPI: the frec DB (`32619e4a5`, ablated history), 121 security-fix events.
- openssl: 252 security-fix parent snapshots scanned for this test (`32619e4a5`, ablated; 252 done, 0 failed).
- The C dynamism pattern was checked identical to the registered regex at `32619e4a5` and `da852aa54`.

Reports: `dyn_ndpi.md`, `dyn_openssl.md`.

| claim | nDPI | openssl | verdict |
|---|---|---|---|
| **DYN-H1** dynamism ranks fixed files above LOC within a powered size band | bands 23–48 +0.118, 49–108 −0.054, > 108 −0.071; none passes | > 108 (the only powered band) −0.088 | **not supported** |
| **DYN-H2** Mantel-Haenszel rate ratio, any dynamism vs none, at equal size + evidence | **2.03** (lo 1.51) | **2.33** (lo 1.74) | **SUPPORTED** (both repos) |

**Robustness (exploratory, `tools/exploratory/dyn_finer_strata.py`).** The registered strata were LOC *deciles*, the
coarseness that leaked size in NM. With finer LOC strata the ratio barely moves:

| strata | nDPI | openssl |
|---|---:|---:|
| 10 LOC bins × 4 evidence | 2.07 | 2.32 |
| 50 LOC bins | 2.17 | 1.80 |
| 100 LOC bins | 2.19 | 1.78 |
| 50 LOC × 4 evidence | 1.97 | 2.25 |

It is not leftover size.

**Reading.**
- Files with function-like macros or `goto` are touched by security fixes **about 2× as often as files of the same size**,
  replicated on two repos where this predictor was unseen.
- As a *ranking* signal it does not beat LOC (H1). Dynamism is common in big files, and a 2× factor on a size-dominated
  baseline does not reorder the files.

**Decision rule → (b), as registered:** keep the current modest per-file dynamism weight as a correction; no increase.

**Context.**
- This is the first snapshot property to show a replicated association with **security** fixes beyond size.
- Plausible mechanism, unproven: in C, function-like macros and `goto` cluster in hand-written parsers and error paths
  (byte-field access macros, `goto fail` cleanup chains). That is the code where memory-safety bugs live.
