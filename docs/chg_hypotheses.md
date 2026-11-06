# CHG — does a function's fingerprint change, or its youth, predict regressions? — registered 2026-11-06, before any fix-to-function statistic

**Why.**
- **NH** found infant mortality: young functions change and die far more often than old ones.
- **REG** found that regressions scale with change volume and commit size.
- The owner asks:
  1. When a function's structural fingerprint changes, is it more likely to need a **regression** fix afterwards, and
     is that specific to regressions or just "busy code gets every kind of fix"?
  2. Is young, fluid code **deficient**: more regression fixes, and a higher regression **share** of its fixes?
- **AGE** found CVE fixes land in old code. This asks the mirror question for regressions, at the **function** level.

## Data

- **Repos:** NH's five, with their quarterly engine snapshots: curl, OpenSSL, harfbuzz, nDPI, libarchive (the same
  DBs and snapshot lists as `nh_eval.py`).
- **Functions:** C/C++ functions with NH's identity rule (file, name) plus the move rule.
- **Unit:** one function present at consecutive snapshots k and k+1 (a *transition*).

## Exposures (from the snapshots only)

**Fingerprint state of the transition k → k+1:**
- **shape-changed**: archetype or complexity differs between k and k+1;
- **edited, same shape**: loc differs, archetype and complexity equal;
- **untouched**: loc, complexity and archetype all equal.

**Age at k+1** = time since the function's first snapshot.
- **young** < 1 year; **old** ≥ 3 years.
- Functions present at snapshot 0 have an unknown birth. They count as **old** only once snapshot k+1 is ≥ 3 years
  after snapshot 0 (the lower bound suffices). Otherwise their age is **unknown**: excluded from age claims, its own
  stratum elsewhere.

## Outcomes (fix events, after the exposure)

- **Source:** the audited XC classes (`events/*_xc.json`, rules v2) plus harfbuzz's security fixes as latent, exactly
  as AGE uses them.
- **Regression = the "regression word" rule only.** The "references a commit ≤ 90 days old" rule
  (regression-linked) is **young code by construction**. It is excluded from scoring and reported as a sanity row.
- **Other fixes** = the `other-fix` class (the comparison class for specificity). Extrinsic and latent are
  descriptive.

**Mapping a fix to functions.**
- `git diff -U0 <parent> <fix>` gives each touched C/C++ file's old-side lines; a pure insertion uses its anchor line.
- tree-sitter (C for `.c`/`.h`, C++ otherwise) parses the file at the parent. Each line maps to its enclosing
  `function_definition`, named by its declarator identifier.
- A fix hits (file, name).

**Window.**
- A transition k → k+1 has the outcome **"hit by a fix of class X in the 180 days after snapshot k+1"** (strictly
  after the exposure is observed).
- Its key (file, name) is taken at snapshot k+1.
- Transitions whose window ends after the repo's last labelled fix are dropped.

## Gate (binding)

**G-JOIN.** Of all fix → (file, name) hits, ≥ 80% must match an engine function present at the latest snapshot
before the fix. This checks that tree-sitter and engine names agree. Otherwise the study stops.

## Claims

All rate ratios are Mantel–Haenszel, with:
- 2,000-round **cluster bootstrap over files** (the file is the resampling unit);
- α = 0.01 / 5, one-sided lower bound.

| id | claim | comparison | strata | supported iff |
|---|---|---|---|---|
| **CHG-H1** | a fingerprint change is followed by more regression fixes | shape-changed vs untouched; outcome = regression hit | repo × log₁₀ loc bin (0.1 wide) × age class (young / 1–3 y / old / unknown) | RR lo > 1 |
| **CHG-H2** | …**beyond simply being edited** | shape-changed vs edited-same-shape | same | RR lo > 1 |
| **CHG-H3** | …and it is **specific to regressions**: among functions hit by any fix in the window, a higher share are regression hits | shape-changed vs untouched, restricted to transitions with ≥ 1 regression or other-fix hit; outcome = regression hit | same | RR lo > 1 |
| **CHG-H4** | young code gets more regression fixes | young vs old; outcome = regression hit | repo × loc bin × fingerprint state | RR lo > 1 |
| **CHG-H5** | young code is **deficient**, not just busy: a higher regression share of its fixes | young vs old, restricted to transitions with ≥ 1 regression or other-fix hit | same | RR lo > 1 |

**Per-repo direction (descriptive)**, each claim. **Not evaluable** if either side has < 30 outcome events pooled.

**Descriptive.**
- Latent (CVE) and extrinsic hit rates by fingerprint state and age, the AGE mirror.
- The regression-linked sanity row: it should be strongly young by construction.

## Priors

- **H1 supported** (activity).
- **H2 uncertain.** Structural change vs a plain edit: the real fingerprint question.
- **H3 uncertain.**
- **H4 supported** (NH infant mortality plus REG).
- **H5 uncertain.** That is the "deficient vs merely busy" test.

---

## Gate G-JOIN failed as registered → amendment A1 (2026-11-06, before any claim statistic was computed)

**Run 1 (scorer `6bd6d63`).** G-JOIN = 53,371 / 67,164 = **79.5% → FAIL**. Per the registration, the run stopped
before computing any claim.

**Diagnosis** (8,313-hit sample, all five repos; script recorded in the PR):

| unmatched cause | share of hits |
|---|---:|
| function **born after the preceding snapshot** (present at the next one) | 13.0% |
| file not present in the preceding snapshot (new file) | 5.4% |
| **name disagreement** (mostly tree-sitter mis-parsing macro-wrapped code as functions: `if`, `DEFINE_STACK_OF`, `USE_SSH`) | **3.7%** |

The gate was meant to test whether tree-sitter and engine **names agree**. As written, it also counted fixes to
functions that did not exist yet at the preceding snapshot. Those can never join, and they do not affect any unit: a
unit is a function present at snapshot k+1, and its outcome window starts after k+1. Harfbuzz's fast growth (26% born
after) drove the shortfall.

**A1 (binding for run 2).** G-JOIN v2 is **name agreement**:
- Among hits whose file exists at the preceding snapshot, the share whose (file, name) matches an engine function at
  the preceding **or** the following snapshot must be ≥ 90%.
- Nothing else changes: claims, strata, α and windows are as registered.
- Run-2 results are labelled post-amendment.

## Results — run 2, post-amendment A1 (scorer `10fab74`; report `chg.md`)

**Gate G-JOIN v2: PASS**, 96.3% name agreement (56,413 / 58,578).

**Data.** 1,526,252 function-quarters across five repos. Hit in the 180-day window: 1,188 regression-word,
59,650 other-fix.

| claim | MH RR | lo | verdict |
|---|---:|---:|---|
| **CHG-H1** shape-changed vs untouched → regression | **2.88** | 2.18 | **SUPPORTED** (curl 2.7, OpenSSL 4.0, harfbuzz 2.2, nDPI 2.7) |
| **CHG-H2** shape-changed vs edited-same-shape → regression | **1.42** | 1.02 | **SUPPORTED, barely** (curl 1.38, OpenSSL 1.19; other repos too few) |
| **CHG-H3** regression share among fixed: shape vs untouched | **1.47** | 1.12 | **SUPPORTED** (four repos 1.2–1.7) |
| **CHG-H4** young vs old → regression | 1.23 | 0.73 | **not supported** (curl 0.80, OpenSSL 1.57, harfbuzz 3.38, libarchive 1.03) |
| **CHG-H5** regression share among fixed: young vs old | **0.77** | 0.45 | **not supported**: young code's share is *lower* (1.7% vs 2.4%), except harfbuzz (2.39) |

**Reading.**
1. **A fingerprint change is a real warning sign.**
   - Functions whose archetype or complexity changed in a quarter are **2.9× more likely to get a regression fix**
     in the next six months than size-matched untouched functions.
   - They are **1.4× more likely than functions edited without a shape change**. The edge over plain editing holds
     but is modest (lo 1.02, two repos evaluable).
   - It is **specific**: among functions that got any fix, a higher *share* were regressions (1.47×).
2. **Young code is busy, not deficient.**
   - Young functions get about twice the fixes of every kind (other-fix 65 vs 33 per 1,000 quarters).
   - Their regression rate is not reliably higher once size and change state are matched.
   - Their regression *share* is lower.
   - The circular regression-linked sanity row behaves as expected: 4.6 young vs 2.6 old.
   - **Harfbuzz is the exception** (H4 3.4, H5 2.4).
   - Together with AGE (CVE fixes land in old code), this says **deficiency shows up as *change in shape*, not as
     youth.**

**Caveats.**
- Gate amended after run 1 (documented above, before any claim statistic).
- Regression-word labels are rare: 648 events, 1,188 hit units.
- Snapshots are quarterly, so "shape change" is quarter-level.
- H2 is only evaluable in curl and OpenSSL.
