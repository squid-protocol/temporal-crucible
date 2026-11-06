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
