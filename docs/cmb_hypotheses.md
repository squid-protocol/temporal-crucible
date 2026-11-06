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
