# FORT — are CVE fixes reinforcements of existing defences ("fortification is hard") or new defences on exposed code, and are regression fixes lexically neutral? — registered 2026-11-06, before any FORT statistic

**Why.** CVE fixes concentrate where code is already defended:
- recidivism (RW);
- `goto` error-cleanup (KF-R);
- grammatical defensive-control functions (GR, a reversal observed in exploration);
- CVE fixes typically add branch and pointer checks (W1).

Regressions show no structural or lexical marker (CHG-2, REG, GR-H3). The owner's interpretation: defensive code marks
information flows that demand a priori fortification, fortifications are hard to get right, and regressions are
logic errors.

**Two readings of the CVE side:**
- **Incompleteness:** CVE fixes *reinforce* functions that are already guarded, because a defence was missing a case.
- **Exposure:** CVE fixes *add* defences to unguarded code on hostile data paths.

## Data

- **Repos:** curl, OpenSSL, harfbuzz, nDPI, libarchive.
- **Fix events:** XC rules v2 classes. Latent = CVE fixes, plus harfbuzz's security fixes. Regression = the
  "regression word" rule only. Plus other-fix and extrinsic. As used in CHG.
- **Units:** (fix commit, function).
  - Functions are those whose span, at the fix's parent, contains a changed old-side line (CHG's tree-sitter mapping;
    C parser for `.c`/`.h`, C++ otherwise).
  - **Pre-fix body** = that function at the parent. **Post-fix body** = the same-named function in the same file at
    the fix commit.
  - Units whose function is absent after the fix are dropped.

## Guard clause (fixed now)

A tree-sitter `if_statement` with **no `else`**, whose consequence is:
- a `return`, `goto`, `break` or `continue` statement; or
- a `compound_statement` with ≤ 3 named statements whose last statement is one of those.

**G** = the number of guard clauses in the function body.

- **Adds a guard:** G_post − G_pre ≥ 1.
- **Pre-guarded:** G_pre ≥ 1.

## Claims (α = 0.01/3; Mantel–Haenszel RR over strata of pre-fix function loc in 0.2-wide log₁₀ bins × repo; 2,000-round bootstrap clustered by fix commit)

| id | claim | comparison | supported iff |
|---|---|---|---|
| **FORT-H1** | **CVE fixes fortify** | P(adds a guard): latent vs other-fix touches | RR > 1, lo > 1 |
| **FORT-H2** | **…and what they fortify was already defended** | among touches that **add a guard**, P(pre-guarded): latent vs other-fix | **incompleteness** iff RR > 1 and lo > 1; **exposure** iff RR < 1 and hi < 1; otherwise inconclusive |
| **FORT-H3** | **regression fixes are lexically neutral** | P(adds a guard): regression vs other-fix touches | RR < 1 and hi < 1 |

**Not evaluable:** < 30 latent or regression touches in the needed cell.

**Descriptive.**
- Per class: P(adds guard), P(removes guard), mean ΔG, P(pre-guarded), and net changed-line size.
- Per repo, the H1 and H2 RRs.
- Extrinsic as a second comparison class.

## Priors

- **H1 likely** (W1).
- **H2 uncertain.** This is the question.
- **H3 uncertain.** Regression fixes may revert guard-touching code.

---

## Results — 2026-11-06 (scorer `01d3c9f`; report `fort.md`)

**Data.** 23,737 fix commits → 59,208 fix × function touches: latent 1,570, regression 1,466, other-fix 51,713,
extrinsic 4,459.

| claim | RR [99.67% CI] | verdict |
|---|---|---|
| **FORT-H1** CVE fixes add guards more than ordinary fixes | **1.88** [1.47, 2.39] | **SUPPORTED** (every repo > 1) |
| **FORT-H2** guard-adding CVE fixes: was the function already guarded? | **1.00** [0.91, 1.10] | **inconclusive**: a tight null, neither incompleteness nor exposure |
| **FORT-H3** regression fixes are lexically neutral | **1.56** [1.19, 1.99]: they add guards *more* | **not supported** |

| class | adds guard | removes guard | mean ΔG | pre-guarded |
|---|---:|---:|---:|---:|
| latent (CVE) | **20.1%** | **8.2%** | +0.09 | 72.2% |
| regression | **16.5%** | 4.6% | **+0.16** | 64.4% |
| other-fix | 11.3% | 5.1% | +0.06 | 69.8% |
| extrinsic | 6.6% | 4.2% | +0.00 | 67.0% |

**Reading.**
1. **CVE fixes are fortifications.** One in five adds a guard clause, about twice the rate of ordinary fixes and
   about 4× that of extrinsic fixes.
   - They also **remove** guards more often (8.2%): CVE fixes *restructure* defences, not only add to them.
   - Read with the high add rate, this is the strongest evidence here that **defences are hard to get right**: the
     fix often rewrites the existing guard logic.
2. **Incompleteness vs exposure is not decided by this measure.** About 70% of all touched functions are already
   guarded, whatever the fix class. Guard-adding CVE fixes land in already-guarded code at exactly the base rate
   (1.00, tight).
   - A finer test is needed: is the *new* guard a condition on the same variable an existing guard checks (extending
     a defence), or on a new input (a new defence)?
3. **Regression fixes are not lexically neutral.** They add guards 1.56× as often as ordinary fixes, with the
   largest mean guard gain (+0.16).
   - So a regression is often **a missed case introduced by a change, fixed by adding a check**.
   - Their *location* has no structural marker (CHG-2, GR-H3), but their *repair* has a lexical form.
   - The per-repo split is wide: OpenSSL 1.71 and harfbuzz 1.90, but curl 0.94 and nDPI 0.61.
4. **The owner's interpretation, revised.**
   - CVEs and regressions are **both** repaired by adding defensive checks, more than ordinary bugs are.
   - What differs is **where they arise**: CVEs in long-lived, already-defended code that hostile input reaches;
     regressions wherever code was just changed.
   - "Fortifications are tough to get right" fits both: CVEs are defences that fall short over time, regressions are
     defences that a change broke or omitted.

---

## FORT-V and FIXK — registered 2026-11-06, before either ran

### FORT-V: does a CVE fix extend an existing defence, or add a new one?

FORT-H2 was a tight null at the function level. FORT-V asks at the level of the **guarded variable**.

**Units.** FORT's touches where the pre-fix body has ≥ 1 guard clause **and** the fix adds a **new** guard: a
post-fix guard whose whitespace-normalised condition text is not among the pre-fix guard conditions.

**Identifiers of a guard.** The tree-sitter `identifier` and `field_identifier` nodes in its condition, excluding
ALL-CAPS tokens (macros and constants) and `NULL`.

**Extension.** A new guard is an extension if its identifiers intersect the union of the pre-fix guards'
identifiers. A touch is "extending" if any of its new guards is.

| id | claim | supported iff |
|---|---|---|
| **FORTV-H1** | CVE fixes **extend** existing defences more than ordinary fixes (incompleteness) | MH RR of P(extending), latent vs other-fix, strata repo × loc bin: lo > 1. **Exposure** if hi < 1; else inconclusive. 99.67% commit-cluster bootstrap |

Regression vs other-fix is descriptive.

### FIXK: which structural elements does each fix class add or remove?

**Units.** Fix commits (XC classes, as FORT).
- Patch text = the added and removed lines of `git diff -U0 <sha>^ <sha>` in C/C++ files outside `tests/`, `docs/`,
  `.github/` and `scripts/` (`hunk_grammar.py`'s rule).
- Commits with no kept file are dropped.

**Rules.** The **engine's own** C rules (`LANGUAGE_DEFINITIONS["c"]["rules"]`, pinned checkout `32619e4a5`): every
named rule except the private `_…` keys, 54 in all. Counts are regex `findall` on the added text and on the removed
text.
- **Gains rule k:** added − removed ≥ 1.
- **Loses rule k:** removed − added ≥ 1.

**Comparison.** Each class (latent, regression, extrinsic) against other-fix.
- Cochran–Mantel–Haenszel test and MH RR, stratified by repo × patch size (log₁₀ of changed lines, 0.25-wide bins).
- **Benjamini–Hochberg** over the 54 rules × {gain, loss} within each class.
- A class's **change signature** = rules with BH q < 0.01 **and** RR ≥ 1.25 or ≤ 0.80.

| id | claim | supported iff |
|---|---|---|
| **FIXK-H1** | CVE fixes have structural changes **beyond** the known defensive ones | the latent signature contains ≥ 1 rule outside {branch, safety, panics_and_aborts, cleanup} |
| **FIXK-H2** | regression fixes have a signature | the regression signature is non-empty |
| **FIXK-H3** | CVE and regression signatures **differ** | Jaccard(latent signature, regression signature) < 0.5, with both non-empty |

**Descriptive.** The full gain and loss RR table per class; extrinsic's signature.

### FORT-V and FIXK results — 2026-11-06 (scorer `66bc10e`; report `fortv_fixk.md`)

**Deviation, recorded.** Of the 54 named rules, **51** are regex rules and were counted. The other 3 are
configuration entries.

| claim | result | verdict |
|---|---|---|
| **FORTV-H1** new guards in already-guarded functions check an already-guarded variable (latent vs other-fix) | latent **84.2%**, other-fix 80.3%, regression 83.1%; MH RR **1.04** [0.97, 1.12] | **inconclusive** (a tight null) |
| **FIXK-H1** CVE signature beyond the known defensive rules | `#define` gain (1.65), pointer / `size_t` / `->` gain (1.42), exit-keyword gain (1.28), plus branch (1.40) | **SUPPORTED** |
| **FIXK-H2** regression signature exists | 23 rules (below) | **SUPPORTED** |
| **FIXK-H3** CVE and regression signatures differ | Jaccard **0.17** | **SUPPORTED** |

**Rule names, translated for C** (the engine's C regexes): `reflection_metaprogramming` = `#define` lines;
`structural_boundaries` = mostly `return`/`break`/`continue` plus `struct`/`typedef`/`enum`; `pointers` = `->`,
`size_t`/`ptrdiff_t`, address-of; `encapsulation` = `static`; `immutability_locks` = `const`.

**Reading.**
1. **Extending an existing defence is the norm for every fix class.** About 80–84% of new guards in already-guarded
   functions check a variable an existing guard already checks. CVE fixes are no different. "Incompleteness vs
   exposure" therefore cannot be separated with this measure either: nearly all fortification is incremental.
2. **CVE fixes have a narrow signature: bounds checks with named limits.** They gain branches, early exits, pointer
   and `size_t` arithmetic, and **new `#define` constants**, all beyond patch size. In plain terms: *add a check
   against a named limit, and bail out*.
3. **Regression fixes have a broad, different signature: restructuring.** Versus ordinary fixes of the same size,
   they gain:
   - **new functions** (`func_start` 1.97×, 40% vs 11%);
   - **new globals** (2.52×);
   - `static` helpers (1.72×), `const` (1.58×), arguments (1.49×), state mutation (1.42×), allocation (1.85×),
     locks (rare, 12.9×).

   And they *lose* macros, casts and outgoing calls. A regression fix often **re-architects** the broken change
   (new helper, new state) rather than patching a line. They also add guards (FORT-H3).
4. **Extrinsic fixes are platform adaptation:** macros (2.57×), inline asm, imports, I/O, API surface. This matches
   ENV.
5. **Overall: each fix class leaves a distinct structural change signature in the engine's own rules.**
   - CVE = guarded bounds with limits.
   - Regression = restructuring with new functions and state.
   - Extrinsic = platform macros and imports.
   - The engine reads *how* code is repaired distinctly by class, even though it cannot predict *where* regressions
     occur (CHG-2).
