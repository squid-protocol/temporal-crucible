# CMB — does the code-reading patch check generalise to a second vendored library, and beat a closest-version matcher on modified copies, judged by a blind auditor? — registered 2026-11-06, before any expat host history was read

**Why.** On vendored zlib, SEM-2 (new guard fragments, then the line rule) made 0 / 1,552 wrong calls on verbatim
truth, and beat the line check 19 / 20 on a held-out audit. Three limits remain:
1. one library;
2. no comparison with the approach real tools use, *closest-version matching*;
3. the instrument's designer did the audits.

CMB adds **expat**, a **closest-version baseline**, an **OSV-scanner** arm (subject to owner approval) and a **blind
auditor**.

## Libraries

**Scope change from the plan.** SQLite and libpng were dropped **before any data**. Neither offers a
metadata-verifiable mapping from CVE to fix commit: SQLite is vendored as a generated amalgamation and its commits
rarely name CVEs; only a handful of libpng commits name a CVE.

- **zlib:** VZ-T's 7 fixes, 12 hosts and 791 states, unchanged.
- **expat** (`libexpat/libexpat` @ the pool clone's head).
  - **Fixes** come from `expat/Changes`: each "Security fixes" item with ≥ 1 CVE and ≥ 1 `#PR`, in the release
    section it appears under.
  - The **fix commit** is the first-parent `Merge pull request #N` commit of each PR. The fix diff is
    merge^1 → merge, restricted to `expat/lib/*.c`.
  - Items whose PRs have no merge commit (pre-GitHub history) are excluded.
  - **Result:** 43 items, releases 2.1.1 … 2.10.0. The list is written by the scorer to the report.
  - **Release tags:** `R_2_x_y`, files under `expat/lib/`.
  - **Version macros:** `XML_MAJOR_VERSION`, `XML_MINOR_VERSION` and `XML_MICRO_VERSION` in `expat.h`.
- **expat hosts.** Path (the copy's directory) and history from blobless clones (`vzt_hist/`):

| host | path |
|---|---|
| python/cpython | `Modules/expat` |
| Kitware/CMake | `Utilities/cmexpat/lib` |
| Kitware/VTK | `ThirdParty/expat/vtkexpat/lib` |
| InsightSoftwareConsortium/ITK | `Modules/ThirdParty/Expat/src/expat` (the `lib` sub-folder if present) |
| pocoproject/poco | `XML/src`, files `xml*.cpp` matched to expat's `xml*.c` by stem: a renamed, C++-compiled copy |
| AOSP external/expat | `lib` (a vendored-copy repository) |

  A host whose path never existed is reported and dropped.

## Units, truth, methods (as VZ-T / SEM unless noted)

- **Units:** (host state, fix, file), for files the fix changes that exist in the state. States are first-parent
  commits touching the path, deduplicated by tree.
- **Verbatim truth:** whitespace-normalised equality with the file at some release tag. Patched iff that release ≥
  the fix's release.

**Methods.**

| method | verdict |
|---|---|
| **SEM-2** | new guard fragments (absent from the pre-fix function), else the line rule; may abstain |
| **CV, closest version** (reimplemented idea; no third-party code) | the release whose file has the highest Jaccard over normalised code lines (ties go to the later release); no verdict if that Jaccard is < 0.5; patched iff that release ≥ the fix release |
| **VER, version string** | from the state's version macros |
| **OSV, OSV-scanner** v2.6.0 | its vendored-C/C++ version determination per state directory, mapped to the fix release. **Runs only with the owner's approval**, since it downloads and executes a third-party binary and sends file hashes to the OSV API. Otherwise CMB-H3 is not evaluable |

## Blind audit (the truth for H2 and H3)

- **Sample:** per library, the non-verbatim units where SEM-2 and the comparator **both decide and disagree**. Up to
  30, seed 2985; all, if fewer.
- **Auditor:** a fresh agent with no access to this conversation, the methods or their verdicts. Per unit it gets
  the CVE item text, the upstream fix diff for that file, and the host file text.
- It answers patched / unpatched / unclear, with a one-line reason.
- Unclear units are excluded.
- Labels are hash-locked before they are compared with any method.

## Claims (α = 0.01/3, one-sided)

| id | claim | supported iff |
|---|---|---|
| **CMB-H1** | **SEM-2 generalises without new errors** | on expat's verbatim units, SEM-2's wrong calls ≤ 1%, Wilson 99% upper ≤ 2% (≥ 100 units) |
| **CMB-H2** | **SEM-2 beats closest-version on modified copies** | on the blind-audited SEM-2-vs-CV disagreements (both libraries pooled), SEM-2 is right more often: exact sign test over units, p < α (≥ 10 audited units) |
| **CMB-H3** | …**and beats OSV-scanner** | the same, with OSV as the comparator (owner approval required) |

**Descriptive.**
- Per library and method: verbatim accuracy, wrong-call rate and coverage (the share of units given a verdict).
- Cross-tabs between methods on modified copies.
- Exposure windows for expat.

**Disclosure.** Aggregates only in public files. If any host's *current head* is judged unpatched, the details are
private and for the owner.

## Priors

- **H1 likely.**
- **H2 uncertain.** CV is right whenever a copy is a light edit of a release. SEM-2 should win on backports and
  independent fixes, and lose on CV-correct cases where it decides wrongly; it has never decided wrongly on known
  truth so far.
- **H3:** pending approval.

**Pre-data path corrections (2026-11-06; presence checks only, no contents compared).**
- ITK's copy is `Modules/ThirdParty/Expat/src/itkexpat/lib`.
- AOSP's is `expat/lib`.
- Poco vendored expat first as C++ (`XML/src/xml*.cpp`, from 2006), later as `dependencies/expat/src/*.c`. Both paths
  are followed.
- **Expat fix mapping:** tree-sitter only (no engine scans of expat), with the ALL-CAPS-macro name filter.

**Owner decision (2026-11-06, before any CMB statistic):** skip the OSV-scanner arm for now. **CMB-H3 is not
evaluable** in this run. It can be run later as its own registered comparison if the binary is approved.

---

## Results, stage 1 (`prepare`, scorer `8e10603`; report `cmb_prepare.md`)

**Data.** 956 host states, 12,023 units. 37 of the 43 expat fixes change at least one function in a `lib/*.c` file.

| claim | result | verdict |
|---|---|---|
| **CMB-H1** SEM-2 no new errors on expat verbatim truth | **687 wrong** / 2,442 decided (Wilson 99% upper 23%) | **not supported** |

| library | method | wrong calls on verbatim truth | coverage |
|---|---|---:|---:|
| zlib | SEM-2 / line / closest-version / version | 0 / 0 / 0 / 1 | 74% / 73% / 62% / 100% |
| expat | **SEM-2 / line** / closest-version / version | **687 / 570** / 0 / 0 | 70% / 68% / 100% / 99% |

**zlib's clean record does not generalise.** On expat, both code-line checks are wrong on about a quarter of decided
verbatim units. Closest-version matching and version strings are perfect.

**Diagnosis (exploratory, `tools/exploratory/cmb_expat_error_breakdown.py`, after stage 1).**
- Nearly every error is the dangerous kind: an **old, unpatched copy called "patched"**. That is 566 of 570 for the
  line check and 683 of 687 for SEM-2.
- The errors concentrate in about 13–15 of the 37 fixes, mostly 2026 releases (2.8.x–2.10.0). For each of those, 63
  to 87 of its 88 verbatim units are wrong.
- **Likely mechanism:** these fixes are larger pull requests that **move and refactor code**, so many of their
  "added" lines already exist elsewhere in the file in older releases. The line rule's "≥ 50% of added lines present"
  then fires on unpatched code.
  - SEM-2 filters only its *guard fragments* for novelty. The underlying line rule never did.
  - zlib's surgical fixes hid this.
- **Repair (not part of this run; needs its own registration):** count only added lines that are absent from the
  whole pre-fix file. Then re-test on both libraries.

The blind audit for **CMB-H2** proceeds as registered.

**Audit packet fix (2026-11-06, before any audit label was compared with any method).**
- The first-round blind auditors reported that many host excerpts were **cut off before the changed code**. When
  tree-sitter could not see a function (preprocessor-split old zlib; zlib-ng's `PREFIX(name)` definitions), the
  excerpt fell back to the first 6,000 characters of the file.
- **Fix:** take each function from its definition line, including `PREFIX(name)`, to the next column-0 `}`.
- The packets were rebuilt. The sample is identical (seed 2985); packets still carry no method verdicts.
- **33 of 60 packets changed.** Their first-round labels are discarded, and **fresh** auditors re-label them.
- The 27 unchanged packets keep their first-round labels. Four of those are legitimately unclear, because the host
  version lacks the function the fix changed.

**Blind labels locked (2026-11-06, before comparison with any method).**
- 60 labels: 33 from the fresh re-audit, 27 from the first round (unchanged packets).
- File `vz_private/cmb_audit_labels.json`, sha256 `889cd94c3e17080e7cf570fabb4e3ed8308eb2398db89c7979044af1cf0b86c7`.
- **Recorded auditor judgement:** in 11 packets about CVE-2022-37434's *follow-up* fix (a NULL-pointer dereference),
  the host never had the dereference, but it lacks the main `len < extra_max` bound.
  - All three re-auditors independently labelled these **unpatched**, for the CVE as a whole.
  - The labels are used as delivered.
  - A sensitivity check with those 11 flipped to patched is reported descriptively.
