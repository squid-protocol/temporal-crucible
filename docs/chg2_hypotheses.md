# CHG-2 — do the engine's change features rank regression risk better than churn alone? — registered 2026-11-06, before any CHG-2 model was fitted

**Why.**
- **CHG** found that a function whose shape changed in a quarter is 2.9× more likely to get a regression fix in the
  next 180 days than an untouched one, and 1.42× more likely (lo 1.02) than one edited without a shape change.
- Most of that is the classic **churn** effect: recently changed code breaks.
- The product question: **does the engine's view of a change add ranking power beyond line-count churn?** That is the
  bar a user cares about.

## Data

- **Units:** CHG's units. Function × quarter transitions k → k+1 in curl, OpenSSL, harfbuzz, nDPI and libarchive.
- **Snapshots, identity, windows:** as in CHG.
- **Labels:** CHG's regression-word fixes. The function-name join uses amendment A1: (file, name) at the preceding or
  following snapshot.
- **Outcome:** a regression-word fix hits the function within 180 days after snapshot k+1.

**Churn (new).**
- Every first-parent commit of each repo is mapped to functions exactly as CHG maps fixes: tree-sitter at the parent,
  `-U0` hunks.
- Each hunk's (old + new line count) is attributed to the function containing its old-side anchor.
- Per transition, from commits in (snapshot k, snapshot k+1]:
  - `commits` = commits touching the function;
  - `churn` = attributed lines.

## Feature sets (fixed now)

| set | features |
|---|---|
| **B0 churn** (baseline) | log1p(commits), log1p(churn), log10(loc at k+1) |
| **M1 churn + engine change** | B0, plus: shape-changed flag; archetype-changed flag; Δcomplexity and \|Δcomplexity\|; Δlog loc; for each of the 32 `sfs` signals, log1p(\|Δcount\|); log1p(fan-in at k+1); complexity/loc at k+1 |

**Model:** L2 logistic (λ = 1, standardised). Fitted on all training positives and a 1-in-10 sample of training
negatives (weight 10), seed 2982.

## Evaluation: effort-aware recall

- Within the test set, rank units by predicted risk ÷ loc (risk density). Select from the top until **20% of the test
  set's total loc** is reached.
- **Recall@20%** = share of test regression-hit units selected.
- **Bootstrap:** selections fixed from the full test ranking; 2,000-round file-cluster bootstrap of the recall
  difference.

| id | claim | split | supported iff |
|---|---|---|---|
| **CHG2-H1** | engine change features beat churn, **forward in time** | train: transitions with snapshot k+1 before 2020-01-01; test: on or after (all five repos) | recall(M1) − recall(B0) > 0, lo > 0 at α 0.01/2 |
| **CHG2-H2** | …**on a repo the model never saw** | leave one repo out: train on four, test on the fifth; pooled over the five test folds (selection per fold) | same |

- **Not evaluable** if a test set has < 100 regression-hit units (H1), or < 100 pooled (H2).
- **Descriptive:**
  - recall of each set and of a size-only ordering (smallest first, the EA rule's comparator);
  - per-fold H2 recall;
  - top M1 coefficients;
  - recall at 5% and 10% of loc.

## Priors

- **H1 uncertain, leaning modest positive.** CHG-H2 lo was 1.02.
- **H2 uncertain.**
- **If M1 does not beat B0,** the engine's value lies outside regression ranking (identity, provenance, targeting),
  and CHG's H2 is best read as small.
