# LAT — the fingerprint lattice: fix families (LAT-F) and lattice moves (LAT-M)

**Status: REGISTERED 2026-11-07.** The owner OKed the draft ("lets start these experiments"). No outcome data has
been read for these hypotheses. The scorer (`tools/lat_eval.py`) is committed after this registration and before any
run.

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

## Amendment 0 — pre-run clarifications (2026-11-07, at registration, before the scorer exists or any data is read)

The draft left these operational choices open. They are fixed here, before any outcome statistic.

1. **Half-step.**
   - A signal *gained* in an interval (absent at the start, present at the end) is a half-step when it has at least
     one positive GR consensus partner and **none** of those partners is present at the end. It arrived without its
     usual companions.
   - `half_steps` = the number of such gained signals.
2. **Lattice signal set.**
   - The union of signals appearing in the 200 frozen shapes, as `function_data` column names.
   - Shapes, rungs (k), families and Jaccard distances are all computed on this set, intersected with the signals
     each data source provides.
3. **LAT-F measurement (pre-fix shape).**
   - **Locating the function:** for each FIXK fix commit, map changed lines to function definitions in the
     **parent** blob, with tree-sitter (`chg_eval.map_fix` logic), C or C++ by extension as in FIXK.
   - **Measuring it:** the function's text is reduced to the engine's comment-free code stream (Prism), then the
     engine's C/C++ keyword rules (engine `32619e4a5`, the version behind the LAT-M scan DBs) give presence per rule.
   - **Naming:** rule keys are mapped to column names with the engine's `SHORT_KEY_MAP`.
   - **Exclusions:** functions under FIXK's excluded paths (`tests/`, `docs/`, `.github/`, `scripts/`).
   - **Units and size:** one unit per (commit, function). Size = the function's line count in the parent.
4. **LAT-F classes:** latent (CVE), regression, extrinsic, other-fix, as in FIXK. `regression-linked` is excluded.
   Cluster for the bootstrap = repo:file.
5. **LAT-F2 / F3 details.**
   - Categories: family (14) × rung band (k ≤ 3, 4–5, ≥ 6).
   - F3 uses 200 placebo draws: each signal re-drawn from a per-repo logistic in standardised log10 size, fitted on
     all touched functions.
6. **LAT-M features.**
   - Computed on the CHG-2 units' start and end signal vectors (presence = value > 0), restricted to the lattice
     signal set.
   - `off_lattice` = the end shape is not one of the 200 and none of its one-signal neighbours is.
7. **LAT-M3 permutation.** Lattice features are permuted jointly (rows shuffled) within churn decile × log-size bin
   strata, in train and test, then M2 is refitted.

## Results (scored 2026-11-07; `tools/lat_eval.py` at c5e478e; full output `docs/lat.md`)

| id | verdict | result | sensitivity |
|---|---|---|---|
| **LAT-F1** | ✗ not supported | CVE-fixed functions in private-C upper rungs 59.3% vs other-fix 56.9%; MH RR 1.08 [1.00, 1.14] (bar 1.25) | same (1.08 [1.00, 1.17]) |
| **LAT-F2** | ✓ supported | fix classes × family/rung, Cramér's V 0.068, within-stratum permutation p 0.0005 | same |
| **LAT-F3** | ✓ supported | V 0.068 vs size-only placebo 99th percentile 0.043 | same |
| **LAT-M1** | ✗ not supported | recall@20%: forward 42.5% → 42.9% (+0.5, lo −1.9); LORO 36.6% → 36.6% (+0.0, lo −2.0) | same |
| **LAT-M2** | ✗ not supported (underpowered) | 2,007 half-step units, only 5 regression-hit; RR 1.23 [0.20, 3.17] | same |
| **LAT-M3** | ✓ control passed | permuted features: forward +0.0, LORO −0.8 points | — |

**Reading.**
- **The fix kinds differ by shape, beyond size, but modestly** (V 0.07).
  - Regression fixes sit in *lower* rungs: k ≤ 5 in 18.5% of them vs 7.9% of other fixes. They hit simpler
    functions, more often in the private-C family (F8: 70% vs 61%).
  - CVE fixes look like ordinary fixes (F8 64% vs 61%), so the specific F1 prediction fails.
  - Useful for describing and routing fixes; not a detector.
- **Lattice moves add nothing to regression prediction beyond churn,** as the CHG-2 prior predicted. Structuring
  change by the lattice does not rescue it. The half-step idea could not be tested properly: only 5 events.
- **Descriptive:**
  - 70.9% of functions never change shape over their observed life.
  - 82% of edits leave the shape unchanged.
  - Moves are 68% single-signal steps; family changes are mostly F7 ↔ F8 (public ↔ private-C).
  - Edits that move the shape have a *lower* regression rate (0.28%) than edits that do not (0.38%).
- **Closes the "lattice as a risk signal" line.** The lattice remains a descriptive and stratifying tool.
