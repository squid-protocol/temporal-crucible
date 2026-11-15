# Review — the scoring step specification (`docs/process/scoring_step_spec.md`, draft of 2026-11-15)

**Reviewer:** an independent session (Claude), 2026-11-15. Read at `905a366` on `sa3/build`, tree clean.
No SA3 tool, harness or job was run. No real input was opened. The numbers in `docs/sa3_placebo.json` and
`docs/sa3_outcome_marginals.json` were not read. Git and bwrap claims were tried on throwaway repositories
under `~/.claude/jobs/24bf9d40/tmp/scoring_review/` (git 2.43.0, bubblewrap 0.9.0).

Each finding is marked **[code]** (verified in code), **[run]** (run on throwaway data) or **[reasoned]**
(reasoned, not run).

## Verdict

**Sound to build after changes. Not sound to build as written.** The core design holds: a fresh clone at a
named commit gives the reference `lock` a real repository, `lock` hashes the nine files the seal expects, and
`score` reads the real inputs from compiled-in paths that do not depend on where the clone sits. I tested the
clone and the sandbox layout on throwaway data and they work. But the draft does not say what happens when
anything fails after the reference `score` has written its result, and it has no mechanism that makes or
records "once". Those two are blockers, because this job runs one time. Eleven further points would each
make a builder guess, and several of the guesses fail only on real data. None needs a sealed file edited.

Counts: **2 blockers, 11 major, 9 minor.**

---

## Blockers

### B1. After step 6 the job can strand the confirmatory result **[reasoned; code]**

The spec stops "at the first failure" for all ten steps (`scoring_step_spec.md:30-31`). It refuses a
non-empty protected directory, and "nothing is resumed or repeated" (`:46`). Steps 7 to 10 run a lot of new
code on real data for the first time: label tables, the label-side input check, two more scoring loops, the
harvest variants, the validator. If any of them fails, the result exists in the clone's `docs/` inside the
protected directory, and nothing is published. The only ways forward are then a copy by hand out of the
protected directory, or a new directory and a second `score`. Both are the things the step exists to prevent.

**Change.** Split the job at step 6.
- Steps 1 to 5 stop on failure. Nothing has been scored.
- Directly after step 6: validate `sa3_result.json` by shape, publish it byte for byte, write the receipt
  (its SHA-256, the commit, the seal's SHA-256). Only then go on.
- Steps 7 to 9 never stop the job. Each ends as done or as `failed` with a code. Step 10 always writes the
  report.
- A resume command re-runs steps 7 to 10 from the stored result. It checks the result's SHA-256 against the
  receipt and can never start the reference `score`. Each resume is recorded. If code changed between the
  first attempt and the resume, the report says so, and those parts are labelled "run later" (Amendment 5
  section 6 already has that label).

**How to test.** On a decoy study, make each of steps 7, 8 and 9 fail in turn (a planted exception). Each
time: the published result equals the clone's file byte for byte; the report exists and names the failed
step; a resume completes the report; the record shows one start of `score`.

### B2. "Once" is not defined, not enforced and not recorded **[code]**

The only guard is that the protected directory must be empty (`:46`, the same rule as
`tools/owner/prepare.py:393-396`). That is once per directory. A second command with `score-2` scores again
and nothing anywhere says the first run happened. Compare `tools/blind/jobcore.py`: a ledger keyed by the
seal's hash, read before anything else (`:298-307`); an entry written **before** the scorer starts
(`:344-347`); a second run needs `--rerun REASON`, which is recorded; a receipt line the owner keeps off the
machine (`:376-384`).

The reference `score` is deterministic (seed 2982, one stream, `sa3_score.py:361`). A second run on the same
inputs and libraries should give the same bytes. So "once" protects the record, not the arithmetic: it rules
out "run, look, change something, run again".

**Change — define it now.**
- "Once" means: the reference `score` process is **started** at most once on the real inputs.
- A ledger at a fixed path outside any run directory (the launcher writes it on the host; a copy goes to the
  public directory). Entry `started`, with time, commit, seal SHA-256, written and flushed before step 6.
  Entry `completed`, with the result's SHA-256, after it. The receipt is printed.
- Any ledger entry: the job refuses, whatever directory is named.
- A failure in steps 1 to 5 writes no entry. A new attempt is then still the first scoring. Each attempt is
  listed in the report.
- A `started` with no `completed` (crash, time-out, power): the reference prints no estimate until after it
  has written the file (`sa3_score.py:500-507`), so nothing was seen. A second start needs `--rerun REASON`
  and is disclosed in the report's first lines.
- A `completed`: no second start, ever. Only the resume of B1.

**How to test.** Decoy runs: a second run after a completed one refuses with a different directory; a run
killed during step 6 leaves `started`; `--rerun` then records the reason; a failure at step 3 leaves no entry.

---

## Major

### M1. The pin has no source, and a pin the job records about itself is not a pin **[code; run]**

"Its commit is the named one" (`:35`), but the command (`:25-27`) carries no commit. A constant in the code
cannot work: a commit cannot contain its own hash. The report's list of SHA-256 values (`:19`, `:69`) is
written by the code it describes; any code could write any list.

Can the hashes go into run-2's seal? **No, not without editing sealed code.** The list is `JOB_CODE` in
`tools/owner/report.py:53-54`; `seal.py:130-131` reads it; the schema accepts only those keys
(`report.py:138`, `:197`); and `report.py` is itself on the list.

**What is achievable.**
1. `--commit <40 hex>` is a required argument. The job refuses unless `git rev-parse HEAD` equals it and
   `git status --porcelain` is empty.
2. The value comes from outside the commit: the hand-over message to the owner, and the commit pushed to the
   remote before run-2 (the branch is pushed today; a push leaves a dated record a third party holds). An
   annotated tag on the commit, also pushed, is a second witness. **[run]**: a tag made in a linked worktree
   resolved to the same commit in a clone.
3. The build review names the **tree hashes** of `tools/` it read. **[run]**: `git rev-parse C:tools` is the
   same for two commits that differ only under `docs/`. So a later documents-only commit does not unpin the
   reviewed code, and anyone can check it.
4. Every stage runs from code taken from the clone at that commit, not from the checkout. The checkout has
   ignored `__pycache__` directories under `tools/` that "clean" does not see (`git status --ignored`).

The report's hash list then stays as a convenience. What it cannot remove: the owner starts the launcher from
the checkout, and that is trusted, as it is for the whole study.

**How to test.** Decoy: wrong `--commit` refuses; one untracked file under `tools/` refuses; a stage's loaded
module hashes equal `git ls-tree` of the clone (the import recorder of `placebo_check.py:193-197` does this
already).

### M2. The reading note is missing from the documents to enter **[code]**

Section 1 item 1 enters "the second erratum" and says "nothing else in a sealed document changes" (`:10-12`).
The dated note on the reading rule was accepted after this draft. It says it is entered into
`docs/sa3_registration.md` with the erratum, before the seal is re-taken
(`sa3_amendment5_note_reading_draft.md:3-5`; `comparison_scorer_part2_spec.md:27-29`). Followed literally, the
registration is sealed without the ruling that the report's "as corrected" column rests on, and entering it
later breaks the seal.

**Change.** Name both documents. Say what "the consolidated text updated to match" means for each (the
erratum rewrites section 6 item 1; the note touches the Holm sentence near the consolidated text's line 136).
**Test:** after the commit, a grep finds both texts in the registration; the only files changed are the two
sealed documents and the two drafts.

### M3. The order of operations leaves out where the build sits and what run-2 must show **[code]**

Which things does run-1's seal cover (`docs/sa3_seal_run1.json` keys)? `inputs`, `lists`, `clones`, `code`
(13 reference modules), `job_code` (7 files), `documents` (6), `lock_expected` (9), `runtime`.

What the new entries change: `documents.sa3_registration.md`, `documents.sa3_registration_consolidated.md`
(SHA-256 and blob each), and `lock_expected.docs/sa3_registration_consolidated.md`. Five leaf values.
Nothing else.

Will run-2 still pass? Yes, as far as code shows. The placebo stage reads only the marginals copy and the
committed placebo file (`prepare.py:533-536`, `:591-602`); the registration is not an input. "Unchanged since
`8fb7fe0`" looks at 13 modules (`seal.py:100-109`). "A equals stored" depends on data only.

Must anything be committed between run-2 and the scoring run? **No, and nothing should be.** `tools/scoring/`,
`tools/compare/`, tests and process documents are in no seal, so committing them would not break
`seal.py verify`. But it would move HEAD away from the pinned commit. The draft's section 1 puts the pin after
run-2 (`:16-20`) and section 4 puts the build "before the owner runs it" (`:74-80`) without saying before
which run.

Four gaps:
- The draft does not say all code is final before run-2.
- Nothing compares run-2's seal with run-1's. `seal.diff` (`seal.py:148-160`) prints the names. The expected
  answer is exactly the five leaf names above. Anything else (a library, an input, a clone) is a stop with no
  outcome seen.
- The job takes `--seal` only. It should also refuse unless `owner_report.json` beside it says `PASS`,
  target `real`, placebo `bytes_equal`. Run-1's verdict was `bytes_equal`; `numbers_equal` in run-2 would
  mean a library changed in between and should stop the step, not pass it.
- `runtime` is sealed. A package update between run-2 and the scoring run fails step 1. Say: same day, no
  updates.

My proposed order is at the end. **Test:** on a decoy, take a seal, change one sealed document, take a second;
the diff prints the expected names only.

### M4. The predictor-side tables and check on real data are never scheduled **[code]**

Step 8 needs `call_degree` and `flux` built from the real scan databases, and the comparison spec wants the
predictor-side input check run "before scoring" as a session-run stage (`comparison_scorer_spec.md:143-155`).
`tools/compare/README.md` says of both real entry points: "Neither was run by the builder." I found no record
that either has been run since. The scoring spec's steps 7 and 8 mention only the label side.

**Change.** Add a numbered step before the pin: who runs it, at which commit, where the tables go, and that
its public verdict and the table hashes are committed. The job then checks those hashes and the phase B table
hashes before step 7, and binds the tables root read-only. Say what a "not equal" there means (stop; no label
is involved, so it can be investigated freely). **Test:** decoy: one changed table byte stops the job before
step 7 with its own code.

### M5. "Real inputs bound read-only" does not say originals or copies, and originals may not open **[code]**

`score` opens each scan and history database with `mode=ro` (`mod1_lift.py:49-50`, `sa3_score.py:89`). In
run-1's seal all 40 repos have a `scan_db-wal` entry, and all 40 are the hash of an empty file: the scan
databases are in write-ahead mode. The preparation job never opened an original. It copied each database,
checkpointed the copy and set it to rollback mode "so it opens from a read-only bind with no side file"
(`tools/owner/DECISIONS.md` item 7; `prepare.py:219-254`). The placebo stage read those copies.

So the answer to "does `score` read the inputs the seal covers" is: it reads from the compiled-in study path
(`mod1_lift.py:42`; `sa3_outcomes.py:41-43`; `sa3_score.py:44`), the pool from `EXPOSURE_POOL`
(`_engine.py:33-35`), and `docs/` from the clone. What sits at the study path is whatever the job binds
there. The seal covers the originals' bytes; a converted copy has other bytes.

**Change.** Step 6 binds exactly what `Job.placebo` binds (`prepare.py:591-602`), for **all** rows with status
`ok`, not only those that clear the primary floor: history copy, scan copy, sidecar, nesting file, outcome
file, clone, GitHub's two lists. The copies are made inside this job by the owner job's `copy` stage, which
hashes each original first; the job compares those hashes with the seal and stops on a difference. That
closes the gap `seal.py:34` itself admits ("it does not prove that a run read those bytes"). The harvest is
not needed by `score`. **Test:** decoy run; plus a decoy whose scan database changes between the seal and the
copy stops before step 4.

### M6. The clone cannot be bound "read-only except `docs/`" the obvious way **[code; run]**

- `sandbox_ro` binds read-write directories first, then code, then inputs (`sandbox_ro.py:164-169`). A
  read-only bind of the whole clone therefore covers a writable `docs/`. **[run]**: with that order the write
  to `docs/sa3_lock.json` fails with "Read-only file system". `sandbox_ro.py` is sealed job code; the order
  cannot be changed.
- What works **[run]**: `docs/` as the read-write directory; `.git` and `tools/` as two read-only inputs. In a
  bwrap sandbox with that layout and nothing else of the repository bound: `git status --porcelain -- <files>`
  printed nothing, `rev-parse HEAD` gave the named commit, `hash-object` gave the content hash, the write
  into `docs/` succeeded, writes into `tools/` and `.git` were refused, no `index.lock` appeared. A whole-tree
  `git status` there shows the unbound files as deleted, so the whole-tree check belongs on the host.
- The launcher must not run from the clone. `check_rw` refuses any directory inside `sandbox.WORKTREE`
  (`sandbox_ro.py:102-106`), and that constant is the location of the running file (`sandbox.py:48`). Run from
  the clone, `clone/docs` is refused as a write location.
- `seal.py verify` needs its own empty protected directory each time (`seal.py:197-198`); it is called
  twice. On a real run `--code-root` is refused (`prepare.py:363-364`), so step 5 must point it at the
  clone's lock file with `--real-docs <clone>/docs` (`seal.py:188`, `:223`).

**Change.** Write the layout into the spec: the bind list, the two verify directories, which tree the launcher
and the stages run from. **Test:** the decoy run of section 4; plus assert on the host after step 6 that
`git -C <clone> status --porcelain` is exactly the two untracked files `docs/sa3_lock.json` and
`docs/sa3_result.json`.

**For the record, the fresh-clone design itself is sound [run].** A `git clone --no-checkout` from a linked
worktree's path, and from its main repository, then `checkout --detach <commit>` (a commit that is not a
branch tip): `.git` is a directory, no `commondir`, no alternates, `HEAD` is the named commit, status is
clean. `git hash-object` equals SHA-1 of `blob <length>\0<bytes>` computed in Python, so the nine lock hashes
are content hashes and do not depend on the path. The repository has no `.gitattributes`, no filter and no
`core.autocrlf`, and step 3 would catch a checkout conversion anyway. The linked worktree alone, without its
main repository, fails every git command inside the sandbox, as `tools/owner/README.md` says. `score` writes
one file, `docs/sa3_result.json` (`sa3_score.py:500`); `lock` writes one, `docs/sa3_lock.json` (`:520`).

### M7. The reference loader has not been run under the seal, with real labels, on about half the repos **[code]**

The placebo stage loads only repos that clear the primary floor (`sa3_score.py:233`; `prepare.py:523-524`):
20 of the 40. `score` loads every `ok` row (`:354`, `:362-363`). `load` asserts that every outcome file path
is a universe file and indexes every commit's paths (`:112-121`). For the other 20 repos that code meets the
real outcome files for the first time in step 6. A failure there kills the one confirmatory run part-way.

**Change.** Move the loader part of step 7 before step 6: the reference `load(repo, True)` unchanged, each
`ok` repo, real outcome file bound, in the sandbox; the arrays are kept in the protected directory for the
label-side check later; the only thing that leaves is ok or failed per repo. It scores nothing. It stops the
job on a failure, before anything is scored. The placebo stage of run-1 is the precedent: it did the same
for 20 repos. **Test:** a decoy with one outcome path outside the universe stops before step 6 and leaves no
ledger entry.

### M8. Every real-data door in `tools/compare/` is shut, and the spec does not say how the job gets in **[code]**

- `harvest_variant.py:221-228`, `:248-252`: study and pool must be decoys.
- `input_check.py:234-238`: an outcome file may be bound "only from a decoy".
- `variants.py:233`: builds its layout from a decoy directory; `:271` refuses `--real`.
- `tables.py:360`: the label tables refuse `--real`; `build_label_tables` (`:318`) reads outcome files
  in-process, which on real data means outside any sandbox.

The job must either edit these files or re-implement their launchers in `tools/scoring/`. Either changes or
duplicates accepted code. **Change.** Say which. If `tools/compare/` is edited: the edits land before the
pin, parts 1 and 2 pass again in all three test modes, both decoy cell maps stay all-equal, and the build
review covers the diff. Say that the label tables are built in a sandbox stage with the outcome files bound
read-only, and that the comparison scorer's "sealed copies" directory is the clone after step 5.

Can any of it write to real data? Not through a sandbox: every bind is read-only and the guard reads the
mount table first (`sandbox_ro.py:217-250`). `harvest_bodies` would delete a harvest without its flags
(`sa3_outcomes.py:58`); the bind refuses that (`DECISIONS.md` item 8). The risk is in-process code on the
host. Keep it to reading the protected directory.

### M9. Run time is unknown and the inherited time-out can kill the one run **[reasoned from the public run log]**

From `docs/sa3_owner_run_log_run1.json`: placebo 68 s for 20 repos; `seal_inputs` 37 s; all copies 44 s; the
two builds 168 s; total 409 s.

- The placebo does 1,200 effect evaluations per repo (`sa3_score.py:245-254`). `score` does, for a repo on
  the primary outcome, up to about 12,400 permuted evaluations and about 9,200 in the matched control
  (`:365-406`, `:309-331`), plus the bootstrap, the residual and the logistic fit per cell; about 4,600 for a
  keyword-only repo. That is roughly 20 times the placebo's arithmetic over twice the repos.
- So one scoring loop is somewhere between **25 and 75 minutes**. I could not measure it.
- The job runs that loop three to five times: reference, comparison, named streams, and up to two harvest
  variants.
- The rest (two verifies, copies, the loader on 40 repos, harvest prepares and builds) is about 10 to 15
  minutes.

**Estimate: one to six hours if run in sequence.** The inherited stage time-out is 7,200 s (`prepare.py:82`).
The sandbox dies with its parent (`sandbox_ro.py:179`), so a dropped terminal kills step 6.

**Change.** Time one loop on a decoy study and scale by evaluations; write the estimate in the hand-over. Give
step 6 its own time-out of a day. Tell the owner to run inside `tmux`. Steps 8 and 9 can run side by side
after step 6. **Test:** the decoy timing; a decoy run started in a terminal that is then closed, to show what
the ledger holds.

### M10. The failure policy leaves the important ruling until after the result is seen **[reasoned]**

"Whether a failed check changes how the result may be described is the owner's ruling, made after the
report" (`:48-51`). A ruling made knowing which way the result points is the kind of choice the study has
spent five amendments removing. That the reference result stands is right and is Amendment 5 sections 2 and
9. The wording should be fixed now.

| event | when | pre-commitment I propose |
|---|---|---|
| run-2 placebo `differs`, `failed`, or not `bytes_equal` as run-1 was | before scoring | stop; nothing scored |
| step 1, 3 or 5 differs | before scoring | stop; nothing scored |
| loader rehearsal fails (M7) | before scoring | stop; nothing scored |
| the placebo **gate** | already fixed | it is the `valid` field of the sealed, committed placebo file (`sa3_score.py:353-356`, `:442-443`). It cannot newly fail in step 6. The report prints it. Say so, so nobody waits for it |
| label-side input check "not equal" or "not comparable" | after scoring | result stands; fixed sentence: "the inputs the two routes read were not shown equal"; the cell map is still printed |
| cell map: R cells differ, W and D all equal | after scoring | result stands; fixed sentence naming the R class; the "defect-specific" against "tracks activity" wording is marked unverified |
| cell map: any W or D cell differs | after scoring | result stands as the registered output; the label gains "the check did not confirm this run"; no hypothesis is called confirmatory until a decoy investigation, written up and dated, places the cause |
| a corrected reading or a variant fails to run | after scoring | reported "failed: code"; a later run is dated and labelled later; never blocks the report |

The owner should accept or change this table before the build. **Test:** run the job on the blind test's
faulty decoy copies; each class of failure prints its fixed sentence and no other.

### M11. The report cannot be built from section 3 **[code]**

- **The deviation table** is specified nowhere. The spec repeats Amendment 5's one sentence (`:66-68`). There
  is no list of rows and no source list. Every row is known today: Amendment 5 sections 1 and 4, the two
  errata, the reading note, `docs/sa3_code_review.md`, the defect log, and part 2's own deviation ("every one
  is run", `comparison_scorer_part2_spec.md:197-199`). **It should be written now by a session, reviewed,
  committed before the pin, and copied in by the job with its hash.** Only one column comes from the run:
  whether the coded and corrected readings came out the same. A table written by a session after reading the
  result is a forking path.
- **Missing from the list**, though Amendment 5 section 8 requires them: "what was seen and when"
  (Amendment 4), and the planted-effect recovery paragraph with its limits. Also missing and needed to read a
  null: the power statement (`docs/sa3_power.md`); a pointer to the pre-scoring counts and the tracker-key
  count; the blind test's result with what it does not show (`blind_test_run1/RESULT.md`); the sentence that
  a full match is "agreement between two routes and one description" (`comparison_scorer_spec.md:34-39`);
  the five variants reported equal from counts and the two not run; the list of attempts (B2).
- **Defect 47 and the raw file.** `sa3_result.json` goes out byte for byte, and it holds "supported" and
  "contradicted" for every summary of every cut (`sa3_score.py:160-170`, `:497-499`). The report must say
  that those words outside the three tests are not readings.
- **No schema.** "Assembled by a validator" (`:55-56`) names no shape for the cell map, the variants, the
  readings or the attempts. `variants.render` returns free text (`variants.py:188-206`). The result file can
  be validated by shape and then copied by bytes; one field, `engine`, is a free value from a scan sidecar
  (`sa3_score.py:357`) and needs a pattern.
- **Fixed texts** (the label, the sentences of M10) should be constants reviewed before the pin.

Section 5's open points: print the three means and intervals in the first lines, under the label; a reader
should not have to open JSON. Publish the per-repo values; they are declared outputs and hold no path or
label. I found nothing in the listed outputs that should be withheld.

**Test:** a schema test per section; the planted-marker test over every public file; a test that the
deviation table in the report equals the committed file.

---

## Minor

1. **Clone with `--no-hardlinks` [run].** A plain local clone hard-linked 22 object files of the throwaway
   source: it changes link counts in the main repository and ties the clone to it. Test: no file under the
   clone's `.git/objects` has more than one link.
2. **The named commit must be reachable from a branch**, or the clone will not hold it and the checkout
   fails. Say which path is cloned (either works).
3. **Check `sealed_at_commit`.** `verify --after-lock` checks the nine hashes only (`seal.py:163-174`). The
   job should also require the lock's `sealed_at_commit` to equal `--commit`. Test: a lock with another
   commit stops at step 5.
4. **Fix the exact command and environment of steps 4 and 6**: the interpreter and flags of the placebo stage
   (`/usr/bin/python3 -I -B`), `LAWS_LINGUIST_DIR` bound and set (without it `laws_units.py:57-67` tries the
   network and the run dies), the same thread variables as the sealed `runtime`. Take a runtime fingerprint
   in the same layout before step 6 and compare it with the seal's.
5. **Reason codes are promised (`:82-83`) but not listed.** At least: `locked` (the reference's exit 2,
   `sa3_score.py:345-352`), `score_crashed`, `score_timeout`, `no_result`, `result_invalid`, `ledger_refused`.
6. **The terminal.** The reference prints the means at the end (`sa3_score.py:501-506`). Say whether the
   owner sees them on the terminal or only in the report. I suggest the report only, with its label.
7. **Line 36 is right but short.** With no `.git` at all `lock` writes real hashes and an empty commit
   (`DECISIONS.md` item 23). Step 5 plus minor 3 cover both cases.
8. **What is committed afterwards, and by whom**: the result, the lock file, the report, run-2's public
   files, the ledger receipt. One commit, after the run, by a session, from the public directories only.
9. **Section 4's test list** lacks: the B1 and B2 tests; a decoy where git works but one file is dirty
   (`lock` must refuse, exit 2, and the job must stop at step 4, not 5); the whole job in a fresh
   interpreter with Enter typed on a pseudo-terminal, as the owner job's test 8 does.

---

## Proposed order of operations

| # | who | what | commit |
|---|---|---|---|
| 1 | session | Revise this spec; the owner accepts the failure table (M10) and the definition of "once" (B2) | spec commit |
| 2 | session | Build `tools/scoring/`, any real-mode change in `tools/compare/`, the tests, the fixed report texts, and `docs/sa3_deviation_table.md`. Decoys only | **K1** |
| 3 | another session | Independent build review; fixes. The review names the tree hash of `tools/` | **K2** |
| 4 | session | Predictor-side tables and predictor-side input check on real data (no label). Commit the verdict and the table hashes. Not all-equal: stop and investigate | **K3** (documents only) |
| 5 | session | Enter the second erratum **and** the reading note in `docs/sa3_registration.md`; update the consolidated text; mark both drafts entered. Run every test file once more. Check `git rev-parse K2:tools` equals this commit's | **C** — the pinned commit |
| 6 | session | Push C. Tag it (annotated) and push the tag. Give the owner C, both commands, the time estimate and the stopping codes, in a message, not in a commit | none |
| 7 | owner | `prepare.py --real --i-am-the-owner`, protected `run-2`, at C. Must print `PASS`, placebo `bytes_equal` | none |
| 8 | session | Diff run-2's seal against run-1's, from the public files: exactly the five leaf values of M3. Nothing is committed | none |
| 9 | owner | The scoring job at C: `--commit C --seal <run-2>/seal.json`, in `tmux`, same day, no package updates | none |
| 10 | session | One commit: result, lock file, report, ledger receipt, run-2's public files | **R** |

Rules that make it hold: every sealed-file change is in C or earlier; all code is final and reviewed before
C; HEAD is C at steps 7 and 9; nothing is committed, and nothing on the machine is updated, between them.
Steps 4 and 5 can swap. Step 2 can come after step 5 if the owner prefers the documents entered first; then
the "no sealed file may change" rule simply starts earlier.

Inside step 9, the order I propose: verify the seal → fresh clone → clone against seal → copies (hashes
against the seal) → `lock` → `verify --after-lock` and the commit in the lock → loader rehearsal on all 40 →
ledger `started` → **`score`** → ledger `completed`, result published, receipt → label tables and label-side
check → comparison scorer and cell map → corrected readings, named streams, variants → report. Everything
before the ledger entry stops on failure. Nothing after it does.

---

## What I did not check

- Nothing was run on real data, and no SA3 tool, harness or job was run at all. The sandbox test used a
  hand-written bwrap command in `sandbox_ro`'s bind order, not `sandbox_ro.py` itself.
- The run-time estimate is arithmetic from one public run log. It could be wrong by a factor of three
  either way.
- Whether a write-ahead database with an empty `-wal` opens from a read-only bind on this SQLite build. I
  rely on the owner job's own decision to copy.
- Whether the real loader will pass on the 20 repos of M7. That is the point of the rehearsal.
- I read `tools/compare/scorer.py`, `input_check.py`, `variants.py`, `harvest_variant.py` and `tables.py`
  for their entry points, guards and data paths, not their arithmetic. I did not read `cellmap.py`,
  `derive.py`, `streams.py`, `reading_b.py`, `decoy_study.py`, `blind_runner.py`, `tracker_keys.py`, or most
  of `placebo_check.py` and `reading.py`. I read `docs/process/owner_job_spec.md` only where it mentions the
  lock; I relied on the built code, its README and DECISIONS.
- No test file was run. I did not check that the existing tests still pass after the documents are entered.
- The wording of the two documents to be entered was read, not reviewed.
- Git behaviour was tried on git 2.43.0 only, on small throwaway repositories with no submodules and no
  large files.
- The owner's global git configuration beyond `core.autocrlf` and filters, as seen from the worktree.
