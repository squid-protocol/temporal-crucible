# XC — do different kinds of fixes have different causes? — registered 2026-11-06, before any harvest or statistic

**Why.** The program's standing result is "history predicts, structure describes". The owner's reflection
(2026-11-06) proposes a reason. A "fix" is not one kind of event:

| class | what happened | where its cause lives |
|---|---|---|
| **extrinsic** | the code was right for an older world; the world changed (compiler, platform, dependency API, standard) | the environment |
| **latent** | the code was always wrong against its own contract; an input finally exercised it (CVEs) | the code × whoever searched it |
| **regression** | a recent change broke working logic | the change process |

Pooling them would dilute any class-specific cause. This battery separates them and asks whether each class answers to
its own predictor.

**What has been seen.**
- Change entropy, churn and prior fixes were tested against security fixes on all three repos (FWD, EA, RW-H2) and
  against pooled bug labels on curl (HV, B-H3). `import_count` was tested against pooled labels (centrality_bands).
  `amplified_cascading_flux` was seen against security fixes on all three repos (NM).
- **New here:**
  - the class split of the outcome, harvested by a new tool across all three repos;
  - the external-include predictor;
  - every class-specificity contrast.
- No class label below exists yet.

## Outcome classes (harvester `tools/xc_harvest.py`)

- **Population.** All non-merge commits reachable from the walk's `events_head` on the walk's branch (curl/openssl
  `master`, nDPI `dev`), from one year before the first snapshot onward.
- **Exclusions.**
  - Commits touching > 50 C files: mechanical sweeps, excluded from every class.
  - Commits touching no C file (`.c`/`.h`).
- **Class assignment.** Each commit gets the first class that matches, in this order:
  1. **latent**: the SHA is an on-master `security-fix` event in `events/<repo>.json`.
  2. **regression**: either
     - a revert (subject starts `Revert "`, or the body has `This reverts commit <sha>`); or
     - fix-like **and** (the message has `regress(ion|ed|es)` **or** references a SHA, ≥ 7 hex, that resolves to an
       ancestor committed ≤ 90 days earlier).
  3. **extrinsic**: the subject names the environment **and** an action.
     - Environment terms: compiler, platform, dependency or standard names. E.g. gcc, clang, msvc, mingw, cygwin,
       windows, win32, macos, darwin, freebsd, android, ios, solaris, aix, 32-/64-bit, endian, glibc, musl, c89/c99/c11,
       openssl/boringssl/libressl/wolfssl/mbedtls/gnutls, zlib, nghttp2, libssh, `newer`/`older` + version, API
       change, deprecat\*, toolchain, cross-compil\*. The exact regex is frozen in the tool.
     - Action: fix-like, or silence / suppress / avoid / work around / adapt / compat / port / make … build / compile /
       work.
  4. **other-fix**: fix-like and none of the above.

  "Fix-like" = `fix(es|ed)?|bug|broke(n)?|break(s|age)?|regress\w*|crash\w*|wrong|incorrect|segfault|leak|overflow|oops|restore`
  in subject or body.
- **Precision gate (binding, before any predictor statistic).**
  - The author hand-audits a seeded random sample (seed 2982) of 30 commits per (class, repo), or all if fewer, from
    subject, body and diffstat.
  - A (class, repo) with audited precision < 0.70 is **withheld**. Its rule may be amended once, recorded here as an
    amendment, and re-audited on a fresh sample before scoring.
  - The audit file is committed (`docs/xc_label_audit.md`).

## Unit, predictors, statistic

- **Unit.** The as-of quarterly snapshots and DBs of FWD/EA: curl 105 (`e246915aa`), nDPI 43 (`e246915aa`), openssl
  110 (`da852aa54`). Their churn/HCM gates passed in `fwd_curl.md`, `fwd_ndpi.md` and `ea_openssl.md`.
- **Candidates.** C files. Positive for class K = touched by a class-K commit dated (committer time) in (t, t + 180 d].
- **Predictors (read at t):**
  - `change_entropy`;
  - `raw_churn_freq`;
  - **prior same-class**: class-K commits ≤ t touching the file;
  - **prior other-class**: commits of the other classes, other-fix included, ≤ t touching the file;
  - **external includes**: distinct `raw_imports` entries matching no file path in the snapshot (by path suffix);
  - context only (seen): `amplified_cascading_flux` / `total_loc`.
- **Statistic.** EA's recall@20 (rank, ties smaller `total_loc` then path, whole files while cumulative LOC ≤ 20%).
  Baselines LOC-desc and LOC-asc. Per snapshot, lift(P, K) = recall@20(P, K) − max(recall@20(LOC-desc, K),
  recall@20(LOC-asc, K)). The baseline is the snapshot's stronger one, the conservative choice.
- **Scored snapshots** for K: ≥ 1 class-K positive. A (claim, repo) with < 20 scored snapshots is *not evaluable*.

## Claims

| id | theory prediction | supported iff (per repo) |
|---|---|---|
| **XC-H1** | regressions answer to the change process | mean lift(change_entropy, regression) > 0, one-sided snapshot-bootstrap lo > 0 |
| **XC-H2** | …specifically | mean over snapshots scored for both of [lift(change_entropy, regression) − lift(change_entropy, latent)] > 0, lo > 0 |
| **XC-H3** | extrinsic fixes answer to environment surface | mean lift(external includes, extrinsic) > 0, lo > 0 |
| **XC-H4** | …specifically | mean of [lift(ext, extrinsic) − lift(ext, regression)] > 0, lo > 0 |
| **XC-H5** | history is class-specific (regression) | mean of [recall@20(prior same-class) − recall@20(prior other-class)] on regression outcomes > 0, lo > 0 |
| **XC-H6** | history is class-specific (extrinsic) | same, on extrinsic outcomes |

- **Tests.** 5,000 snapshot-bootstrap rounds, seed 2982; α = 0.01 / 6 one-sided per (claim, repo).
- **Equivalence null.** The 90% CI lies inside [−0.02, +0.02]; otherwise *not supported (inconclusive)*.
- **Headline.** A claim holds if it is SUPPORTED on every evaluable repo. **The theory is supported** if at least one
  "own cause" claim (H1/H3) **and** its specificity claim (H2/H4) hold. **It is falsified for this program** if H1–H4
  all fail with equivalence nulls on every evaluable repo. Anything else is mixed.
- **Descriptive.**
  - Class counts and C-file-touch shares per repo.
  - The full predictor × class recall@20 matrix (LOC-desc, LOC-asc, entropy, churn, prior same, prior other, external
    includes, flux density) × (extrinsic, latent, regression, other-fix).
  - Regression-lag and latent-lurk distributions where an introducing commit is known.

## Priors

- XC-H1 **leaning supported**: change entropy beat LOC on pooled bug labels on curl.
- XC-H2 **uncertain**.
- XC-H3 / H4 **uncertain**: the extrinsic labels may be thin in C files.
- XC-H5 **leaning supported**: regressions cluster in recently-churned files.
- XC-H6 **uncertain**.
