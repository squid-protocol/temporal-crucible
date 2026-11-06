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

---

## Results — 2026-11-06 (scorer `eebc7ae` committed before running; report `age.md`)

4,153 fixes blamed (up to 300 per repo and class).

| claim | repos | pooled effect (log₁₀ days) | factor | 90% CI | verdict |
|---|---|---:|---:|---|---|
| **AGE-H1** regression vs generic | curl, openssl, harfbuzz | −0.005 | ×0.99 | [−0.109, +0.191] | **not supported** |
| **AGE-H2** CVE vs generic | curl, nDPI, openssl, harfbuzz | +0.007 | ×1.02 | [−0.178, +0.199] | **not supported** |
| **AGE-H3** CVE vs regression | curl, openssl, harfbuzz | +0.050 | ×1.12 | [−0.185, +0.248] | **not supported** |
| **AGE-H4** extrinsic has no signature | curl, nDPI, openssl, harfbuzz | −0.061 | ×0.87 | [−0.208, +0.093] | **not supported** (inconclusive) |

Median age of the changed code (days; n):

| repo | generic | regression (word) | regression-linked (sanity) | CVE | extrinsic |
|---|---:|---:|---:|---:|---:|
| curl | 448 (253) | 144 (209) | 41 (277) | **733** (154) | 509 (246) |
| nDPI | 139 (272) | — | 25 (50) | 109 (97) | 222 (39) |
| openssl | 320 (258) | 278 (113) | 14 (257) | **908** (182) | 196 (231) |
| harfbuzz | 71 (265) | 247 (159) | 0 (259) | **21** (70) | 37 (134) |

**Headline → no pooled age signature.** None of H1–H4 holds when the repos are averaged.
- The sanity row behaves as built: regressions linked to a commit ≤ 90 days old change code aged 0–41 days.

**Why the pool is flat (exploratory, not a verdict): the CVE effect splits by who finds the bugs.**

| repo | how its CVEs are mostly found | CVE vs generic fix age |
|---|---|---|
| curl | human reporters | **×1.6 older** (733 vs 448 days) |
| openssl | human reporters | **×2.8 older** (908 vs 320) |
| nDPI | OSS-Fuzz | ×0.8 (109 vs 139) |
| harfbuzz | OSS-Fuzz | **×0.3 younger** (21 vs 71) |

- **Human-found CVEs** sit in code ~2–2.5 years old: old, frozen code that someone eventually audited.
- **Fuzzer-found CVEs** sit in code days to months old. Continuous fuzzing catches bugs soon after they are written.

This is the same split seen in LV (frontier), INP (input surface) and KF (curl): **a latent defect's age at discovery
is set by the searcher, not only by the code.**
- Pooling the two discovery regimes cancels the effect.
- A registered test splitting repos by discovery process (or splitting CVEs by reporter, e.g. curl advisories that credit
  OSS-Fuzz) is owed.

**Regression word labels** are mixed: younger than generic on curl (144 vs 448) and openssl (278 vs 320), older on
harfbuzz (247 vs 71). The age-independent regression labels show no consistent age signature.
