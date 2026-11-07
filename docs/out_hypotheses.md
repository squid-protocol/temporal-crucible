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

---

## Results, stage 1 (`prepare`, scorer `34f21c3`; report `out_prepare.md`)

**Data.** 6,936,799 functions read; 6,549,411 in strata with ≥ 1,000 functions; **4,288 outliers**. The grammar fit
is discrete with many ties, so the rank-based bottom 0.1% holds fewer than 0.1% of functions.

| claim | result | verdict |
|---|---|---|
| **OUT-H2** outliers concentrate in vendored/generated/test paths | flagged 35.4% vs stratum-expected 23.4%: **1.51×** (lo 1.42) | **SUPPORTED** (just over the 1.5 bar) |

**What the enrichment is.** Almost entirely **test** paths: 34.9% of outliers, against 0.4% in vendored or generated
paths.

**Descriptive.**
- Outliers by language: C 1,118, C++ 600, Python 422, Java 355, C# 351.
- Repos with the most outliers: dotnet runtime 467, FreeBSD 347, illumos 219, Kotlin 156.
- **The engine threat-signal columns read 0 for every function** (outliers and all), so the overlap check is
  uninformative. Those `threat_*` function columns appear to be unpopulated in this DB: an engine or DB observation to
  check, not an OUT result.

**Stage 2.** The blind code-only audit (80 packets) is running.

**OUT-H1 blind labels locked before comparison:** `vz_private/out_audit_labels.json`, sha256 `cd8982df35ec3a797255fa5739743a58d810eb85b427d33d882303ce9a524f27`.
