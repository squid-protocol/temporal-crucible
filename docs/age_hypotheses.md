# AGE-H1..H4 — the age signature of fix classes: how old is the code each kind of fix changes? — registered 2026-11-06, before any blame statistic

**Why.** NH found that young code is unstable (it dies young and changes shape often) and old code freezes. XC found
three kinds of fix with different causes. Putting them together predicts an **age signature**:
- **regressions** change *young* code (the change process breaks recent work);
- **latent CVEs** change *old* code (defects survive in frozen code until someone searches it);
- **extrinsic** fixes have *no* particular age (they land on the coupling boundary regardless).

**Measure: the age of the code a fix changes.**
- For each fix commit: the parent-side lines it deletes or modifies in C/C++ files (`git diff -U0`).
- Each line is dated by `git blame --line-porcelain <parent>` (committer time of the line's last change).
- Line age = fix committer time − line committer time.
- **Fix age = median line age over its changed lines.**
- Fixes with no parent-side changed lines (pure additions) are excluded; their share is reported.
- This needs no function tracking, so it has no rename or left-truncation problem.

**What has been looked at.** Class counts per repo. No blame has been run.

## Labels and the circularity guard

- **Classes:** XC labels (`events/*_xc.json`, rules v2). harfbuzz's latent class is its OSV security fixes
  (`events/harfbuzz.json`), with those SHAs removed from its other classes.
- **Regression (scored):** only events labelled by the **regression word** (`why = "regression word"`). Those labels
  carry no age constraint.
  - Events labelled by referencing a commit ≤ 90 days older, or by reverting one, are young *by construction*. They
    are reported as a **sanity check only, never scored**.
- **Baseline:** `other-fix`, the generic fixes.
- **Sample:** per (repo, class), up to 300 events, seeded (2982) random sample; all events if fewer.
- **Repos.**
  - Latent and extrinsic: curl, nDPI, openssl, harfbuzz.
  - Regression: curl, openssl, harfbuzz (nDPI has 6 regression-word events; libarchive's regression labels are
    withheld).
  - A (repo, class) cell with < 30 measured fixes is not evaluable.

## Claims

Effect = median log₁₀(fix age, days) of the class − the same for `other-fix`, within repo. Pooled = the mean over
evaluable repos. Bootstrap: fixes resampled within each (repo, class), 5,000 rounds, seed 2982.

| id | claim | supported iff |
|---|---|---|
| **AGE-H1** | regression fixes change **younger** code than generic fixes | pooled effect < 0, upper bound (α = 0.01/4) < 0 |
| **AGE-H2** | CVE fixes change **older** code than generic fixes | pooled effect > 0, lower bound > 0 |
| **AGE-H3** | CVE fixes change older code than regression fixes | pooled (latent − regression) > 0, lower bound > 0, over repos with both |
| **AGE-H4** | extrinsic fixes have **no** age signature | pooled effect's 90% CI inside ±log₁₀(1.5) (within a factor of 1.5) |

**Descriptive.**
- Median ages in days per (repo, class).
- The construction-linked regression events, as a sanity check.
- The pure-addition share per class.

## Priors

- H1 **leaning supported**.
- H2 **leaning supported**: curl's median CVE lurk is about 4.5 years.
- H3 **leaning supported**.
- H4 **uncertain**: platform code may be older on average, since adapters accumulate.
