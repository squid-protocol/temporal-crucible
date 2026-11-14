# A codebase built for research — architecture specification (for SA3 only)

**Status: Revision 2, 2026-11-14, after one independent design review. Nothing is built.** Owner-approved as a
thing to draft. Route: specification → design reviews → build by a different model, in steps → code review →
the control repository run through it.

**What Revision 2 changed.** The first draft was reviewed by an independent session
(`docs/process/reviews/research_codebase_review_claude.md`: 5 blockers, 9 major, 6 minor; verdict "ready after
changes"). Its three heaviest findings were reproduced before anything here was changed (section 12). The
result is a **smaller thing built sooner**:

- **Step one is now a harness**, not a rewrite: the *existing* SA3 code run on control repositories with every
  path redirected. The first draft's "new code equals old code" test could not be run safely without it.
- **Existing rule code is moved, not rewritten.** The first draft would have changed SA3's numbers in six ways
  it did not list (section 6).
- **The general machinery is deferred** until a second study needs it: the configuration language, plug-ins,
  the generated rule-to-code table, rename following, the change effect.
- **Blinding is its own project**, built and tested on the control repository (`blinding_spec.md`, also
  revised today). SA3 is not a blinded study and gains nothing from it.
- Table design, invariants, storage, provenance and the lint are corrected where the review found them wrong.

It builds on `STUDY_SCAFFOLD.md`, `blinding_spec.md` and `control_repo_spec.md` and does not repeat them.

## 1. What is wrong today, measured

Read-only inventory of `tools/`, 2026-11-14, counts as corrected by the review. No study data was opened.

| what a database gives | what the code does today |
|---|---|
| One definition of each thing | The file-universe rule is written **5** ways that do not agree. The snapshot cut is recomputed in **6** places over different commit sets. The tree-wide rule is written **3** times with three denominators. SA3's keyword outcome and its tainted-merge test use two different keyword rules. |
| A schema with constraints | "Positives are ranked" is one `assert`. Nothing checks the reverse, that every ranked file can be positive. The universe is never stored: three tools recompute it. |
| Provenance | The seal lists 9 files by hand. It omits every data input and **13** code files that define rules, among them the universe rule. The result records no hash of any scan, label or history file. |
| Reproducibility | One random stream is shared across repos, so a result depends on the order of repos in a file; the placebo restarts the same stream for every repo. |
| Stages with inputs and outputs | Building outcomes deletes and rebuilds one of its own inputs. SA3's snapshot is whatever a MOD-1 tool last wrote to a JSON file. The file that decides which repos are scored is written by no tool. |
| Configuration | **56** of **225** tool files hold a hard-coded absolute path; the study directory is assigned in 14. Per-repo exceptions are lists inside code. |
| Access control | None. |
| Migrations | Four amendments on an edited document; the scorer disagreed with the text in nine places. The control repository found one more today (defect log 54). |
| Tests | None for the outcome builder or the scorer. |

**What this architecture does not touch.** The review walked 20 defect-log entries: the design catches 5
mechanically, makes 8 less likely and does nothing for 7. Statistic and gate design, power, instruments, label
validity and repo-level data faults — about half the log — are found by simulation, label audits and data
cards, which the scaffold covers. This document is about the universe, text-versus-code, the seal,
reproducibility and plumbing.

## 2. Principles

1. **A rule exists once**, and later stages import it.
2. **Derived facts are stored, not recomputed.** Later stages read tables and never call git.
3. **A stage reads its inputs and writes its outputs, and nothing else.**
4. **A constraint fails at build time.**
5. **A result names everything it depended on,** computed, not typed.
6. **Every part runs on the control repository before it is trusted.**
7. **For each rule, the specification says whether the text or the code governs.** SA3 is registered and its
   registration governs; where the code is kept against the text, that is a ruling, written down.
8. **Move before rewriting.** A rewritten rule is a new chance for a fault; a moved one is not.

## 3. The steps, in order, each with its exit test

| step | what | exit test |
|---|---|---|
| **0. Harness** | Run the **existing** SA3 pipeline (history walk, body harvest, scan, outcome builder, nesting, scorer) on a generated repository, with every path under a temporary directory. This is also phase 2 of the control repository. | The run completes on a negative and a positive control. A wrapper that fails on any write outside the temporary directory, and on any open of the study directory, reports none. One engine scan of a generated repository is timed. |
| **1. Three-way table** | For each rule and each control-repository case: what the existing code gives, what the manifest says, and whether they agree. | Every row is one of: code = manifest; code ≠ manifest (an existing fault, listed, ruled); undecided in the manifest (listed). No row is empty. A rule difference seeded into a copy of the code shows up in the table. |
| **2. Amendment** | SA3 Amendment 5: scoring moves from "exactly as frozen at `edc5c53`" to the stored tables. It lists every item of section 6 with its ruling and which of text or code governs. | The owner accepts it. |
| **3. Stored tables** | `file`, `touch`, `event`, `link`, `pool`, `marginal` (section 4), built by the existing functions, **moved** behind one builder each, with hashes. Later stages read the tables. | Built on the control repository: equal to the manifest except rows listed in step 1. Built for SA3's repos: every public count equal to today's, or the difference explained without opening labels. |
| **4. Seal and streams** | A generated seal (section 5). Named random streams. | A stage that reads an undeclared file fails. Permuting the repo order and the set of predictors scored gives identical numbers. The gate of section 8 of the registration is re-run under the new streams and reported as a deviation. |
| **5. Reading rule** | One function for the reading of the three confirmatory tests together, Holm step included, with "an earlier test failed" defined; a separate vocabulary for everything else. | Defect-log entries 42, 43, 47 and 48 are each a named test case. Every combination of inputs has an expected word. |
| **6. Control suite** | Section 7. | All rows pass, at the sizes and pass rules stated there. |
| **7. Seal and score** | The owner authorises. | — |

Each step is built by Opus from this document with the SA3 code open, and reviewed before the next begins.
The builder may read `tools/` and `docs/`. It may not open the study directory; steps 3 and 4 run against
SA3's real data only as a job whose outputs are the public counts.

## 4. The tables

One file per table build, named by its content hash, never written over. The hash is SHA-256 over rows in
byte order of the key, with fixed column types, floats written as IEEE hex, paths as UTF-8 bytes with a stated
escape, and nulls marked. **Test:** the same table built in reverse insertion order, and with whole numbers
written as reals, has the same hash.

| table | one row per | columns beyond the key | notes |
|---|---|---|---|
| `repo` | repo | language, unit rule, **cohort** (drawn / earlier eight), **status and reason** (scored; scan incomplete; no harvest; …), the clone's tip hash | a build stops if the clone's tip differs from the one the scans and history were made at |
| `snapshot` | repo | `cut_ct`, `sha`, `ct`, `window_start`, `window_end` | four different things, all stored. The hash is an **input**, taken from the scan; it is not recomputed |
| `file` | path in the snapshot's tree | `in_universe`, `reason`, `loc`, language | built **after** the scan (LOC comes from it). Reasons are a closed, ordered list: not the repo's language · test · vendored · documentation · example · tutorial · generated · excluded by `.gitattributes` · not in the archive · not scanned by the engine · zero LOC |
| `measure` | (file, measure) | value, instrument, version, **absent-means** (`zero` or `missing`, per measure, copied from today's code) | derived predictors (ratios to LOC, sums, non-zero yes/no, score among non-zero) are rows built by named functions |
| `touch` | (commit in the window, snapshot unit path) | — | a later commit is matched to a snapshot file by **equal path**, as today. Rename following stays sensitivity S8, not run |
| `link` | (commit, link) | kind (issue, CVE, revert, trailer), value, resolved target | **protected** |
| `event` | (unit commit, linking commit, path) | kinds counted strictly, kinds counted when every revert counts, tier, own or inherited | **protected**. This is what holds a merge's positives: its first-parent diff ∩ the linking commit's files |
| `pool` | (control commit, path) | — | **protected**: the labelled commits follow from it by subtraction |
| `marginal` | (repo, outcome) | positive files, qualifying commits, largest share, clears-floor | public. The **frozen, registered list governs**; a regenerated value that differs is reported, not used |

Invariants, failing the build:

- every tree path appears in `file` exactly once; `in_universe = 1` implies no reason;
- every `event` and `pool` path is in `file` with `in_universe = 1`;
- **every universe file is one the history could record a touch for** — the reverse check that is missing
  today. A `.gitattributes` line that switches vendoring *off* currently puts a file in the universe that can
  never be positive; the count of such files per repo is reported for a ruling (section 6, item e).

Reported, not failing: commits out of time order; a snapshot that is not on the first-parent chain (both occur
in correct data when the repo is not merge-workflow).

"Protected" for SA3 means stored apart with their own hashes; SA3's labels already exist in plaintext and were
used. For a blinded study it means `blinding_spec.md`.

## 5. The seal and the random streams

The runner wraps `open`, `sqlite3.connect` and `subprocess` for each stage and records in a ledger: every file
opened and its hash; every Python module loaded and its hash; code run as a subprocess (the engine,
`hist_meta.py`) by path and hash; interpreter, package (numpy, scipy, `tree_sitter_language_pack`, SQLite) and
git versions; `PYTHONHASHSEED`; each clone's tip. The seal is the closure of the ledger for a result. The
scoring job recomputes it and stops on any difference. A result carries its seal's hash.

What it cannot do, stated: SA3's scans were made without a fixed hash seed, so they can be hashed but not
reproduced.

Git runs only through one wrapper: `GIT_NO_LAZY_FETCH=1`, `gc.auto=0`, no writing command on a clone. A
blobless clone that cannot serve a command is a repo status with a reason, not a crash.

Random streams are named for study, repo and purpose. The registered "200 draws, seed 2982" becomes one stream
per repo and purpose seeded from 2982; this changes the drawn numbers and is a listed deviation.

Mechanical checks, run with the tests:

- functions in the moved code take every registered parameter as a **required argument**; no module assigns a
  numeric constant at module level except the one parameter file. (A lint on literal *values* was tried by the
  reviewer on the existing code: about half its alarms were not parameters.)
- no absolute path outside one `paths` module;
- no import of the label tables' reader outside the scoring job.

## 6. Where the stored tables could change SA3's numbers

The default for each is **what the registered code does**. Each goes in Amendment 5 with its ruling.

| # | item | default | governed by |
|---|---|---|---|
| a | Matching later commits to snapshot files | equal path; no rename following | code |
| b | A missing predictor value | per measure, as today: the branch-state primary and `in_degree` read absent as 0 | code |
| c | Random streams | named streams; the gate is re-run and reported | deviation |
| d | The snapshot | the scanned commit, an input; the cut is stored beside it | code |
| e | Universe files the history cannot touch | **ruled 2026-11-14:** counted per repo, then removed from the universe; a deviation, reported with the counts | owner |
| f | The list of scored repos | the frozen list | registration |
| g | The universe variant | with `.gitattributes`, tutorial exclusions and the scan's generated list | code |
| h | Tree-wide denominator | the universe | code |
| i | Keyword rule for the keyword outcome vs for tainting a merge | **ruled 2026-11-14:** two rules, as today, for SA3; one rule in the next study | code |
| j | Tainted merges | **ruled 2026-11-14:** counted when they inherit; taint governs the keyword outcome and the control pool | code; **the text is corrected** in Amendment 5 (defect log 54) |
| k | Holm step, "not robust", the vocabulary outside the confirmatory tests | as the registration says; the code is fixed (defect log 42, 43, 47) | text |
| l | Stored `.gitattributes` cut at 200,000 characters | report whether any repo reaches it | — |

## 7. The control suite

Sizes come from the first control-repository review: 800 files and 20 seeds resolve ±0.03 on a truth
statistic. Before the suite's size is fixed, step 0 measures the time of one engine scan of a generated
repository; the numbers below are then confirmed or cut, and each pass rule is simulated for its
false-failure rate before it is used.

| run | size | must hold |
|---|---|---|
| negative control | 800 files, 20 seeds, a span leaving 730 days after the snapshot | the universe equals the manifest's unit files on every path; decided labels equal the manifest's; each property's effect, **against the expected labels**, is within three standard errors of the same statistic computed from the manifest's expected labels |
| positive control, three strengths | 800 files, 10 seeds each | the planted property is recovered and grows with strength; the others stay within the negative control's spread |
| each mutation | default profile, 3 seeds | a recorded expectation: universe and labels still match, **or** the pipeline reports the repository unusable for a stated reason. A mutation the pipeline gets silently wrong fails |
| quick set, with the ordinary tests | one negative and one positive repository, default profile, 1 seed | universe and labels only (exact comparisons; no statistic at one seed) |

Two truths exist by design: true fixes, and the labels the written rule should give (silent fixes differ).
Universe and label rows are judged against the expected labels; a separate, reported row gives the statistic
against true fixes, which is what the label costs.

## 8. Blinding

Not on SA3's route. `tools/blind/` is built from `blinding_spec.md` (Revision 2) and tested on the control
repository, where the truth is known. It reads labels through the `event` and `pool` tables of section 4, so
the first blinded study plugs into the same tables.

What it buys, stated: `touch`, the commit messages and the label rules are all readable, so true labels are a
short join for any session. Blinding here stops the accidental join, gives scrambles to develop on, and leaves
an audit trail. Real blinding is data that is not on the machine.

## 9. Deferred until a second study needs it

A full `defs` package rewritten from the rules; `study.toml` beyond a flat parameter file; plug-ins; a
generated rule-to-code table (it proves a mapping, not behaviour — the weight belongs on a control-repository
case per rule); rename following; the `prior` point and the change effect. The first draft's design for these
was not committed; the design review quotes the parts it examined.

## 10. What this does not do

- It does not make the other 220 tools consistent, and does not delete them.
- It does not change SA3's registered statistic or hypotheses.
- It does not make labels unknowable on this machine.

## 11. Owner rulings, 2026-11-14

The owner accepted all three recommendations below. Nothing here is open.

1. **Item e:** files that are ranked but can never be positive because `.gitattributes` switches an exclusion
   off. Rule after the count: remove them from the universe (my recommendation: a ranked file that cannot be
   positive is defect 2 again) or keep the registered universe and report them.
2. **Item i:** keep two keyword rules (my recommendation: yes for SA3, corrected in the next study).
3. **A second, independent build:** yes, as an experiment, for the core where an error changes the answer:
   the reading rule (step 5) and the `event` table builder (step 3). Built by a different model from the same
   text without sight of the first build; outputs compared number for number on the control repository; known
   faults seeded into one copy, and the count caught by the comparison recorded beside the count a review
   catches.

Item e is applied in step 3, after the count; all three go into Amendment 5 (step 2).

## 12. Review record

| review | by | result |
|---|---|---|
| Design review 1 | Claude Fable 5.2, independent session, 2026-11-14 | 5 blockers, 9 major, 6 minor. `reviews/research_codebase_review_claude.md` |
| Reproduced by the author before acting | equal-path matching (`sa3_outcomes.py:168-171`) · missing read as zero (`sa3_score.py:103`) · scramble leak, measured on control repositories: 25% of files alone in a cell, 36–38% of true positives positive in all 20 copies; the reviewer's own remedy (top-level directory) still leaves 12–16% at 300 files, so `blinding_spec.md` now sets a minimum cell size instead | adopted, the last with a change |
| Adopted without separate reproduction (cited to code by the reviewer) | invariants that fail on correct data; the `label` table's missing path; the unsafe exit test; the Holm dimension; provenance gaps; the lint's false alarms; the smaller route | — |
| Not adopted | — | — |
| Still owed | a second design review by a different model (checklist item 15: Gemini, on the pull request) | — |
