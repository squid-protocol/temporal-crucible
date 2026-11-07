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
