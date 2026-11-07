# VZ-T — vendored zlib through time: does the code-line patch check detect *unpatched* copies, and where does reading the code beat reading the version? — registered 2026-11-06, before any host history was read

**Why.**
- VZ showed the code-line patch check agrees with each host's declared version, once rsync's documented backports
  are counted: 137/137.
- But every current copy was patched, so **detection of unpatched code was never tested**.
- Each host's history contains its earlier, pre-fix copies. VZ-T walks those histories.
- **The product question:** where does a code check disagree with a version check, and which is right? Version
  scanners already catch plain version bumps. The value of reading code lies in the disagreements: backports,
  hand-patched or partial copies, and missing or stale version strings.

**Disclosure rule (as VZ).** Public files give aggregates only. Per-host, per-CVE timelines go to
`temporal-crucible-pool/vz_private/`. These are past states of public projects, but the rule is kept for
consistency.

## Data

**Hosts and paths.** VZ's 12 hosts and paths, at the same heads. MySQL's path is the `zlib-*` folder that holds the
code in each state.

**States.**
- Every first-parent commit of the host's default branch, up to the VZ head, that touches the path.
- Consecutive identical states (same tree id for the path) are merged.
- Each state is dated by commit time.
- Histories come from blobless clones (`vzt_hist/`); libgit2 from the existing full clone.

**CVE files and fix lines.** VZ's 7 fix commits; the same code-only R/A lines (comment lines excluded) per changed
file: `inflate.c`, `deflate.c`, `trees.c`, `inftrees.c`, `inffast.c`, `crc32.c`.

**Code check (file level, no fingerprint).**
- Within the host state's file of the same base name:
  - **patched** if ≥ 50% of the fix's A lines are present;
  - **unpatched** if ≥ 50% of its R lines are present and < 50% of A;
  - otherwise **undetermined**.
- In a history, the file is known by name. Locating copies was VZ-H1's job; this isolates the patch check.

**Independent truth: verbatim copies.**
- A host file is **verbatim** if, after whitespace normalisation, it equals that file in some upstream zlib release
  tag (`v1.2.3` … `v1.3.1`).
- Truth: **patched** iff that release is ≥ the fix's release (1.2.9, 1.2.12, 1.2.13).

**Version verdict.**
- From the state's `ZLIB_VERSION` (`zlib.h` or `zlib*.h.in`): patched iff ≥ the fix release.
- Missing version → **no verdict**.

**Units.** (host, state, CVE fix) where the file exists in the state.

## Claims (α = 0.01/2; Wilson 99% bounds)

| id | claim | supported iff |
|---|---|---|
| **VZT-H1** | the code check **detects unpatched copies** (sensitivity) | among verbatim-unpatched units, share the check calls *unpatched* ≥ 90%, Wilson lo ≥ 75% (≥ 20 units; else not evaluable) |
| **VZT-H2** | …without false alarms (specificity) | among verbatim-patched units, share the check calls *patched* ≥ 90%, Wilson lo ≥ 75% (≥ 20 units) |

Units counted as *undetermined* stay in the denominators: they count against the check.

**Descriptive (the product question).**
- On **non-verbatim** units: a cross-tabulation of code verdict × version verdict.
- Every disagreement is listed privately, and a seeded sample of ≤ 20 is audited by reading the host diff. Labels:
  backport / hand-patch / version string stale or missing / check error.
- **Exposure windows:** per host and CVE, the time from the upstream fix release date to the first state the code
  check calls patched. Medians are public; per-host values are private.

## Priors

- **H1 and H2 likely:** fix lines are specific.
- **Disagreements:** expected, and few. rsync's backports, plus copies whose headers lag the code.

---

## Results — 2026-11-06 (scorer `8d497b0` committed before running; report `vzt.md`; per-host detail private)

**Data.** 791 distinct vendored-zlib states across 12 hosts; 6,155 (state × CVE file) units. 1,552 of them are
verbatim copies of an upstream release.

| claim | result | verdict |
|---|---|---|
| **VZT-H1** sensitivity on verbatim-unpatched | 919 / 1,127 = 81.5% (lo 78.4%) | **not supported** (bar 90%) |
| **VZT-H2** specificity on verbatim-patched | 310 / 425 = 72.9% (lo 67.1%) | **not supported** |

**The registered verdicts hide the key fact: on verbatim copies the check was never wrong.**

| verbatim truth | called right | called wrong | undetermined |
|---|---:|---:|---:|
| unpatched (1,127) | 919 | **0** | 208 |
| patched (425) | 310 | **0** | 115 |

- Every miss is an **abstention**, which the registration counted as a failure.
- Abstentions cluster in releases far from the fix:
  - zlib 1.0.x and 1.1.x states for the 2016 and 2022 fixes, where neither the old nor the new lines exist yet;
  - 1.3 states for CVE-2016-9843, where the code has since moved on.
- **Reading:** when the check decides, it is right (1,229 / 1,229). It cannot decide on code that differs from both
  the pre-fix and post-fix text.

**Disagreements with the version string on non-verbatim copies.**
- 779 in all: zlib-ng 646, Chromium 76, rsync 51, OpenJDK 4, Qt 2.
- **Audit of the registered seeded sample (20), by reading code and commits:**

| label | n | what |
|---|---:|---|
| **backport, check right** | 5 | rsync (documented in `NEWS.md`) and Chromium carry fixes their version string predates |
| **stale or compatibility version label, check right** | 8 | zlib-ng's `ZLIB_VERSION` is a compatibility string (e.g. `1.2.11.zlib-ng`) while its code has the CVE-2018-25032 fix |
| **check error: fixed differently** | **7** | zlib-ng fixed CVE-2022-37434 with its own guard. It keeps zlib's removed line and wraps the copy in `if (len < state->head->extra_max)`, which is equivalent but textually different, so the check wrongly says "unpatched" |

**What this means.**
1. **Verbatim copies are easy, and already solved elsewhere.** File hashing against releases (OSV-scanner-style)
   handles them; our check matches that, perfectly when it decides.
2. **Backports and stale labels are where the code beats the version:** 13 / 20 of the audited disagreements. This
   is the niche, and it holds.
3. **Independent fixes defeat line matching:** 7 / 20, all in a rewritten fork. Recognising "fixed differently"
   needs a *semantic* check, for example whether the fix's guard condition (`len < extra_max`) is present in any form.
   The structural layers are a natural basis for that. It is the next instrument to build and register.

**Exposure windows (descriptive).** Days from the upstream release carrying each fix to the first state the check
calls patched, median over hosts:

| CVE | median | range |
|---|---:|---|
| CVE-2016-9840/41 | 266 | 5 → 1,979 |
| CVE-2016-9843 | 220 | 5 → 804 |
| CVE-2018-25032 | 49 | −1,319 → 458 |
| CVE-2022-37434 | 70 | −67 → 455 |

- Negative values: hosts that track zlib's development line had the fix before it was released. The CVE-2018-25032
  fix sat on zlib's `develop` branch from 2018 until the 1.2.12 release in 2022.
- Windows are bounded below by the check's abstentions, so they are approximate.
