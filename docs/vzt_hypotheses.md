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
