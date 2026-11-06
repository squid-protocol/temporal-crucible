# Where do latent defects hide? The verification surface — design note (2026-11-06, not a registration)

**The idea (owner, 2026-11-06).** CI is the repo's intrinsic contract-verification system. Latent defects are those the
contract never pinned down. If we know which code the contract exercises, and which code outside search (fuzzers,
users) has reached, we should be able to say where latent defects are likely still hiding.

## What GitGalaxy measures today

- **A static, 1-hop test map** (`network_risk_sensor.extract_test_coverage_mapping`): functions in test-path files →
  production functions they call directly, through files the test includes.
  - It feeds only the file-level `risk_verification` score. That score reduced to size in H3 / per-vector exposure.
  - No per-function "tested" flag is stored.
- **It misses most real verification in C projects.** curl's ~1,900 tests are data files driving the `curl` binary.
  nDPI's are pcap regressions through `ndpiReader`. Neither appears as test-file → function calls.
- **Static call-graph reachability will not fix this.** From the tool's `main` almost everything is reachable.

## What exists to measure it properly

- **Search coverage history (extrinsic exploration).** OSS-Fuzz publishes a daily per-file `summary.json` (lines /
  functions / regions / branches covered) and per-line HTML for every project:
  - `gs://oss-fuzz-coverage/<project>/reports/<YYYYMMDD>/linux/`;
  - publicly listable;
  - nDPI from 2019-11, curl and openssl from 2018-08 (checked 2026-11-06).
- **Contract coverage (intrinsic verification).** Not published historically. It can be produced by building each
  quarterly snapshot with `--coverage` and running the repo's own suite, then reading gcov/llvm-cov per function.
  - nDPI builds and tests in minutes, so this is feasible for its 43 snapshots.
  - curl's suite is longer; old toolchains are the risk.
- **The contract's strength, not just its reach.** The ladder's L5 mutation work is the precise instrument: a
  surviving mutant marks behaviour the tests execute but do not check (cf. "pseudo-tested" methods).

## A 2 × 2 the data can fill

| | search has reached it | search has not reached it |
|---|---|---|
| **contract covers it** | well explored: lowest latent risk | checked happy paths |
| **contract does not cover it** | **where discoveries happen** | **dark matter**: latent defects wait here until search arrives |

## Candidate hypotheses (to register before any outcome statistic)

- **LV-H1 (where).** At equal size, latent (CVE / fuzz) fixes land disproportionately in code the contract does not
  cover at t.
- **LV-H2 (when: the search frontier).** Latent discoveries follow *new* search coverage. Files or functions whose
  fuzz coverage rose in the prior window carry more latent fixes in the next one than equally-sized,
  equally-covered files whose coverage did not move. Discovery is exploration.
- **LV-H3 (the contract's strength).** Among covered functions, those with surviving mutants carry more later latent
  fixes. This is the expensive one; it needs mutation runs.

**Recommended first step: nDPI.** Pull the OSS-Fuzz daily summaries (2019-11 → present), align them to the quarterly
snapshots and the XC latent labels, and build nDPI contract coverage at the same snapshots. That gives LV-H1 and LV-H2
on one repo. Then register and replicate on curl or openssl.
