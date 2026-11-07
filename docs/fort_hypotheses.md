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
