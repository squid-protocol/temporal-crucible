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

## Amendment 1 — 2026-11-06, after the round-1 label audit and before any predictor statistic

- **Round 1** (`docs/xc_label_audit.md`):
  - regression passed: curl 0.87, nDPI 0.77, openssl 0.73;
  - latent passed: curl 1.00, nDPI 0.70, openssl 0.90;
  - **extrinsic failed on all three repos**: curl 0.33, nDPI 0.40, openssl 0.30.
- **Why extrinsic failed.** Generic "fix compiler warning" says nothing about the environment changing. Bare library
  names collide with the repo's own modules: curl's TLS backends, openssl's own `openssl` app.
- **The amended rule** (`tools/xc_harvest.py`, `EXT_ENV` v2). The environment must be named explicitly as one of:
  - a platform, OS or arch;
  - a named compiler (with or without version);
  - a C standard;
  - a libc;
  - toolchain / LTO / cross-compiling;
  - a dependency **with** a version or a newer/older/API qualifier.

  Generic `compiler`, `warning(s)`, `-W…`, `linker`, `deprecat*`, `autoconf`/`cmake` and bare dependency names are
  dropped.
- Everything else is unchanged, including the class order. Only the extrinsic rule changed; latent and regression
  labels are identical.
- **Re-audit:** a fresh sample (seed 2983, excluding round-1 commits) of 30 extrinsic commits per repo, same ≥ 0.70 gate.
  Under the registration this is the one amendment, so a failure now withholds extrinsic on that repo (XC-H3, H4 and H6
  become *not evaluable* there).

---

## Results — 2026-11-06 (labels `c52d566`, scorer `tools/xc_eval.py` committed before scoring)

Reports: `xc_curl.md`, `xc_ndpi.md`, `xc_openssl.md`. Lift = recall@20 minus the snapshot's stronger LOC ordering.

| claim | curl | nDPI | openssl | holds? |
|---|---|---|---|---|
| **H1** change entropy → regressions | −0.032 ✗ | −0.024 ✗ | **+0.090 ✓** | no (1/3) |
| **H2** …more than → CVEs | −0.054 ✗ | −0.016 ✗ | **+0.115 ✓** | no (1/3) |
| **H3** external includes → extrinsic | −0.104 ✗ | +0.034 ✗ | −0.064 ✗ | no |
| **H4** …more than → regressions | +0.015 ✗ | +0.119 ✗ (lo −0.052) | −0.036 ✗ | no |
| **H5** prior regressions → regressions (vs prior other fixes) | −0.021 ✗ | −0.088 ✗ | **−0.113**, CI [−0.170, −0.062] ✗ | no; the **opposite** is true on openssl |
| **H6** prior extrinsic → extrinsic (vs prior other fixes) | **+0.094 ✓** | −0.068 ✗ (29 snapshots, 50 events) | **+0.194 ✓** | no (2/3) |

**Headline rule → MIXED.**
- Neither an own-cause claim nor its specificity claim holds on every repo.
- The theory is not falsified either: no H1–H4 cell is an equivalence null, and several point the predicted way.

### What the class split shows (descriptive, from the registered matrix)

1. **The classes have different histories, even though structure predicts none of them.** Class-specific recidivism
   (prior same-class count, lift over the stronger LOC baseline):

   | class | curl | nDPI | openssl |
   |---|---:|---:|---:|
   | latent (CVEs) | **+0.041** | **+0.042** | **+0.099** |
   | extrinsic | −0.094 | −0.117 | **+0.056** |
   | regression | −0.060 | −0.058 | −0.054 |
   | other-fix | −0.218 | −0.187 | −0.050 |

   - **CVEs recur in place on all three repos**: the RW-H2/EA result, now seen as specifically a property of latent
     defects.
   - **Regressions never recur in place.** They follow general fix activity: prior *other* fixes beat prior regressions
     on every repo (H5 reversed). A regression is a property of where work is happening, not of a place.
   - **Extrinsic fixes recur against other history** on curl and openssl (H6). Files that needed a
     platform/compiler/dependency adaptation keep needing them: a stable "membrane" that faces the environment.

2. **The membrane is real, but the structural proxy for it failed.** External include count does not find it (H3 ✗
   everywhere). Extrinsic fixes skew to small files: LOC-asc reaches 0.279 / 0.251 recall on curl / openssl, against
   0.098 / 0.144 for LOC-desc. That fits platform shims and setup headers. History finds the membrane, the include
   count does not.

3. **Regressions answer to the change process on openssl only.** There change entropy and churn beat size for
   regressions (+0.090 / +0.103) but not for CVEs (−0.009 / −0.031), exactly the predicted specificity. curl and nDPI
   show no regression lift. On curl the lift is no larger for regressions than for CVEs.

4. **Generic "other" fixes are the size-free residue.** Nothing beats LOC-asc on them anywhere (all lifts −0.05 to
   −0.22). They are spread thinly over many small files.

### Reading it against the intrinsic/extrinsic theory

- **What survives.** Fixes are not one phenomenon. Latent defects, environment adaptations and regressions each have a
  *different history signature*:
  - CVEs recur in place;
  - extrinsic fixes recur on an environment-facing membrane;
  - regressions recur wherever work is happening, never in place.
- **What fails, again.** Reading any of these causes off a static snapshot. Change entropy works for regressions on
  one repo. External includes do not find the membrane.
- **The one-line update.** *Fix classes have distinct histories, but no snapshot metric sees the class.*

### Caveats

- Labels are rule-based: audited precision is 0.70–1.00 and recall is unmeasured.
- nDPI's extrinsic class is small (50 commits; 29 snapshots scored).
- H6 compares against all other fix history, which is mostly the large other-fix class.
- The class-specific recidivism table is descriptive. It is the lead to register next, e.g. "a file's
  class-conditioned fix history beats its pooled history", on an unseen repo.

## Exploratory follow-up — a static environment-coupling measure (2026-11-06, NOT registered)

Prompted by the top extrinsic files (`config-win32.h`, `curl_setup.h`, `e_os.h`, `ppccap.c`): count, per C file and
snapshot, the `#if`/`#ifdef`/`#ifndef`/`#elif` lines testing platform/compiler/arch macros (`P`), `HAVE_*` (`H`), or
version comparisons (`V`). Tool: `tools/exploratory/xc_envcond.py`. Reports: `xc_envcond_*_exploratory.md`.

Platform/compiler/arch conditionals per line (`P per line`), lift over the stronger LOC order:

| class | curl | nDPI | openssl |
|---|---:|---:|---:|
| **extrinsic** | **+0.119** | **+0.048** | **+0.133** |
| latent | −0.147 | −0.095 | −0.259 |
| regression | −0.115 | −0.107 | −0.038 |
| other-fix | −0.098 | −0.115 | −0.089 |

- This is **the first static measure in the program that both beats size and is class-specific**: it finds extrinsic
  fixes and is worse than size on every other class.
- `HAVE_*` and version checks do not show the pattern.
- **Exploratory only.** The labels are seen and the measure was chosen after looking at the top files.
- The registration owed is **ENV-H1** on an unseen repo. It needs only git, no engine scan, so it is cheap. The claim:
  `P per line` beats both LOC orders on extrinsic fixes **and** its extrinsic lift exceeds its lift on latent and
  regression fixes. A gitgalaxy engine column for platform-conditional density is the product follow-up if it holds.

## Exploratory follow-up 2 — history dynamics by class, five repos (2026-11-06, NOT registered)

Tool `tools/exploratory/xc_history_dynamics.py` (git only; size = line count). Reports:
`xc_history_dynamics_{curl,ndpi,openssl,harfbuzz,libarchive}_exploratory.md`. Labels are seen, so nothing here is a
verdict.

**1. Recidivism is class-dependent.** Lift over the stronger size order:

| outcome | own-class history | pooled fix history | reading |
|---|---|---|---|
| **latent** (curl / nDPI / openssl) | **+0.060 / +0.294 / +0.106** | −0.010 / +0.251 / +0.084 | CVE history beats size 3/3, and beats pooled history 3/3 |
| **extrinsic** (curl / nDPI / openssl / harfbuzz / libarchive) | −0.050 / **+0.097 / +0.063 / +0.123** / −0.041 (last 365 d: −0.009 / … / +0.040) | −0.159 / +0.041 / −0.093 / −0.039 / −0.033 | own history beats pooled 5/5; beats size 3/5 (all-time) |
| **regression** | −0.053 / +0.144 / −0.047 / −0.046 / (libarchive labels withheld) | −0.031 / +0.138 / +0.066 / −0.062 | no own-class recidivism; on curl, nDPI and openssl pooled history matches or beats it |
| **other-fix** | all −0.06 … −0.21 | all negative | nothing beats small-files-first |

**2. The extrinsic surface evolves in bursts on a persistent core.**
- **Bursty everywhere.** Dispersion of the monthly extrinsic share vs binomial: curl 2.22, nDPI 1.39, openssl 2.15,
  harfbuzz 1.60, **libarchive 4.88** (1 = steady).
- **The burst months match recognisable outside events:**
  - new platforms: openssl RISC-V 2022-09, POWER9 and Haiku 2016-04; harfbuzz Windows CE 2014-08; nDPI OpenWRT and
    FreeBSD 2023-10;
  - new toolchains: clang 3.8 warnings; Cygwin 1.7 (2009);
  - new warning regimes: GCC `-W` flags on FreeBSD-current 2012-02; clang-tidy adoption 2026-02. Some "environment"
    is therefore the project's own choice of tooling.
- **The rate changes a lot over decades.** Extrinsic share of fixes:
  - curl: 15–23% in 2003–05 → ~5% in the 2010s → 8–10% again in 2024–26;
  - openssl: 12–19% before 2014 → 3–9% after;
  - libarchive: 20–38%, because portability is its product.
- **A persistent core.** Of each year's extrinsic-touched files, typically 50–80% were already extrinsic files in
  earlier years (curl 50–82%, libarchive 60–100%). The rest is new spread.

**Next registration owed (BURST-H1).** The extrinsic share rises after dated external shocks: GCC/Clang major
releases and major-dependency releases. Release calendars come from upstream sources, frozen before the join.
