# LAT — the fingerprint lattice: fix families (LAT-F) and lattice moves (LAT-M)

**Status: DRAFT registration (2026-11-07), awaiting owner OK.** No outcome data has been read for these hypotheses.
The scorer (`tools/lat_eval.py`) is committed before any run; nothing is scored before that commit.

## Why

The exploratory fingerprint work (`docs/kwp_hypotheses.md` exploratory sections) found:

- Common function shapes form a lattice. 196 of 199 growth edges among the 200 commonest shapes add exactly one signal.
- The shapes cluster into families: public / general (F7), private C + pointers (F8), bare one-step (F6), annotated /
  test (F3), and smaller ones.

Two practical questions follow:

1. **LAT-F:** do different kinds of fix land in different families?
2. **LAT-M:** does *how* a function moves on the lattice say anything about regressions that churn does not?

## Priors from this program (stated so the bar is honest)

- **Change vs regressions:** CHG-2 found that engine change features **lowered** churn's regression recall@20%
  (41.3% → 38.7% forward; 36.7% → 33.8% leave-one-repo-out). "Shape change" was mostly edit size. CHG's 2.9× was
  mostly churn.
- **Stability:** archetypes persist through 88% of edits (NH). Project fingerprints are stable across eras
  (SIG / SFS). Many functions never change shape.
- **Fix signatures exist:** FIXK found that CVE fixes gain branch, pointers, structural keywords and `#define`, and
  that regression fixes gain new functions, globals and state (Jaccard 0.17 between the two). Structure-at-birth
  and atypicality hypotheses were null (INT-S, ARCH-Z, OUT-H1).
- **Expectation:**
  - LAT-M1 is most likely null. It tests whether structuring change by the lattice rescues what raw |Δsignal|
    features could not.
  - LAT-F is more plausible, because FIXK already shows class-specific signals.

## Frozen inputs

- **Lattice and families:** `docs/fingerprint_trees_exploratory.json` (sha256 prefix `a27d2c93f817`).
  - Contents: the 200 commonest population signatures (v2.12.0-b64f42bf, 6.94M functions with loc ≥ 3), their
    growth parents, and 14 average-linkage Jaccard families.
  - Families are unsupervised; no fix label was used to build them.
- **Family assignment of any function:** the family of its nearest top-200 shape by Jaccard over the shared signal set.
  - Ties go to the more common shape.
  - A function with no signal in common with any top-200 shape is "unassigned" and reported.
- **Rung** = the number of signals present (k).
- **Grammar for "half-steps":** the 32 GR consensus pairs (KW-R / GR), positive pairs only.
- **Signal namespace:** every source is mapped to `function_data` column names via the engine's `SHORT_KEY_MAP`
  (gitgalaxy#8009 `SIGNAL_DISPLAY_NAMES`). Signals absent at function level (gitgalaxy#8012) are dropped.
- **Rule version:**
  - LAT-F uses FIXK's per-function signals (engine C rules at the FIXK pin).
  - LAT-M uses the per-snapshot scan DBs behind NH and CHG-2.
  - Both predate the #8010 / #8011 / #8016 rule fixes; see Sensitivity.

## LAT-F — do fix kinds live in different families? (C/C++, FIXK commit set)

- **Units:** functions touched by FIXK's 23,110 classified fix commits with kept C/C++ files. Classes:
  - latent-CVE: 613 commits;
  - regression: 644;
  - extrinsic: 1,869;
  - other-fix: 19,984.
- **Shape:** the **pre-fix** shape (the parent blob), so the outcome cannot define the exposure.
- **Strata:** repo × log10(loc) bin of 0.2.
- **Clustering:** file-cluster bootstrap, 2,000 rounds.

| id | claim | test | bar |
|---|---|---|---|
| **LAT-F1** | latent-CVE fixes land in the private-C upper rungs (family F8 and k ≥ 6) more than other fixes | MH rate ratio, latent vs other-fix, exposure = pre-fix shape in F8 ∧ k ≥ 6 | RR ≥ 1.25 and 99% lower bound > 1 |
| **LAT-F2** | the four fix classes differ in pre-fix family × rung beyond size | Cramér's V of class × (family, rung band k ≤ 3 / 4–5 / ≥ 6); null = class labels permuted within repo × size strata, 2,000 permutations | p < 0.01 |
| **LAT-F3** | F2 is not a size artefact | the F2 statistic on shapes simulated from the size-only placebo (per-signal logistic on log loc, KW style) | observed V > the placebo's 99th percentile |

- **Descriptive** (not tested): per class, the top families and rungs; per family, the share of each fix class.
- **Use if supported:** review routing ("CVE-class risk concentrates in these families").

## LAT-M — do lattice moves predict regressions beyond churn? (CHG-2 unit set)

- **Units:** CHG-2's function × snapshot-interval units in its five repos: 1,526,252 units, 1,188 regression-hit.
  Same regression labels, same forward split (train < 2020, test ≥ 2020), same leave-one-repo-out folds.
- **Baseline B0:** CHG-2's churn + size model, unchanged.
- **M2 model:** B0 + lattice-move features, computed from presence vectors at the interval's start and end:

| feature | definition |
|---|---|
| moved | shape changed |
| step | Hamming distance |
| jump | step ≥ 2 |
| climb | Δk > 0 |
| descend | Δk < 0 |
| family_change | the assigned family differs |
| half_steps | number of signals gained whose positive consensus partner is absent at the end |
| off_lattice | the end shape is not among the top 200 and has no top-200 one-signal neighbour |

| id | claim | test | bar |
|---|---|---|---|
| **LAT-M1** | lattice moves add regression recall beyond churn | recall@20% of LOC-ranked units, M2 − B0, forward **and** leave-one-repo-out; file-cluster bootstrap | difference ≥ +2.0 points **and** lower bound (α 0.01/2) > 0 in **both** |
| **LAT-M2** | half-step edits precede regressions | among edited units (churn > 0): half_steps ≥ 1 vs 0 → regression-hit; MH strata = repo × churn decile × log-size bin | RR ≥ 1.25, 99% lower bound > 1 |
| **LAT-M3** (pipeline control) | shuffling move features within churn × size strata removes any gain | M1 statistic with features permuted | \|difference\| < 1.0 point, otherwise the M results are void |

- **Descriptive** (not tested):
  - share of functions whose shape never changes over their life (the owner's observation);
  - the transition matrix between families;
  - climb / descend rates by age;
  - the most common single-signal moves.
- **Use if supported:** a review-time change-risk flag ("this edit is a half-step").
- **If null:** close the "lattice as risk signal" line. The lattice stays a descriptive and stratifying tool.

## Sensitivity (pre-stated, reported beside every result)

Re-run every test excluding the signals the open rule fixes change:

- `def_safety`, `state_pointers` (#8010, C `size_t`);
- `def_sync_locks`, `arch_io`, `arch_concurrency`, `state_memory_alloc`, `def_cleanup` (#8016, kernel / Windows
  vocabulary).

A verdict that flips under the sensitivity run is reported as **fragile**.

## Multiplicity and decision

- **Two families of tests:** LAT-F (α = 0.01) and LAT-M (α = 0.01, two-sided bounds as stated).
- **No reruns with changed bars.** Any deviation is recorded as a dated amendment before the affected numbers.
- **Disclosure:**
  - public files carry aggregates only;
  - per-function CVE specifics stay in `temporal-crucible-pool/vz_private/`.
