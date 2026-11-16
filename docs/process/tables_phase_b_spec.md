# Stored tables, phase B — SA3's real data, predictor side only (specification)

**Status: Revision 2, 2026-11-14, after an independent review. Nothing built, nothing run.** Step 3, phase B,
of `research_codebase_spec.md`. **This is the first step that reads SA3's real study data.** The owner gave the
go-ahead on 2026-11-14; the gates of this document still apply before the run.

**What Revision 2 changed.** The first version was reviewed (`reviews/tables_phase_b_review_claude.md`: 4
blockers, 12 major, 10 minor; "safe after changes; not safe to run as written"). On damage the design held:
under a read-only bind every git and SQLite write the reviewer tried failed and left files unchanged. The
faults were about what could leak. The answer adopted is the review's own:

- **The job binds nothing from the label side.** No outcome file, no link harvest. Nine of the ten counts
  never needed them. What is not there cannot leak.
- **No `touch`, `event`, `link`, `pool` or `marginal` table is built here.** With readable commit messages,
  `touch` is the label minus one pattern; calling it public was not honest. Those tables wait for the
  owner-run job, which needs them for Amendment 5 section 9.
- **The count that needs the links** (lower-case tracker keys) **moves to the owner-run job**, by this
  document's own rule.
- The default target is a decoy; the real run needs an explicit flag and a guard. Scan databases are copied
  before being opened. A failed invariant reports a number and a count, never a row from a protected table.

## What the job reads, per repo

Bound read-only, one repo at a time, and nothing else from the study directory:

| input | used for |
|---|---|
| the history database (`history/<repo>.db`) | commits, the walk's parameters, the frame |
| the MOD-1 database the frame reads (`dbs/<repo>.db`), if `frame()` requires it | the cut and the snapshot |
| the scan sidecar and the scan database, **with its `-wal` and `-shm` files if present** | the tree's archive count, the stored `.gitattributes`, LOC, measures |
| the nesting file | nesting coverage |
| the corpus clone | `git ls-tree` of the snapshot; `git archive` where the clone can serve it |
| GitHub's two cached lists; the reference code | the unit rule |

**Not bound: `sa3_outcomes/`, `meta_sa3/`, `meta_mod1/`, and every other repo's files.** A test lists the study
path from inside the sandbox and finds exactly the declared inputs.

## What the job writes

To one new output directory outside the study directory:

1. Per repo, the tables `repo`, `snapshot`, `file`, `measure`, with `index.json`.
2. Per repo a data card, and one study card, holding the counts below **and nothing else**. The phase A data
   card's rows that depend on activity (the share of a directory's files untouched in the window) are not
   produced in phase B.
3. A run log: stages, return codes, and for a failed invariant its number and the count of failing rows.

## The counts (Amendment 5, section 7)

| # | count | how |
|---|---|---|
| 1 | Every (repo, measure) cell that is silent under the rule as at `edc5c53`, under the rule as at `8fb7fe0`, or both; the cells where the two differ, by measure, marking the confirmatory measures | below |
| 2 | For the 15 drawn repos: the cut, the scanned snapshot's time, and whether the window start equals the cut | `frame()`, the sidecar, the clone's commit time |
| 3 | Window start, window end, usable commits; whether the window ends after it starts | the same |
| 4 | Completeness on the registered measure (what `universe()` returns, with "archive unavailable" reported apart from a true zero) and against the tree with reasons | `file` |
| 5 | Files excluded by each of the four patterns of `PU_generic_dirs_restored`, and how many have scan rows | `file` |
| 6 | Universe files that the history walk's own unit rule excludes (the `.gitattributes` re-inclusion). Other ways the two can disagree — path spelling, symbolic links and submodule entries — are counted **only as** "tree entries that are not regular files" and "scan paths not in the tree"; the review showed the code can see no more than that | `file` |
| 8 | The share of universe files with a nesting value | `measure` |
| 9 | The stored `.gitattributes` text: its length, and whether it reaches the 200,000-character cut | the sidecar |
| 10 | How each prebuilt input was made: SHA-256 of GitHub's two lists; the history walk's unit rule and C-family flag; engine id; hash seed if recorded; grammar pack version | sidecars, the history's `meta` |

Count 7 of the first version, and the harvest's flags, are produced by the owner-run job.

**Count 1, exactly.** Silence does not depend on any outcome, but the scorer computes its predictors in
`load()`, which also reads the outcome file. So: the reference scorer's `load()` and `silent()` are **called
unchanged**, once from the file as at `edc5c53` and once as at `8fb7fe0`, each in its own process, with the
outcome directory in the sandbox replaced by **stub outcome files generated by the job**: the same keys, every
list empty. No real outcome is bound, so none can be read. Two checks before the numbers are believed:

- on control repositories, silence computed with stubs equals silence computed with the real outcome files,
  for every cell, under both rules;
- on SA3, the `silent` values this gives for the four primaries equal those already published in
  `docs/sa3_placebo.json`.

**Expected, so that a surprise is visible:** Amendment 4 says the old rule silenced the yes/no indicator and
nesting depth everywhere, and defect log 46 says three count measures changed in 14 repo cells. So the
differing cells should be: the indicator and the nesting measures in most repos, plus 14 cells of count
measures. Anything else is reported as unexpected and not explained away.

## How it runs

**A read-only sandbox, as new code** (`tools/harness/sandbox_ro.py`; the existing sandbox and its tests are
not touched): root read-only; home, `/tmp`, the projects root and the corpus root hidden; **only the declared
inputs of one repo bound in, read-only**; the engine export read-only and never run; one output directory and
one scratch directory read-write; the network unshared; `GIT_NO_LAZY_FETCH=1`, `gc.auto=0`.

**The default target is a decoy.** `phase_b.py` with no target refuses. `--decoy DIR` is the ordinary mode.
The real study directory is used only with `--real --i-am-the-reviewer-session`, and then only if a guard,
reading the kernel's mount table before touching any path, finds the study path and the clone mounted
read-only.

**SQLite.** Scan databases are in write-ahead mode. Opening one read-only in a writable directory creates side
files; under a read-only bind one with no side file fails, and `immutable=1` can return stale rows. So every
database is **copied, with its `-wal` and `-shm` if present, into the scratch directory, and the copy is
opened**. The originals are never opened by SQLite.

**Git.** `ls-tree -r` works on a blobless clone; `archive` does not without a fetch. So the `file` table's
paths come from `ls-tree`. Where `archive` fails, `in_archive` is "unknown", the registered completeness is
"archive unavailable", and nothing is fetched. `universe()` returns `complete = 0.0` when its own archive call
fails, without an error: the job detects that case and reports it; it does not treat it as zero.

**Repos the pipeline excluded.** Six of the 46 are marked scan-incomplete and have no outcome file. They get
`repo`, `snapshot` and `file` tables and counts 3 to 6 and 9 to 10 all the same: those counts matter most
there. A repo for which a stage cannot run is recorded with the stage and the reason, and the run continues.

**Phase A's builder is not called and not edited**, apart from one change: `tools/tables/invariants.py`
reports a failing row of `event` or `pool` by invariant number and count only (it named the commit and the
path; on real data that names positive files). Phase B imports the phase A modules that need no outcome
(`schema`, `canon`, the `file`, `repo`, `snapshot` and `measure` builders, refactored out of `build.py` into
importable functions without changing what they produce — the phase A tests must still pass and the phase A
table hashes must be unchanged).

**Before and after.** From outside the job, inside a read-only sandbox of its own, a manifest is taken of
every declared input and of each clone's `.git` directory: path, size, modification time, change time. It is
taken before the run and after it, and compared. This is cheaper than hashing tens of gigabytes and catches
what went wrong last time (new pack files, an emptied reflog).

## Before the real run

1. **Sandbox tests on a decoy:** a write to the study path fails; a write to a clone fails; `git gc` and a
   fetch fail; the output and scratch directories are the only writable places; the study path lists exactly
   the declared inputs; a deliberately misbehaving stage leaves the decoy's manifest unchanged.
2. **Rehearsal** on a decoy built by the harness from control repositories — the base pair, `generic_dir_names`,
   `vendored_half`, `bot_merges`, `merge_workflow`, `mixed_language`, and four cases the review named that a
   control repository can imitate: a repo with no outcome file; a blobless clone of a control repository; a
   scan database in write-ahead mode with and without side files; a repo given a `.gitattributes` line that
   switches vendoring off for one directory (written into the decoy's sidecar and tree by the test, not by a
   change to the generator). The four tables must equal phase A's for the same repositories, hash for hash,
   where phase A builds them; each count must equal the value known from the manifest.
3. **What the rehearsal cannot show** is stated in the run log's header: the real layout's sizes, the earlier
   eight repos' later window start, C-family repos with headers, and whether the engine left side files. For
   each, the job fails safe (a recorded reason) and a **preflight** reports, per repo and before any table is
   built: which declared inputs exist, which databases have side files, whether the clone is partial.
4. **The control-suite bounds' false-failure rates** (`research_codebase_spec.md` section 7) are simulated and
   written there.

## The run, and after it

- Preflight first, on all repos; its report is read before anything else runs.
- Then one repo at a time, in the frozen list's order, then the remaining repos.
- Afterwards a session reads the study card, the data cards, the index files and the four tables.
- **A failure on real data is not investigated on real data.** It is reproduced on a decoy, or reported to the
  owner with the stage, the reason and the count.

## Deliverables

```
tools/harness/sandbox_ro.py     the read-only, declared-inputs sandbox and its guard
tools/tables/phase_b.py         the job: --decoy DIR | --real --i-am-the-reviewer-session ; --out DIR
tools/tables/study_card.py      the nine counts
tools/tables/silence.py         count 1: stub outcomes, the two versions of load() and silent(), called
tools/tables/manifest_stat.py   the before / after manifest
tests/test_tables_phase_b.py
```

and the two listed changes to phase A (`invariants.py` messages; the builders made importable).

## Rules for the builder

- **The builder never runs the job with `--real`**, and never opens, lists or stats the real study directory,
  the corpus, the pool or `~/.blind`, by any route. It builds and tests on decoys.
- Write only the deliverables and the two listed phase A changes. No commits. No edit to any SA3 tool or to
  `tools/harness/sandbox.py`.
- Report: what was built; the sandbox tests; the rehearsal — table hashes against phase A and each count
  against its known value; the silence check on control repositories under both rules; that the phase A tests
  and hashes are unchanged; anything in this document that is wrong, ambiguous, unsafe or impossible.

## Review record

| point | disposition |
|---|---|
| B1 a failed invariant names positive files | adopted: number and count only; phase A changed |
| B2 the default target was real data; no guard | adopted: decoy by default, flag and mount-table guard |
| B3 `touch` is the label minus one pattern | adopted: not built here; nor the untouched-share row |
| B4 count 1 is not computable from `measure` | adopted: `load()` and `silent()` called with stub outcomes; expected remainder stated |
| M1 `universe()` swallows a failed archive | adopted: detected and reported |
| M2 write-ahead side files | adopted: copy, then open the copy; preflight |
| M3 protected tables do not belong here | adopted |
| M4 the hash check | adopted: an outside stat manifest including the clones |
| M5 the whole study directory was bound | adopted: declared inputs only |
| M6 scan-incomplete repos | adopted |
| M7 partial clones | adopted: `ls-tree`; "archive unavailable" |
| M8 count 6's causes | adopted: only what the code can see is promised |
| M9 phase A's builder | adopted: importable builders, hashes unchanged |
| M10 count 7 | moved to the owner-run job |
| M11 what the rehearsal cannot tell | adopted: stated; preflight; fail safe |
| M12 the data card | adopted: phase B's card is the counts only |
| Not adopted | none |
