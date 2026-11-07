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
