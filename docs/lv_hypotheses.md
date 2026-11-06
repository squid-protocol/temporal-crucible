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

---

## Results — LV-H1..H3, 2026-11-06 (scorer `3a487cd` committed before the join)

- **Data:** 2,419 OSS-Fuzz daily summaries (3 days missing upstream); 75 monthly snapshots (2020-03 → 2026-07).
- **Candidates:** a median of 218 instrumented C files per snapshot.
- Report: `lv_ndpi.md`.

| claim | n | mean lift | lo (α = 0.0025) | 90% CI | verdict |
|---|---:|---:|---:|---|---|
| **LV-H1** frontier finds latent fixes beyond size | 63 | +0.026 | −0.156 | [−0.083, +0.136] | **not supported (inconclusive)** |
| **LV-H2** …more than other fixes | 63 | +0.143 | −0.068 | [+0.018, +0.266] | **not supported (inconclusive)** |
| **LV-H3** reached beats unreached for latent | 63 | +0.088 | −0.022 | [+0.023, +0.151] | **not supported (inconclusive)** |

Descriptive lift by class:

| score | latent | extrinsic | regression | other-fix |
|---|---:|---:|---:|---:|
| frontier | **+0.026** | −0.069 | −0.094 | −0.115 |
| reached | −0.116 | −0.154 | −0.261 | −0.090 |
| unreached | −0.205 | −0.055 | −0.180 | −0.213 |

**Headline → not established on nDPI.**
- Every claim points the predicted way, and H2 and H3 exclude zero at 90%, but none clears the registered α.
- The frontier is the only score that is positive for latent fixes and negative for every other class.

**Why the test is weak on nDPI (descriptive).**
- nDPI's fuzzers already reach **~96% of instrumented lines**: the median file's line coverage is near-saturated, so
  "reached" has little variance.
- Only **18%** of files gain any coverage in a 90-day window.
- In a near-saturated project, discovery cannot be explained by reach.

The registered replication on curl or openssl (lower, moving fuzz coverage) is now the informative test.
Function- or line-grain frontiers, from the per-line HTML reports, are the sharper instrument.

## LV-H4 feasibility (CI coverage)

A pilot built the last quarterly nDPI snapshot in `ubuntu:22.04` with `--coverage` and ran nDPI's own pcap regression
suite (`tests/do.sh`). The build succeeds, and the suite takes about an hour single-threaded. LV-H4 needs ≥ 20 scored
snapshots of CI coverage: on the order of 20–30 container-hours, and older snapshots may need older toolchains.
Not run yet.

**Pilot result (descriptive; no outcome joined).** The last quarterly snapshot (pre-2026-01-01) built and ran nDPI's
suite in **~26 minutes** in the container: 274 tests OK. gcovr reported 307 files.

| | line coverage |
|---|---:|
| **CI suite (the contract)** | **43.5%** of lines; several library files at 0% (bitmap, community-id, filter) |
| **Fuzzers** | ~96% of instrumented lines |

So on nDPI the "fuzz-reached but CI-uncovered" quadrant is large, and LV-H4 has the variance the saturated fuzz-only
test lacked. Recipe: `tools/lv_ci_coverage_build.sh`. At ~26 min per snapshot, 25 quarterly-or-monthly snapshots is
≈ 11 container-hours single-file, fewer in parallel.

---

## LV-R — curl replication of LV-H1..H3 — registered 2026-11-06, before any curl coverage report is downloaded

**What is fixed.** Claims LV-H1..H3, the scorer (`tools/lv_eval.py` at `3a487cd`, unchanged), α = 0.01 / 4, the
block bootstrap, the 90-day window and the 7-day report slack: all exactly as registered for nDPI.

**curl specifics.**
- OSS-Fuzz project `curl`; report paths `/src/curl/<repo path>`.
- Branch `master`, labels `events/curl_xc.json` (rules v2, audited in `xc_label_audit.md`), harvest head `04bfe8f`.
- Monthly snapshots from the first month with a report ≥ 90 days of history behind it.
- Invocation: `--start 2018-12`. The first report is 2018-08-20, so 2018-12 has a 90-day look-back.

**Prior, and why it differs from nDPI.**
- curl's CVEs are mostly **human-reported**, unlike nDPI's OSS-Fuzz-bisected events. The frontier theory therefore
  predicts a **weaker** LV-H1 on curl.
- A null on curl alongside an nDPI positive would itself support "discovery is *the searcher's* exploration".
- LV-H1 **uncertain**; LV-H2 **uncertain**; LV-H3 **leaning supported**: fuzz reach marks exercised code in general.
- **Headline for the pair:** "discovery is exploration" holds across repos iff LV-H1 and LV-H2 are SUPPORTED on curl
  (nDPI was directional only).
