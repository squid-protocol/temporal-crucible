# SRCH-H1..H3 — does who finds a CVE set how old the code it fixes is? — registered 2026-11-06, before any statistic on the new splits

**Why.** One pattern has recurred four times:
- LV (search frontier);
- INP (input surface);
- KF (curl does not show the `goto` link);
- AGE: human-found CVEs (curl, openssl) change code 1.6–2.8× older than generic fixes; fuzzer-found ones (nDPI,
  harfbuzz) 0.3–0.8× younger.

The reading: **a latent defect's age at discovery is set by the searcher.** Continuous fuzzing catches bugs soon after
they are written. Human auditors find old bugs in frozen code. AGE's split was exploratory, seen on the data that
suggested it. This entry tests it where it has not been seen.

**What has been looked at.**
- AGE's per-repo medians (curl, nDPI, openssl, harfbuzz).
- Credit counts: curl credits fuzzing on 3 of 239 advisories; openssl's CVE records credit fuzzing on 13 of its 252
  fix events.
- **Never computed:** any age on libxml2, file or libexif; any openssl split by credit; any ordinary-commit baseline.

## Measure

AGE's, verbatim (`tools/age_eval.py`, `fix_age`): the median blame age of the parent-side lines a commit deletes or
modifies, in C/C++ files.

**Baseline: ordinary commits.**
- A seeded (2982) random sample of up to 300 non-merge commits per repo.
- Each touches 1–50 C/C++ files and is reachable from the walk head (default branch head for the new repos).
- CVE-fix commits are excluded.
- Ratio = median age (CVE fixes) / median age (ordinary commits), within repo.

## Claims

| id | claim | data | supported iff |
|---|---|---|---|
| **SRCH-H1** | **fuzzer-found CVE fixes change young code** (unseen repos) | OSS-Fuzz security fixes of **libxml2, file, libexif** (`events/<repo>.json`) vs each repo's ordinary commits. libtiff and libpng are excluded: < 10 events | pooled mean log₁₀ ratio < 0, bootstrap upper bound < 0 |
| **SRCH-H2** | **within one repo, the fuzzer-found CVEs are younger than the human-found ones** | openssl security-fix events. Fuzzer-credited = the CVE record's credits match `oss-?fuzz\|libfuzzer\|fuzz` (13 events); human = the rest | median log₁₀ age (fuzzer) − (human) < 0, bootstrap upper bound < 0 |
| **SRCH-H3** | **the regimes differ**: CVE / ordinary age ratio is lower where fuzzers find the bugs | fuzzer regime: nDPI, harfbuzz, libxml2, file, libexif. Human regime: curl, and openssl's human-credited CVEs | mean log ratio (fuzzer repos) − mean (human repos) < 0, bootstrap upper bound < 0 |

**Tests and power.**
- Bootstrap: fixes and baseline commits resampled within repo, 5,000 rounds, seed 2982. α = 0.01 / 3 one-sided.
- A repo enters a claim with ≥ 10 measured CVE fixes.
- **Honest power note:** SRCH-H2 has only 13 fuzzer events. A miss there is weak evidence either way. H3 reuses seen
  repos (curl, openssl, nDPI, harfbuzz) for both regimes, alongside the three unseen ones.

**Descriptive.**
- Per-repo ratios.
- curl's 3 fuzz-credited advisories, listed.

## Priors

- H1 **leaning supported** (nDPI and harfbuzz both pointed this way).
- H2 **uncertain** (small n).
- H3 **leaning supported**.
