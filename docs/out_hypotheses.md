# OUT — what code breaks the universal keyword grammar? — registered 2026-11-07, before any OUT statistic

**Why.** KW-P confirmed a cross-language keyword grammar: 78% of pair signs hold across 2.9M independent functions,
and 97% of repos follow it. If almost all code follows it, the functions that break it most may be a distinct
population (generated, minified, vendored, test scaffolding, obfuscated) rather than ordinary hand-written code. That
is the basis of a language-agnostic "unnatural code" detector.

## Data

- **Population DB:** `master_db_v2.12.0-b64f42bf.db`, **all** 745 targets: outlier detection is a product use, so
  crucible-source repos are included.
- **Units:** functions with loc ≥ 3.

## Grammar fit (fixed now)

- **Weights:** GR's 32 crucible consensus pairs, weights w = the crucible median log(O/E), now confirmed by KW-P.
- **Fit:** G(f) = Σ w over pairs with **both** signals present, − Σ w over **positive** pairs with **exactly one**
  present.
- **Strata:** language × log₁₀ loc bin (0.2) × number of consensus signals present (capped at 8). Only strata with
  ≥ 1,000 functions are used.
- **Outlier:** bottom 0.1% of G within its stratum (rank-based).
- **Control:** a function from the same stratum with G between its 40th and 60th percentiles.

## Claims (α = 0.01/2)

| id | claim | supported iff |
|---|---|---|
| **OUT-H1** | grammar outliers are rarely ordinary hand-written code (blind audit) | see the audit below: the share judged "ordinary hand-written" is lower among outliers than among controls by ≥ 20 percentage points, Fisher exact one-sided p < α |
| **OUT-H2** | grammar outliers concentrate in vendored, generated and test paths (automatic) | P(flagged path) for outliers ÷ for **all** functions in the same strata (MH-weighted) ≥ 1.5, with bootstrap (2,000; over outliers) lo > 1 |

**H2 path flag (fixed).** The path matches any of:
- a vendored or generated directory: `vendor`, `vendored`, `third_party`, `thirdparty`, `3rdparty`, `external`,
  `deps`, `node_modules`, `dist`, `build`, `generated`, `gen` or `autogen`;
- a test directory: `test`, `tests`, `testing`, `spec`, `fixture` or `fixtures`;
- `.min.`;
- `_pb2.py`;
- `.pb.go`, `.pb.cc` or `.pb.h`.

Reported both overall and split into vendored / generated / test.

**H1 audit.**
- 40 outliers and 40 matched controls (seed 2982), shuffled.
- Each is shown to a fresh agent as **code only**: the function text from the local checkout (start line, up to
  150 lines) plus its language. **Path, repo and outlier status are withheld.**
- Labels: ordinary hand-written / generated / minified or bundled / vendored third-party / test or fixture /
  obfuscated or suspicious / data table or declarative / unclear.
- Unclear is excluded.
- Labels are hash-locked before comparison.

**Descriptive.**
- The most-violated pairs among outliers.
- Outlier rates by language and by repo.
- Overlap with the engine's own threat signals (`threat_*` > 0).

## Priors

- **H2 likely.**
- **H1 likely,** but "unnatural" hand-written code (heavy macros, odd styles) may dilute it.
