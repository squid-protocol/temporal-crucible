# temporal-crucible: what we know so far — synthesis, 2026-11-06

**What this program does.** temporal-crucible tests what the GitGalaxy engine (structural and keyword scanner) is
good for, using code history: quarterly and weekly engine scans of real repositories, with outcomes taken from later
commits.

Every claim below was **registered before its data was computed**: hypotheses committed, then the scorer committed,
then the run. Exploratory findings are labelled as such. Details live in each study's `docs/*_hypotheses.md` and in
the register (`HYPOTHESES.md`).

**Evidence levels used here.**
- **Replicated:** supported on repositories chosen after the original result.
- **Supported:** registered and passed, not yet replicated.
- **Mixed:** passed in some repos or arms.
- **Not supported:** failed the registered test.
- **Ruled out:** failed and replicated, or refuted.

---

## 1. What the engine is good for (established)

| finding | evidence | level | study |
|---|---|---|---|
| **Library coupling marks where library work lands.** Files that call a library's API receive the work that names it | recall@20 +0.40 over size, +0.46 over other libraries, +0.22 over file names (21 units, 4 repos); **replicated** on PostgreSQL + libgit2 (+0.44 / +0.49 / +0.18, 14 units) | **replicated** | LIB, LIB-R |
| …and the **engine's own call graph** carries it | `calls_out_to` coupling +0.34 over size, but 0.06 behind the regex (misses `#include` and COM-method coupling) | supported (non-inferiority ✗) | LIB-E |
| **Platform conditionals mark where extrinsic fixes land** | `#ifdef` density beats size on unseen harfbuzz and libarchive (+0.17 / +0.12); the only metric of 225 screened that passed holdout | **replicated** | ENV, SC |
| **Past security fixes predict future ones (recidivism)** | median recall 0.444 vs 0.000; 77–27 against exposure. This is the baseline any structural signal must beat | supported, decisive | RW-H2 |
| **`goto` marks security-risk code** | security-fix rate ratio about 2 at equal size; 2.8 on 5 unseen repos. Not specific to lifetime faults | **replicated** (general risk only) | DYN, KF, KF-R |
| **Projects have stable structural fingerprints** | keyword mix identifies a project across eras 95.9%; the `sfs` fingerprint 99.0% | supported | SIG, SFS |
| **Codebase natural history** | infant mortality (young functions die 2.9× faster), structural freeze with age, archetypes persist through edits (88%), hubs stable and growing sub-linearly; replicated in direction on GitGalaxy's own Python history | supported (5 / 6) | NH, GG |
| **Regimes leave a mark** | Gemini-era vs Claude-era GitGalaxy code: AUC 0.877 against within-era placebos of about 0.7. The era bundles model, tooling and workflow, not the model alone | supported (one repo) | GG |
| **Layered fingerprint finds copies of code** | call set + control-flow skeleton + profile: fork copies ranked first 46% → **80%**; C → C++ BoringSSL 29% → **94%**; vendored zlib (12 hosts) **91%** vs 68%, 98% on same-name copies, without names | supported, out of sample | LAY, VZ |
| **Code-reading patch check works for "surgical-fix" libraries** | zlib: 0 / 1,229 wrong on verbatim truth; beats version strings on backports and stale labels; beats closest-version on blind-audited modified copies **30 / 30, 19 / 20, 30 / 30** | supported (zlib only) | VZ-T, SEM-2, CMB, SEM-3 |

**In one line:** GitGalaxy is good at **what code is, where it came from, how it lives, and where the outside world
touches it**: coupling, identity, copies, provenance and natural history.

## 2. What it is not good for (ruled out or not supported)

| claim | result | study |
|---|---|---|
| Regression prediction beyond churn | Engine change features **lower** churn's recall@20 (41.3% → 38.7% forward; 36.7% → 33.8% on held-out repos). "Shape change" ≈ edit size | CHG-2 (CHG's 2.9× was mostly churn) |
| Young code is deficient | Young code gets more fixes of every kind, but not more regressions once matched; a *lower* regression share | CHG H4/H5 |
| Centrality (PageRank, popularity) finds bugs | Fails on unseen repos | CEN |
| Input-facing code marks CVEs | Loses to size on 3 of 4 repos | INP |
| Fuzz-frontier marks latent bugs | Fails on curl (−0.195) | LV, LV-R |
| Who finds a CVE sets the age of the code it fixes | Refuted: CVE fixes change older-than-typical code (×2.1–3.7) whoever finds them | AGE, SRCH |
| Extrinsic fixes burst after compiler releases | Bursts are real but not timed to releases | BURST |
| Co-change omission predicts regressions | Null; commit size is the best predictor | REG |
| Archetypes or atypicality find fixes | Stable, but no fix-finding beyond size | ARCH, ARCH-Z |
| The autonomous fleet writes differently from interactive Claude | AUC 0.64, below within-group drift (0.70) | FLT |
| The coarse fingerprint finds copies | 12.5% of name-found fork copies; none in C++ BoringSSL | UT |
| Code-reading patch checks on **refactoring-fix** libraries (expat) | Line / SEM-2 call about 25% of old verbatim copies "patched"; SEM-3 cuts that to 4.9% but still fails; blind audit 1 / 29 vs closest-version 28 / 29 | CMB, SEM-3 |

## 3. Corrections made along the way (keep these in mind when quoting earlier summaries)

1. **LIB's outcome is library-named work, not security fixes.** Earlier chat summaries said "where security fixes
   land". Recorded in `librep_hypotheses.md`.
2. **The libarchive "engine bug"** was a duplicate-SHA scratch-directory race in the rescan tooling (fixed, #62), not
   the engine.
3. **SRCH refuted** the "searcher sets CVE age" explanation suggested by AGE's exploratory split.
4. **FLT reversed GG's exploratory note:** interactive sessions, not the fleet, wrote most of `gitgalaxy/tools/`.
5. **CHG's "3% of functions carry 21% of regressions"** is mostly churn. Any edit covers 31%. GitGalaxy's own
   increment was small (1.42×, lo 1.02) and vanished against a churn baseline (CHG-2).
6. **VZ's 13 "renamed" copies:** 11 were an artefact (`_tr_tally` became a macro). Vendored zlib is essentially
   never renamed.
7. **SEM-1 was unusable** (227 false "patched", from non-new guard fragments). SEM-2 fixed it on zlib.
8. **Gate and instrument amendments**, each documented before the affected statistic:
   - CHG's name-join gate (A1);
   - VZ's engine-span fallback for preprocessor-split C;
   - CMB's audit-packet excerpt fix (33 packets re-audited by fresh agents).

## 4. Product-relevant engine findings

- **The default scan skips vendored, version-named directories.** MySQL's `extra/zlib/zlib-1.3.2/` produced 0
  functions. Supply-chain use needs a "include vendored code" option.
- **`calls_out_to` misses COM-style method calls** through interface pointers (harfbuzz DirectWrite) and does not
  record per-file `#include` dependencies. Both cost LIB-E its non-inferiority.
- **Preprocessor-split C** (old zlib `inflate.c`) defeats tree-sitter. The engine still extracts the functions, so
  engine spans make a useful fallback.

## 5. What it means for positioning

- **Strongest, most defensible:**
  - library and platform **coupling surfaces** (where external change lands; replicated);
  - **identity and copy-finding** with a layered fingerprint, across forks, C → C++ rewrites and vendoring;
  - **codebase biography**: natural history and regime shifts.
- **Not a bug or regression predictor.** Churn and recidivism already do that, and the engine adds nothing beyond
  them.
- **Supply chain ("trust the code, not the label") is real but narrow so far.**
  - It works for libraries whose security fixes are surgical (zlib). There it beats version strings and
    closest-version matching on modified copies.
  - It fails for libraries whose fixes are refactors (expat), where closest-version matching should be used.
  - **Not yet tested:** a real tool head-to-head (OSV-scanner, skipped by owner decision), more libraries, and
    renamed copies at scale.
- **Port traceability (COBOL → Java)** is out of scope for fingerprints: a runtime-based port is not 1:1. The
  translator should emit its own provenance (owner note).

## 6. Open questions and next steps (proposed)

1. **"Fingerprint finds, model judges"** for patch status.
   - Blind auditor agents judged expat-style refactored fixes reliably where text rules failed.
   - Validate on about 4,800 verbatim units with known truth, then on held-out modified copies.
2. **Engine coupling 2.0:** add `#include` dependencies and interface-method calls, then re-test LIB-E
   non-inferiority.
3. **Renamed-copy benchmark** large enough to register (forks and rewrites, not vendoring).
4. **OSV-scanner head-to-head**, if the binary is approved.
5. **Replications still owed:**
   - RW (recidivism) and SIG / SFS identity on unseen repos;
   - `amplified_cascading_flux` (AMP-H1);
   - LAY on a second fork family.

## Where things are

- Study PRs today:
  - #75 GG, #76 FLT, #77 CHG, #78 CHG-2: merged;
  - #79 UT, #80 LIB-R / LIB-E / LAY, #81 VZ / VZ-T / SEM / CMB / SEM-3: open, merge in that order.
- Private material (never in this public repo) is under `temporal-crucible-pool/ut_private/` and
  `temporal-crucible-pool/vz_private/`:
  - audit candidates;
  - per-host CVE timelines;
  - hash-locked audit labels.
