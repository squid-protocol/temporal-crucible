# SILENT — can a fix's structural change signature pick out security fixes whose commit messages say nothing about security? — registered 2026-11-06, before any SILENT model was fitted

**Why.**
- FIXK found that CVE fixes have a distinctive change signature in the engine's own C rules: more branches, early
  exits, `size_t`/`->` arithmetic and new `#define` limits, beyond patch size.
- Our CVE labels are **advisory-linked** (curl's vulnerability table, OpenSSL advisories, nDPI/OSS-Fuzz,
  harfbuzz's security events). **Most of those commits' subjects contain no security words** (curl 161 / 185,
  OpenSSL 172 / 235, nDPI 69 / 105).
- So we have real "silent patches": security fixes invisible from their commit messages.
- A detector that flags them from code alone has direct value: finding undisclosed security fixes when backporting
  or auditing vendored code.

**⚠ Disclosure.** Unlabelled commits the model ranks highly may be undisclosed security fixes. They are historical
and already fixed, but their list stays **private** (`temporal-crucible-pool/vz_private/silent_candidates.json`).
Public files give aggregates only.

## Data

- **Repos with CVE labels:** curl, OpenSSL, nDPI, harfbuzz. CHG's `fix_events`, which includes harfbuzz's security
  events as latent. libarchive is excluded: it has no CVE labels.
- **Units:** fix commits with ≥ 1 kept C/C++ file (FIXK's rule).
- **Features:** for each of FIXK's 51 engine C rules, *gain* (net ≥ 1) and *loss* (net ≤ −1) flags; plus log₁₀(changed
  lines) and log₁₀(kept files). 104 features.
- **Security words** (subject, case-insensitive): cve, security, vuln…, overflow, use-after-free / uaf,
  out-of-bounds / oob, heap, buffer, dos, denial, exploit, sanitiz…, crash, asan, fuzz, ossfuzz / oss-fuzz.
- **Positives:** latent events.
  - **Silent positives:** latent events whose subject has **no** security word.
- **Negatives:** other-fix events whose subject has no security word ("ordinary fixes"). They may contain
  undiscovered security fixes, which makes the test conservative.

## Model and evaluation

- **Model:** L2 logistic regression (λ = 1, standardised features), trained on all latent vs other-fix commits of
  the training repos.
- **Leave-one-repo-out (4 folds).** Each held-out repo's commits are scored by a model that never saw that repo.
- **Evaluation set:** held-out **silent positives** vs held-out **ordinary negatives**, pooled over folds.
- **Baselines:** (a) patch size only (log changed lines); (b) the four known defensive rules only (branch, safety,
  panics_and_aborts, cleanup, gain and loss flags, plus size).

| id | claim | supported iff |
|---|---|---|
| **SIL-H1** | the signature finds silent CVE fixes beyond patch size | pooled held-out AUC(full) − AUC(size only) > 0; commit-bootstrap (2,000) lo > 0 at α = 0.01/2 |
| **SIL-H2** | it is usable: silent CVE fixes concentrate at the top | the share of silent positives in the top 10% of each held-out repo's evaluation set (by score), divided by their overall share, has lower bound > 1.5 |

**Descriptive.**
- AUC per held-out repo.
- The defensive-rules-only baseline: is the gain beyond the known four rules?
- The most influential features.
- Explicit (security-worded) CVE fixes, for contrast.
- The count of unlabelled ordinary fixes scoring above the median silent positive (private list).

## Priors

- **H1 likely, modest** (AUC gain of a few points): FIXK effects are 1.3–1.7×.
- **H2 uncertain.**

---

## Results — 2026-11-06 (scorer `f6b0b57`; report `silent.md`; candidate list private)

**Data.** 19,088 fix commits. 613 CVE fixes, of which **451 silent**; 17,392 ordinary fixes.

| claim | result | verdict |
|---|---|---|
| **SIL-H1** signature beats patch size on silent CVE fixes (held-out repos) | AUC **0.569** vs size 0.507 (lo +0.012). The four known defensive rules alone give **0.572** | **SUPPORTED, but weak** |
| **SIL-H2** silent CVE fixes concentrate in the top 10% | **1.51×** (lo 1.09; bar 1.5) | **not supported** |

Per held-out repo, AUC full vs size: curl 0.583 / 0.525, OpenSSL 0.573 / 0.579, nDPI 0.571 / 0.499, harfbuzz
0.557 / 0.480. Explicit (security-worded) CVE fixes: 0.554.

**Reading.**
- **FIXK's signatures are population tendencies, not a detector.**
  - The CVE-fix signature is real (FIXK), and it generalises across repos: AUC above patch size in 3 of 4 held-out
    repos.
  - But it separates individual commits barely better than chance.
  - All of the gain comes from the known defensive rules (branch, pointers, exits). The other 47 rules add nothing.
- **Not usable as-is:** 6,315 ordinary fixes score above the median silent CVE fix. 62% of CVE fixes gain a branch
  (FIXK), but so do 42% of ordinary fixes.
- **What might make silent-patch detection work:**
  1. **Combine *where* and *how*:** prior security fixes in the same file (recidivism, RW-H2, the strongest location
     signal), coupling surfaces and defended-code context, alongside the change signature.
  2. A **semantic** reading of the change: is the new branch a comparison against a size or limit followed by an
     exit? That is the FIXK pattern made specific, beyond keyword counts.
  3. The "model judges" route.
- Each needs its own registration.

---

## WH — where + how: does combining location history with the change signature make silent-patch detection usable? — registered 2026-11-06, before any WH model was fitted

**Why.** SILENT's change signature alone ("how") gave held-out AUC 0.569. Location ("where") is the program's
strongest security signal: recidivism (RW-H2), with CVEs landing in already-defended code (GR, FORT). WH tests
whether the two **combine**.

**Data, positives, negatives, folds, model:** exactly SILENT's.
- 4 repos, leave one out;
- silent CVE fixes vs ordinary fixes;
- L2 logistic regression, λ = 1.

**Location features ("where"), from history strictly before each commit:**
- **prior_sec:** log1p of the number of earlier CVE (latent) commits, in the same row set, touching any of this
  commit's kept files; plus an indicator > 0.
- **prior_fix:** log1p of the number of earlier fix commits of any class in the row set touching those files.
- **defended:** guard clauses per 100 lines in the functions the commit touches, at its parent (FORT's guard
  definition and mapping). 0 if no touched function was mapped.

**Models.**

| model | features |
|---|---|
| SIZE | log changed lines, log files |
| WHERE | SIZE + the location features |
| HOW | SILENT full (rule gain/loss flags + size) |
| WHERE+HOW | all of the above |

| id | claim | supported iff (paired commit bootstrap, 2,000; α = 0.01/3) |
|---|---|---|
| **WH-H1** | location adds to the change signature | AUC(WHERE+HOW) − AUC(HOW) > 0, lo > 0 |
| **WH-H2** | the change signature adds to location | AUC(WHERE+HOW) − AUC(WHERE) > 0, lo > 0 |
| **WH-H3** | the combination is usable | top-10% enrichment of silent CVE fixes with WHERE+HOW, lo > 1.5 |

**Descriptive.**
- AUC of all four models, per repo.
- Precision in the top 1%, 5% and 10% vs the base rate.
- The count of unlabelled ordinary fixes above the median silent positive (private list, as SILENT).
