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

---

## Results — 2026-11-06 (scorer `68c01aa` committed before running; report `srch.md`)

2,394 commits blamed (CVE fixes plus up to 300 ordinary commits per repo).

| repo | ordinary commits, median age | CVE fixes: fuzzer-found | CVE fixes: human-found |
|---|---:|---|---|
| curl | 327 d | 2,755 d (3), ×8.4 | 691 d (151), ×2.1 |
| openssl | 242 d | 1,245 d (7), ×5.1 | 892 d (175), ×3.7 |
| nDPI | 176 d | 111 d (98), **×0.63** | — |
| harfbuzz | 24 d | 21 d (70), ×0.88 | — |
| **libxml2** (unseen) | 524 d | 1,104 d (38), **×2.1** | — |
| **file** (unseen) | 262 d | 874 d (24), **×3.3** | — |
| libexif (unseen) | 353 d | 61 d (6), ×0.17 (n < 10, not used) | — |

| claim | effect | upper bound | verdict |
|---|---:|---:|---|
| **SRCH-H1** fuzzer-found CVE fixes younger than ordinary commits (libxml2, file) | **+0.423 (×2.65 older)** | +0.838 | **not supported**: the opposite direction |
| **SRCH-H2** openssl fuzzer- vs human-credited | — | — | **not evaluable**: only 7 of the 13 fuzzer-credited fixes have measurable changed lines (< 10) |
| **SRCH-H3** fuzzer-regime ratio lower than human-regime | −0.298 (×0.50) | +0.135 | **not supported** |

**Headline → the searcher explanation of CVE age is refuted.**
- On unseen OSS-Fuzz repos, fuzzer-found CVE fixes change code **2–3× older** than ordinary commits, as human-found
  CVEs do.
- openssl's and curl's fuzzer-credited CVEs are older still (×5.1, ×8.4; small n).
- AGE's exploratory split was not about the searcher.

**What survives (descriptive, against the ordinary-commit baseline).**
- **CVE fixes mostly change older-than-typical code:** ×2.1–3.7 in curl, openssl, libxml2 and file, whoever found them.
  That is AGE-H2's original prediction ("latent defects live in old code"), visible here against a cleaner baseline.
- **nDPI (×0.63) and harfbuzz (×0.88) are the exceptions.** They are the two repos whose CVEs track the age of
  ordinary work rather than exceeding it. In harfbuzz, ordinary code changes are themselves extremely young (24 d
  median).
- So the exceptions look like **project-specific** churn regimes (fast-turning code bases), not a fuzzer effect.

**Correcting the record.** The "searcher split" called the program's most consistent pattern after AGE is **not
supported as an explanation of age**. The earlier searcher observations concern *where* fuzzer-found CVEs land
relative to search coverage and input code (LV, INP), and stay as they were: directional, unregistered as an age
claim. A registered test of "CVE fixes change older code than ordinary commits", on unseen repos with a pre-specified
exception rule, is the natural follow-up.
