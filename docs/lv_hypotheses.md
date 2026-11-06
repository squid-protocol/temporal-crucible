# LV-H1..H4 — where and when are latent defects found? The search frontier on nDPI — registered 2026-11-06, before any coverage × outcome join

**Question.** The owner's framing: CI is the intrinsic contract, and latent defects are what the contract never pinned
down. Outside search (fuzzers, users) discovers them. The design note (`latent_verification_surface.md`) proposes that
**discovery is exploration**: latent defects are found where search has just arrived.

**What has been looked at before this entry.**
- The list of OSS-Fuzz nDPI report dates (2,422 days, 2019-11-06 → 2026-11-06).
- One report's schema (per-file lines / functions / regions / branches).
- The date range of the 105 XC latent labels on nDPI (2019-11-12 → 2026-05-02).
- No coverage figure has been joined to any file-level label.

## Data

- **Search coverage.** OSS-Fuzz daily `summary.json` for nDPI (`gs://oss-fuzz-coverage/ndpi/reports/<day>/linux/`),
  mirrored at `temporal-crucible-pool/ossfuzz-coverage/ndpi/`.
  - Paths `/src/ndpi/<repo path>` map to repo paths; files outside `/src/ndpi/` are dropped.
  - Per file and day: `lines.count`, `lines.covered`.
- **Snapshots.** Monthly: for each calendar month from 2020-03 (so a 90-day look-back exists) to the last month whose
  boundary + 90 d precedes the harvest head:
  - t = the last first-parent `dev` commit before the boundary;
  - the coverage report used is the latest one dated ≤ t's boundary and within 7 days of it;
  - with no such report, the snapshot is dropped.
- **Candidates.** C files (`.c`/`.h`) present at t that appear in that report with `lines.count` > 0, i.e.
  instrumented fuzz-build code. Size = the report's `lines.count`, so size is the coverage tool's own line count.
- **Outcome.** XC labels (`events/ndpi_xc.json`, rules v2). Positive for class K = touched by a class-K commit in
  (t, t + 90 d]. A 90-day window, shorter than XC's, because snapshots are monthly.

## Scores (read at t; higher = review first)

| name | definition |
|---|---|
| **frontier** | newly covered lines per line: max(0, covered_t − covered_{t−90 d}) / count_t, using the report nearest t − 90 d (± 7 d). A file absent 90 days earlier counts covered_{t−90} = 0 |
| **reached** | covered_t / count_t (fuzz line coverage) |
| **unreached** | 1 − reached |

## Claims

Lift = recall@20 (EA's rule, size = `lines.count`) minus the stronger of the two size orderings.

| id | claim | supported iff |
|---|---|---|
| **LV-H1** | latent defects are found at the search frontier | mean lift(frontier, latent) > 0, lo > 0 |
| **LV-H2** | …specifically: the frontier is not where extrinsic or regression fixes go | mean of [lift(frontier, latent) − lift(frontier, other-fix)] > 0, lo > 0 |
| **LV-H3** | discovery needs reach: fuzz-reached code carries the latent fixes, not unreached code | mean of [lift(reached, latent) − lift(unreached, latent)] > 0, lo > 0 |
| **LV-H4** (conditional) | the contract gap: at equal size, latent fixes land in fuzz-reached code the **CI suite does not cover** | evaluated only if CI-coverage builds succeed on ≥ 20 scored snapshots; score = fuzz-covered-but-not-CI-covered lines per line; mean lift(latent) > 0, lo > 0 |

LV-H4's CI coverage: build t with `--coverage` (gcc/gcov) and run the repo's own test target. A per-file line set
stands for the contract. Its build recipe is fixed in a tool committed before any LV-H4 join.

**Tests.**
- Monthly snapshots overlap in outcome windows, so the bootstrap resamples **blocks of 3 consecutive snapshots**
  (5,000 rounds, seed 2982).
- α = 0.01 / 4 one-sided.
- < 20 scored snapshots = not evaluable. Equivalence null: 90% CI inside [−0.02, +0.02].

**Headline.**
- **Discovery is exploration (on nDPI)** iff LV-H1 and LV-H2 are SUPPORTED.
- LV-H3 says whether *reach* alone, not its recency, matters.
- Replication is owed on curl or openssl, which also have OSS-Fuzz histories, with their own labels.

## Priors

- LV-H1 **leaning supported**: OSS-Fuzz files a bug within days of the fuzzer reaching it, and nDPI's events are
  OSS-Fuzz-bisected.
- LV-H2 **uncertain**: new coverage also follows new code, which draws every class of fix.
- LV-H3 **leaning supported**.
- LV-H4 **uncertain**; feasibility is the first risk.
