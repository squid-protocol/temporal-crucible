# CPF — does a file's comment profile predict its next year of fixes, beyond size and history? — registered 2026-11-11 (owner OK), before any outcome was joined to a profile

**Why.**
- Function-grain comment studies gave thin effects. DC-2 (danger comments → 1.45× first CVE) is real, but DCS, CF-H2
  and COM-H4 found no usable per-function signal. The owner asked (2026-11-11) for comments analysed as a whole.
- The exploratory profile study (`docs/comment_profiles_exploratory.md`, outcome-blind) found large, stable
  structure at file and system grain. Nine C systems differ several-fold in comment density and header coverage,
  and files keep their commenting culture for years.
- Whether that structure relates to fixes has not been looked at. This registration fixes the test before any
  profile is joined to an outcome.

## Prior work

- **This program.**
  - "Everything structural reduces to file size" (HYPOTHESES summary): FWD, FREC, ARCH-Z, INT and CEN at file grain.
  - CHG-2 / LAT-M: churn and history dominate next-fix prediction.
  - DC-2 / SCAR-I2: danger comments at birth flag CVE risk, beyond file history.
  - The profile study above (exploratory, no outcomes).
- **Ibrahim, Bettenburg, Adams and Hassan, "On the relationship between comment update practices and software
  bugs", JSS 85(10), 2012, doi 10.1016/j.jss.2011.09.019.** In FreeBSD, PostgreSQL and Eclipse, comment-update
  practices helped explain future bug fixes at subsystem grain, alongside traditional bug-prediction metrics.
  Checked 2026-11-11.
- **Fluri, Würsch and Gall, WCRE 2007, doi 10.1109/WCRE.2007.21.** Newly added code is rarely commented; 97% of
  comment changes happen in the same revision as the code change. Checked 2026-11-11. This motivates the "neglect"
  measure: code that grows without its comments.
- **This study's difference:**
  - file grain;
  - a size + churn + fix-history baseline that the profile must beat;
  - CVE fixes as a separate outcome;
  - a later-era holdout;
  - replication on four repos never used for comment work.
  - It **tests** Ibrahim et al.'s comment-practice → bugs link (PostgreSQL is in both studies), and the program's
    "reduces to size" finding, for comments.

## Data

- **Repos.**
  - **core:** curl, OpenSSL, nDPI, harfbuzz, libarchive.
  - **unseen** (never used in a comment study with outcomes): libgit2, libxml2, postgres, redis.
- **Profiles:** `tools/comment_profiles.py` (as committed in #142) at each repo's quarterly snapshots, from git with
  the engine at gitgalaxy `c7cdf7832`. Profiles are per file:
  - density (body comment lines ÷ code lines);
  - header coverage;
  - danger share (DC lexicon);
  - TODO/FIXME debt per kloc;
  - commented-out code per kloc.
- **Anchors:** for each repo, the last quarterly snapshot of each calendar year, if the repo's fix labels run ≥ 12
  months past it.
- **Unit:** a file-year, meaning a C/C++ file at an anchor with ≥ 50 code lines and ≥ 1 function. Paths under
  tests/, docs/, fuzz/, scripts/ and examples/ are excluded at any depth, as in the profile study.
- **Fixes:** `chg_eval.fix_events` (the `<repo>_xc.json` labels; harfbuzz CVEs from `events/harfbuzz.json`). A fix
  touches a file if the fix commit modifies that path (`git diff-tree`).
  - **any fix** = every class `fix_events` returns;
  - **CVE fix** = the `latent` class.
- **Outcomes**, in the 12 months after the anchor:
  - **Y_fix:** ≥ 1 fix touches the file.
  - **Y_cve:** ≥ 1 CVE fix touches it. Only curl, OpenSSL, nDPI and harfbuzz have enough CVE labels; libxml2 has 41,
    and is descriptive only.

## Features

| family | features |
|---|---|
| **B, baseline** (every model) | log code lines; repo (one-hot); log1p fixes touching the file in the 12 months before the anchor; log1p commits touching it in those 12 months (churn); log1p file age in years (since first seen at a snapshot); file had a CVE fix before the anchor |
| **P, comment profile** | density, header coverage, danger share, debt / kloc, dead / kloc. Transformed `log1p(x · s)` with s = 10, 1, 10, 1, 1 |

- **Model:** L2 logistic regression with standardized features. C is chosen from `logspace(−3, 2, 11)` by 5-fold
  file-grouped CV on the training era, separately for B and B + P. The model is fully specified here, so there is no
  exploratory stage and no freeze commit.
- **Split (outcome-blind, per repo):** anchors in years up to and including the repo's median anchor year →
  **training era**; later anchors → **test era**. All claims are scored on the test era.

## Claims (α = 0.01/4; file-cluster bootstrap 2,000 rounds, seed 2982, on the test era)

| id | claim | supported iff |
|---|---|---|
| **CPF-F** | in the core repos, P adds to B for predicting next-year **any fix** | AUC lift > 0 and one-sided lower bound (α = 0.0025) > 0 |
| **CPF-V** | in curl, OpenSSL, nDPI and harfbuzz, P adds to B for next-year **CVE fix** | the same; ≥ 20 test-era file-years with Y_cve = 1, else **underpowered** |
| **CPF-R** | the same procedure (own training and test eras) in the **unseen** repos, pooled, for **any fix** | the same |
| **CPF-N** | **comment neglect** precedes fixes. Among file-years whose code grew ≥ 20% over the previous year, files whose body comment lines did not grow have a different next-year fix rate | MH risk ratio of Y_fix, neglected vs not, strata repo × log₁₀ code lines (0.25 decade) × prior-year fix count (0, 1, 2–3, 4+); all nine repos; two-sided 99.75% CI excludes 1, direction named |

- **Null:** a failed lift claim is a **replicated null** if its two-sided 99% CI lies inside [−0.02, +0.02];
  otherwise **inconclusive**.
- **CPF-N power:** ≥ 20 neglected file-years with a next-year fix, else underpowered.

## Descriptive (no verdicts)

- Effort-aware recall at the top 20% of code lines for B and B + P (score ÷ code lines, as in EA/CHG-2).
- Per-repo test-era lifts. Fix labels are known to mean different things per repo.
- Single-measure lifts: B + density only, B + header coverage only.
- Standardized coefficients of P in each model.
- Libxml2's CVE outcome, if it has ≥ 10 test-era CVE file-years.

## Data honesty

- The profile study read no outcome. No profile has been joined to a fix or CVE.
- The fix labels and the file-level fix counts have been used by many earlier studies, but never with comment
  profiles.
- libgit2, libxml2, postgres and redis have not been used in any comment study with outcomes. libxml2 was in DC-R's
  unseen set, at function grain and for CVEs only.

## Priors

- **CPF-F, most likely a replicated null or a tiny lift (< 0.01).** The baseline holds churn and fix history, which
  dominate file-grain fix prediction in this program.
- **CPF-V, small positive possible:** danger wording is a known CVE marker at function grain. **CPF-R, as CPF-F.**
- **CPF-N, direction unknown.** Neglect could mark rushed growth (more fixes) or stable, settled code (fewer).
  Ibrahim et al. found abnormal comment-update practice preceded bugs, so the lean is > 1.

## Known limits

- **File paths are not followed across renames.** A file renamed in the outcome year loses its later fixes, which
  biases toward the null.
- **Fix-touches-file counts every file in a fix commit,** including incidental edits.
- **The test era is later and the repos are larger.** That is a stricter, not a random, holdout.
