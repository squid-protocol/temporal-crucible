# GR — does the crucible's keyword grammar hold in the five C repos, and do functions that break it (or drift from it) attract latent or regression fixes? — registered 2026-11-06, before any GR statistic on the five repos

**Why.** On the language-crucible, yes/no signal presence with a continuous size model (KW, exploratory) showed a
modest cross-language grammar. Size-only placebo 0.003; real cross-language r 0.112. Defensive-control signals
(guards, early exits, cleanup, concurrency) travel together; interface and state-mutation code keep apart from them.

GR asks whether that grammar:
1. holds on **independent** code: the five study repos, none of which is in the crucible's C sources;
2. predicts **where fixes land**, both for functions that are atypical and for functions that drift away from it.

## Grammar (fixed now, from the crucible only)

- **Measure:** KW's exploratory one (`tools/exploratory/kw_presence_oe.py`), recomputed deterministically on the
  crucible scan (`kw_scan`, engine `32619e4a5`).
- **Consensus pairs:** signal pairs defined in ≥ 11 crucible languages whose median log(O/E) has ≥ 70% sign agreement.
- **Weight w_ij** = that median log(O/E).
- **Grammar fit** of a function:
  - **G(f)** = Σ w_ij over consensus pairs whose two signals are **both present** in f, minus Σ w_ij over positive
    pairs where **exactly one** is present.
  - Restricted to pairs whose signals both exist in the repo, i.e. are used, with prevalence 2–98% in its latest
    snapshot.
  - Low G = an atypical combination: co-occurrences the grammar avoids, and partners the grammar expects but that are
    missing.

## Data

- **Repos:** curl, OpenSSL, harfbuzz, nDPI, libarchive, with their quarterly engine snapshots (the NH and CHG DBs).
  C/C++ functions with loc ≥ 3, CHG's identity rule and transitions.
- **Engine-pin caveat:** these DBs come from earlier study pins (`32619e4a5`, `da852aa54`, `e246915aa`). Signal
  definitions may differ slightly from the crucible scan.
- **Fix labels:** CHG's (XC rules v2; harfbuzz security fixes as latent; regression = "regression word" only); CHG's
  tree-sitter fix-to-function mapping with amendment A1. Outcome: the function is hit by a fix of class X within
  180 days after snapshot k+1.

## Claims (α = 0.01/4)

| id | claim | test | supported iff |
|---|---|---|---|
| **GR-H1** | **the grammar exists in the five repos** | in each repo's latest snapshot, recompute log(O/E) with the same continuous size model; sign agreement with the crucible's consensus sign, over consensus pairs available in C | pooled over repos: agreement > 50%, exact binomial p < α; reported per repo |
| **GR-H2** | **atypical functions attract latent (CVE) fixes** | function × quarter units with ≥ 2 used signals present; "atypical" = bottom quintile of G within (repo × loc bin × number of present signals); MH RR vs the rest, file-cluster bootstrap (CHG's) | RR > 1 and lo > 1 |
| **GR-H3** | …**and regression fixes** | the same, outcome regression | RR > 1, lo > 1 |
| **GR-H4** | **drifting away from the grammar precedes regressions** | transitions where G **drops** by ≥ 1 unit vs transitions where G is unchanged, among edited functions (loc or signals changed); strata repo × loc bin × CHG fingerprint state | RR > 1, lo > 1 |

- The strata in H2 and H3 include **the number of present signals**, so "more signals = more fixes" cannot drive
  the result.
- **Not evaluable** if < 30 outcome events on either side.

**Descriptive.**
- Other-fix and extrinsic rates by G quintile.
- Per-repo RRs.
- The share of edits that move G up vs down: do edits drift toward the grammar?
- The pairs most often violated in fixed functions.

## Priors

- **H1 likely**, given the cross-language agreement.
- **H2 uncertain.** Atypical combinations might mark odd, hand-rolled code where CVEs live, or might be noise.
- **H3 uncertain.**
- **H4 uncertain.** CHG-2 found that change features add nothing beyond churn, but H4 compares within edited functions
  and asks about direction.
