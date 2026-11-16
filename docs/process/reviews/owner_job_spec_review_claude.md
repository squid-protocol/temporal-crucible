# Review of `owner_job_spec.md` — the owner-run preparation job

Reviewer: Claude (independent session, 2026-11-14). Read-only on the worktree; this file is the only file
written. No path under laws-study, `/nvme-data`, the clone pool, `temporal-crucible-tables` or `~/.blind` was
opened, listed or statted. No SA3 tool, harness or phase B job was run, and no SA3 module was imported.
Experiments used throwaway data under `/home/joe/.claude/jobs/24bf9d40/tmp/ownerjob_review/`: `rx/` (a copy of
the `hist_meta.py` patterns on made-up messages), `np/` (the placebo arithmetic, copied as text, on synthetic
arrays), `sq/` (SQLite side files, with one bwrap read-only bind of a throwaway directory), `ord/` (order and
size experiments).

Each finding is marked **[code]** verified in code, **[run]** run on synthetic data, or **[reasoned]** reasoned,
not run. Paths are relative to the worktree.

## Verdict

**Safe after changes. Not safe to build as written.** I found no output of this job that would hand a session
a predictor-outcome estimate; on that central point the design holds. It is not ready on four other points.
(1) The protected tables and every stage log can only be written where sessions work, and the reused phase B
launcher copies exception text into the public log; one such exception in the reference loader carries a file
path from the outcome file. (2) The closed list of public outputs is a test of file names, not a mechanism;
nothing checks what is inside them. (3) The tracker-key count cannot be computed from `link` and `event` as
defined for any merge-workflow repo, which is 7 of the 15 confirmatory repos, and two builders would publish
different numbers. (4) Layer 1 cannot fail on real data, and the tables it blesses lose two things the
reference scorer reads: the order of commits in the outcome file, which decides the matched-control draws, and
the keyword outcome's files. The job is also larger than Amendment 5 needs before scoring: only the count and
the seal are required by its order of operations, layer 2 is worth keeping, and the label tables with layer 1
should wait for the comparison scorer's specification.

## What blinding this job does and does not preserve

Said plainly, because the spec half-says it. The label rule is public code. The commit messages, histories
and clones are readable by any process running as the owner's user. So the label is not a secret, and nothing
this job does can make it one. A session that broke the rules could rebuild every outcome file exactly. What
can still be preserved is narrower, and it is what matters:

- no number that sets a real predictor against a real outcome reaches a session before scoring;
- no per-file or per-commit outcome data lands in a place sessions read as a matter of routine;
- no debugging on real outcomes (defect 26 was a debugging habit, not a design choice).

The job as specified keeps the first. It does not keep the second (B1). It keeps the third only by a sentence
("a failure is not investigated on real data") with nothing behind it (B2, M6).

## Findings

### Blockers

**B1. Outcome-side text has three ways out, and the protected directory has nowhere safe to live. [code]**
- `sandbox_ro.check_rw` accepts a read-write directory only under `~/.claude/jobs` or `/tmp`
  (`tools/harness/sandbox_ro.py:57`, `65-74`). The spec forbids changing that file. So the protected tables,
  which hold every positive (commit, path) pair, must be written under the directory every session uses for
  scratch work, or under `/tmp`, which does not survive a reboot. Mode 700 stops other Unix users and no
  session (phase B review, M3).
- Phase B's launcher writes each stage's stdout, stderr and traceback to `<scratch>/<repo>/<stage>/stage.log`
  and its result to `result.json` beside it (`tools/tables/phase_b.py:461`, `467`). Scratch is under the same
  two roots. In phase B that was harmless because nothing outcome-side was bound. Here the stages read labels.
- The same launcher copies a stage's `reason` into the public run log (`phase_b.py:405`, `578-579`, `594`,
  `610`). The reason is `f"{type(e).__name__}: {str(e)[:300]}"`. In the reference loader, the lists of the
  outcome file are indexed without a guard: `d["hp_commits"] = {s: [ix[p] for p in v] ...}` and the same for
  the pool (`tools/sa3_score.py:120-121`). The assertion two lines above covers the `files` lists only. If a
  file a control commit touched is no longer in the universe, the exception is `KeyError('<that path>')`, and
  its text is the path. The reference outcome builder has the same shape with a commit hash
  (`tools/sa3_outcomes.py:203`). A first run on real data is exactly when this happens.

*Change.* (a) One listed change to `sandbox_ro.py`: a third allowed read-write root that exists only for this
job, under home (so every sandbox hides it) and named in the session rules as forbidden, for example
`/home/joe/.sa3-owner/`. (b) Every stage's run directory, log, result and scratch lives inside it. (c) The
public directory is bound into no sandbox. (d) A stage's failure is reported outside as the exception's type
name and the stage name, never its message; `jobcore.py` already does this (`tools/blind/jobcore.py:145-165`).
*Tests.* On a decoy: plant a control-pool path that is not in the universe and a revert whose target is
missing; assert the marker path and hash appear in no file outside the protected root and not on the
terminal. Assert `check_rw` accepts the new root only for this job and that a phase B sandbox cannot see it.

**B2. The closed list is not enforced by anything. [code]**
The spec's protection is "a test asserts the list is closed" plus a planted-marker test. That checks file
names, and checks content only for the strings the decoy happens to plant. Nothing checks content on the real
run. The existing guard in `tools/blind/jobcore.py` cannot be reused whole: `guarded_call` blocks `subprocess`
and `sqlite3` (`jobcore.py:59`), and the stages here need `git archive` and SQLite. Its output check is also
too weak for this job: it passes any string of up to 64 characters (`jobcore.py:183-185`), which admits a
40-character commit hash or a short path.

*The smallest change that makes a stray path or hash impossible rather than unlikely:* stages cannot reach the
public directory or the terminal at all (phase B's `--new-session` and `stdout=log` already give the second;
B1(c) gives the first). The launcher, outside the sandbox, reads one `result.json` per stage and passes it
through a validator with a closed schema: a fixed key set; values are integers, booleans, or a word from a
closed list per key (`equal`, `not equal`, `not determined`, stage names, exception type names from a fixed
list, else `other`); a 64-hex string only under the seal's named keys; one finite real under the layer 2
difference key; repo names only from the frozen marginals file, matched against the pattern at
`phase_b.py:554`. No free text anywhere. Anything else: the public file is not written and the report says
"a stage returned an undeclared output" with a count.
*Tests.* A stage stub that returns, in turn, an extra key, a path in a string field, a list, a 40-hex string
in a verdict field, and a marker on stdout: each time nothing reaches the public directory or the terminal.

**B3. The tracker-key count is not computable as defined, and is defined loosely enough to give several numbers. [code] [run]**
What a stored link row holds (`tools/hist_meta.py:59-83`): `extract_links` puts every fix-reference value in
one set and stores each as `(sha, "issue_fix", value)`. The value is the first non-empty capture group of the
match, so:

| alternative of `issue_fix_sa3` | stored value | can it be told from the value? |
|---|---|---|
| 1: `#N`, `GH-N`, `bug N`, `bpo-N`, `PR N` | the digits only; the prefix is not kept | digits only: cannot be told from 3 |
| 2: tracker key | the key as written, case kept: `utf-8`, `JIRA-123` | **yes**: it is the only value with a hyphen |
| 3: `GnuPG-bug-id: N` | the digits | digits only |
| 4: `Fixes: <hash>` | 7 to 40 hex characters, case kept | hex with no hyphen |

I checked "has a hyphen ⇔ alternative 2" on 27 made-up messages against `m.lastindex` of the pattern, and on
200,000 random values drawn from each alternative's capture class: no exception. Case is kept, so "contains a
lower-case letter" is `value != value.upper()`. So the alternative **is** recoverable from the stored rows for
the one case the count needs. And if the pattern is re-applied, `m.lastindex == 2` gives the alternative
directly, so "calling the reference module's own compiled patterns" does work. Importing `hist_meta` is safe:
its module level only compiles patterns and names a path (`hist_meta.py:29-56`).

That is not the hard part. "Qualifies **only** because of" is. What the spec's definition cannot settle:
- **Inherited positives.** In a merge-workflow repo the qualifying link is on a brought-in commit, not on the
  unit commit that has the `event` row. Neither `event` nor `link` records which brought-in commit gave the
  merge its positives (`tools/tables/build.py:66-68`). So for those commits the definition has no answer. 7 of
  the 15 drawn repos that clear the primary floor are merge-workflow (counted from
  `docs/sa3_outcome_marginals.json`).
- **Trailers.** `Fixes:`, `Bug:` and `Reported-by:` are stored under their own kinds and turned into fix
  references later (`sa3_outcomes.py:183-184`). "Fix utf-8 decoding" with a `Fixes: the decoder` line in the
  body has a second qualifying link. So does a body line `Fixes: utf-8 handling`, which is both a lower-case
  key and a trailer [run]. The spec does not say trailers are "another link".
- **Reverts.** A revert qualifies only if its target resolves and existed at the cut. `link` has no resolved
  target (DECISIONS 12). `Revert "Fix utf-8 decoding"` whose target is late qualifies through the quoted key
  alone; with an early target it does not need the key.
- **An upper-case and a lower-case key together**: two rows; qualifies without the lower one [run].
- **The third integer** ("at least one lower-case key beside another qualifying link") inherits all of the
  above.
- One edge where stored links and a re-applied case-sensitive pattern differ [run]: `Fixes: deadbeef-1` in a
  **subject**. Case-insensitive, alternative 2 takes it as a key; case-sensitive, alternative 4 takes
  `deadbeef` as a hash. Rare; state it and move on.

*Proposed definition, computable, with no rule rewritten.* The count is a difference between two runs of the
reference outcome builder:

> A = commits under HP when `sa3_outcomes.build(repo)` is called unchanged on the sealed inputs.
> A′ = the same call with a copy of the harvest in which every row with `kind = 'issue_fix'`, a hyphen in
> `value`, and `value != upper(value)` has been deleted.
> **The count is the number of commits in A and not in A′.**

`build()` returns the outcome dictionary and writes nothing (`sa3_outcomes.py:139-316`; `main()` does the
writing). It handles merges, trailers, reverts, CVEs, the cap and bots as the frozen code does, because it is
the frozen code. It needs the clone (`topology`, `files_of`), the history, the sidecar, the scan copy and the
harvest copy, all read-only. Two guards: the copy must keep its `meta` rows, or `harvest_bodies` tries to
delete and re-harvest it (`sa3_outcomes.py:49-60`; under a read-only bind that fails, safely); and where
`git archive` fails on a partial clone `build()` returns `scan_incomplete` with no outcomes (phase B review,
M1), which must be reported as "not determined", not as zero.
Publish per repo: A (already public), the count, and two check bits: "A equals the stored outcome file's HP
commits, as a set" and "the hyphen rule agrees with the pattern re-applied to the stored messages" (the
number of disagreements, expected 0). Drop the third integer, or define it for own links only and say so.
*Tests.* A decoy with one planted commit each of: lower-case key alone; with `#N`; with an upper-case key;
with a `Fixes:` trailer; with a CVE; a late revert quoting a lower-case subject; an early revert doing the
same; a merge inheriting a lower-case key from one brought-in commit; a merge inheriting it from one and `#N`
from another; a merge over the cap; a bot's brought-in commit. Known answer for each. The self-test of the
hyphen rule calls `hist_meta.RX` and `extract_links` themselves, so **the build needs no copy of the
patterns**; my experiment used a copy only because I may not run the tools.
*A cheaper cross-check, own events only:* tier is `issue_fix`, no fix-semantic trailer row, every `issue_fix`
row has a hyphen and a lower-case letter. It restates which trailers count, so it is a check, not the count.
In the repos that are not merge-workflow the two must agree.

**B4. Layer 1 cannot fail on real data, and the label tables lose two inputs the reference scorer reads. [code] [run]**
- `event` and `pool` are built from the outcome file's lists and nothing else (`build.py:320-341`). Comparing
  them with those lists tests the encoder. Phase A already tests the encoder hash for hash on decoys, and
  invariant 6 already recounts `marginal` from `event`. On real data this comparison is true by construction.
- "The stored `file` table against `universe()` now": phase B built the table by calling `universe()`
  (`phase_b.py:310`). The comparison can detect that the sidecar, the scan database, GitHub's lists or
  `laws_units.py` changed since phase B ran, or that phase B's output was altered. It cannot detect a wrong
  universe rule: both sides are the same rule (defect 56). The seal's hashes, compared with the
  `inputs_sha256` phase B stored, say the same thing more cheaply.
- **Order.** The matched control picks commits by their **position** in the outcome file's `commits` objects:
  `hp, pool = list(d["hp_commits"]), list(d["pool"])`, then `rng.choice(len(pool), K)` indexes that list
  (`sa3_score.py:300-315`). The outcome builder fills those objects by iterating a set of hashes
  (`sa3_outcomes.py:226`, `282-292`, `309-310`), so their order follows Python's hash seed at build time and
  is fixed only by the file's bytes. The stored tables sort rows by key (`tools/tables/canon.py:93-101`) and
  have no position column (`schema.py:70-73`). On synthetic data the same pool in two orders gives different
  control vectors from the same seed. So a comparison scorer reading `event` and `pool` cannot reproduce the
  reference's `minus_control`, which decides "defect-specific" against "tracks activity". Layer 1, comparing
  **sets** of pairs, would print "equal".
- **The keyword outcome.** `event` holds no KW rows and no table holds KW's files (DECISIONS 10;
  `build.py:71-72`). The reference scores KW for all 23 predictors (`sa3_score.py:371`). A scorer reading
  tables cannot.

So a pass at layer 1 would be read as "the comparison scorer sees what the reference sees", and it is not
evidence of that. What a real layer 1 has to compare: the arrays the reference's own `load()` returns
(`paths`, `loc`, each `y`, `hp_commits` and `pool` **as ordered lists**, each `x`) against the arrays the
comparison scorer's loader builds from tables, hashed, per repo and per item. That needs the comparison
loader, a position column and a KW table, which is a schema change the spec rules out ("phase A's table
hashes unchanged").
*Change.* Take the label tables and layer 1 out of this job and into the comparison scorer's specification.
Until then say the honest thing: "the tables are a re-encoding; equality is by construction and is tested on
decoys". If anything of layer 1 stays, keep only the comparisons that have an independent side: `marginal`
against the committed marginals file (it can show an outcome file rewritten since publication, defect 44, but
only if a count moved); invariant 5 (every outcome pair has a touch in the history's window); and B3's
"rebuild equals stored" bit, which is the strongest of the three.
*Tests.* For the order claim: a decoy whose pool object is written in two orders must give two different
reference `minus_control` values; a layer 1 worth the name must then print "not equal" for the table built
from either.

### Major

**M1. Layer 2, "run from a copy so that it writes there", is underspecified and the easy build fails at the last line. [code]**
- `stage_placebo` reads outcome files: **yes**. It calls `load(repo, with_predictors=True)` for every repo
  that clears the HP floor (`sa3_score.py:233`, `239`). `load` reads all six `files` lists, HP's `commits`
  and the pool's `commits` (`119-121`), and every predictor. It uses only `y["HP"]`, the paths, LOC and the
  four primaries. It is the first process to hold real predictors and real labels together. Its outputs are
  label against hash placebos and size surrogates, never against a real predictor.
- It writes one file, `DOCS / "sa3_placebo.json"` (`285`), and prints per-repo lines of the same content.
  `ROOT` is `Path(__file__).resolve().parent.parent` (`34`). So a copy at `X/tools/sa3_score.py` writes to
  `X/docs/`. Three consequences the spec does not state: `X/docs/` must exist; it must hold a copy of
  `sa3_outcome_marginals.json`, which `scored_repos()` reads from `DOCS` (`77`); and it must be writable,
  while phase B binds code read-only and binds read-write directories **before** code
  (`sandbox_ro.py:126-129`), so a writable `docs/` inside a read-only code tree is covered by the later bind.
  The write is the last statement after all the computing. Bind `X/tools` as the code and `X/docs` as the
  read-write directory.
- It does not use the shared stream: a fresh `default_rng(2982)` per repo (`247`). Repo order from the
  marginals file sets only row positions and key order. Within a repo the four primaries share that stream in
  a fixed order.
- It shells out, through `universe()`, to `git archive | tar -t` on each clone and throws the result away
  (`sa3_outcomes.py:82-86`; `load` ignores the second return value). So layer 2 does not need the clones for
  its answer. Binding them costs a full archive of each snapshot and adds the only route to a clone. Say
  which is intended; the confirmatory run should do the same.
- Running from a copy changes no hash the reference `lock` expects: `lock` hashes files under whichever root
  it runs from, and an identical copy has identical blob hashes.
- Determinism [run]: I copied `bands`, `Design`, `hash_placebo`, `fit_size_model` and `draw_surrogate` as
  text and ran them on three synthetic repos of 2,500, 9,000 and 30,000 files. The output bytes and all 45
  fitted coefficients were identical across `OPENBLAS_NUM_THREADS` 1, 2, 4 and 12, across runs, and across
  hash seeds. **That says less than it seems**: on this machine numpy is linked to Debian's reference BLAS and
  LAPACK through `/etc/alternatives` (`ldd` of `_umath_linalg`), which has no threads. Random-number
  consumption cannot depend on thread count; the generator is not threaded.
*Change.* State the layout, the binds, whether clones are bound, and that the comparison runs inside the
sandbox and returns a verdict. *Test.* The decoy run; plus a run with `docs/` read-only, which must fail
before the first repo is loaded, not after the last.

**M2. No rule says what a layer 2 mismatch means, and there are at least four causes that cannot be told apart on real data. [code] [reasoned]**
A byte match can be expected **if** the committed file was written by the committed code from today's inputs
on this machine. That is not known. `docs/sa3_placebo.json` was last committed in `8fb7fe0`, the same commit
that changed the scorer and the outcome builder (`git log -- docs/sa3_placebo.json`), and defect 44 records
outcome files rewritten after the leak. A mismatch can mean: an input changed; the file was written by the
code as it stood before that commit's last edit; a library changed; or the copy's layout differs. "Within
1e-9" does not separate these cleanly: a last-bit change in a fitted coefficient can flip one surrogate draw
(`rng.random(n) < p`, `sa3_score.py:222`), which moves an effect by about one pair in the pair count, far more
than 1e-9. And the consequence is not small: the confirmatory run reads the **committed** file's `valid` gate
and `surrogate_mean` (`sa3_score.py:353-356`, `400`), and `docs/sa3_power.md` is derived from it.
*Change.* Decide now, in the spec, what each outcome of layer 2 leads to: bytes equal; integers equal and
reals within tolerance; integers differ. For the last, the owner needs a stated next step that is not
"look". Report integer fields (`n`, `positives`, `pairs`, `silent`) as equal or not, apart from the largest
difference among reals; one mixed "largest absolute difference" is dominated by a pair count.
*Test.* On a decoy: change one label (integers differ), change one predictor value (reals differ), change
nothing (bytes equal); each must land in its own class.

**M3. The seal hashes files that change when read, and not the bytes the run reads. [run] [code]**
- "Its scan database (with side files)". On a throwaway WAL database, one ordinary `mode=ro` read in a
  writable directory changed the `-shm` file's SHA-256 and left the database and `-wal` unchanged. On a
  cleanly closed WAL database the same read created `-shm` and an empty `-wal`. Every SA3 reader outside the
  sandbox opens these files that way (`mod1_lift.py:45-46`). So a seal over `-shm`, or over "which side files
  exist", fails after any such read between sealing and scoring, with nothing wrong. Under a read-only bind
  the three files were unchanged [run].
- The job copies each database, checkpoints the copy and sets it to rollback mode (`phase_b.py:200-209`),
  then binds the copy at the study path. The reference scorer would read the **converted copy**, whose bytes
  differ from the sealed original. The spec does not say how the seal reaches the copy.
- Hashed at one time, read at another. `seal.py verify` runs, then the inputs are bound and read. This box
  runs timers and unattended workers.
*Change.* Seal the database and its `-wal`; record `-shm` and `-journal` as present or absent, unhashed. Hash
what is read: copy every input into the protected root once, hash the copy's bytes, bind the copies, and
compare with the seal (`jobcore._read_sealed` does this for the blinded study, `jobcore.py:205-212`). For a
converted database add a content hash the conversion does not change (row dump of `file_data` and
`fcall_data` in key order) to the seal and check it after conversion.
*Tests.* Seal a decoy; read each database once with `mode=ro` outside the sandbox; `verify` must still pass.
Change one row through the `-wal` only; `verify` must fail. Change a file between verify and bind; the run
must stop.

**M4. The import recorder is the right closure for Python and misses everything else the run loads. [code] [run]**
- Python: every import in the reference scorer's closure is at module top level, and `stage_score` imports
  nothing `stage_placebo` does not. The closure is `sa3_score`, `sa3_stats`, `mod1_lift`, `sa3_outcomes`,
  `laws_units`, `_engine`, `hist_replicate`, `label_cascade`, `label_card`, `hist_fixlabel`, `fixlike_v2`,
  `laws_history` (read from the import lines; not run). So recording at the placebo stage is sound for
  Python.
- Five of those twelve are not named in Amendment 5 section 1 (`_engine`, `hist_replicate`, `label_cascade`,
  `label_card`, `fixlike_v2`), so "a check that it equals the reference contents of section 1" has no
  reference for them. None has changed since `8fb7fe0` (`git log 8fb7fe0..HEAD`, checked). `hist_meta.py`
  **is** named in section 1 and is **not** loaded: the scorer never imports it. A builder following the spec
  would seal neither group against a reference. Name `8fb7fe0` as the reference for the whole closure, and
  seal `hist_meta.py` by name.
- `stage_score` shells out to `git hash-object` (`sa3_score.py:42-43`, `349`), which the placebo stage never
  does. Both stages run `git archive` and `tar` (`sa3_outcomes.py:82-83`). Neither binary is "loaded from
  `tools/`".
- "numpy and its linear-algebra library": here the library is whatever `/etc/alternatives/libblas.so.3`
  points at. Installing OpenBLAS would change the arithmetic without changing numpy's version [run: `ldd`].
- Read by path at score time and not in the spec's list: `docs/sa3_lock.json` (M5). In the list: nesting
  files, the marginals file, the first scored repo's sidecar (`sa3_score.py:357`).
- Not captured at all: environment variables the code reads (`EXPOSURE_POOL`, `LAWS_LINGUIST_DIR`,
  `GITGALAXY_PATH`, `tools/_engine.py:18-33`, `laws_units.py:57`), thread-count variables, the hash seed, the
  sandbox launcher's own code.
*Change.* Record the file each module was actually loaded from and hash those bytes; record the resolved path
and SHA-256 of the python binary, of every shared object in `/proc/self/maps` at the end of the placebo
stage, and of `git` and `tar`; record the environment the sandbox sets. *Test.* A decoy run with a second
BLAS selected through an environment override must change the seal.

**M5. The reference `lock` rewrites a file after the seal, and its own check passes when git fails. [code]**
`stage_lock` writes `docs/sa3_lock.json` (`sa3_score.py:520`); `stage_score` reads it (`344-352`). The file
does not exist today. A seal taken before `lock`, which is Amendment 5's order, cannot contain it. And
`blob()` returns an empty string when git fails (`42-43`); inside a sandbox with no checkout, `lock` records
empty hashes at commit `''` (defect 57) and `score` then compares empty with empty and proceeds. So the
reference seal can be vacuous exactly where the confirmatory run is meant to happen.
*Change.* The external seal carries the nine expected blob hashes, computed without git (SHA-1 of
`blob <length>\0<bytes>`), and the scoring job checks, after `lock` and before `score`, that the lock file
holds those nine values, each 40 hex characters. Seal before `lock`; check the lock against the seal after.
*Test.* On a decoy run `lock` where git cannot find a checkout: the check must refuse.

**M6. The owner cannot tell a pass from a fail, and nothing says what happens after a partial run. [code] [reasoned]**
- No overall verdict is defined. "A repo whose stage fails is recorded and the run continues" — is the seal
  then written? Is that run a pass? Is "within tolerance" a pass? The owner has to decide alone, because the
  one party that could explain the report may not look at the protected directory.
- Partial runs. Phase B refuses if the output or scratch directory exists (`phase_b.py:531-533`); phase A's
  builder refuses if `index.json` exists (`build.py:256-258`). The spec says neither applies nor what
  replaces them. After a crash the protected root is half written and the public directory has no report.
- "Prints and waits for Enter" with no terminal: a session's shell gives end-of-file, and what happens then
  is unspecified.
*Change.* (a) Each run gets a new numbered subdirectory in both roots; nothing is ever written over; an
append-only ledger in the protected root records every start and finish, as `jobcore.py:345-348` does.
(b) The public report is written last, atomically, and always: a crashed run leaves `INCOMPLETE` with the
last stage reached. (c) One top line, `PASS`, `FAIL` or `INCOMPLETE`, from a rule written in the spec, with
the failing checks listed by name. (d) The real run requires standing input to be a terminal and a typed
phrase, not Enter. (e) Before the run the owner gets one page: the expected number of repos at each status;
the decoy run's time; which lines are measurements with no right answer (the count) and which are checks;
what each failure means and the next step for each; and two rules — do not paste anything from the protected
root into a session, do not re-run to "see if it passes".
*Tests.* Kill the job during the third repo: the report says `INCOMPLETE`; a second run uses a new
subdirectory and the first is intact. Run with standing input closed: exit 2 before bwrap starts.

**M7. The count will not include the commits Amendment 5's own example names. [run]**
Amendment 5 section 5: "Case is ignored, so 'Fix UTF-8 decoding' and 'fix x86-64 build' are fix references".
`UTF-8` in capitals matches the key pattern **with or without** case being ignored. With the case-sensitive
variant, "Fix UTF-8 decoding", "Fix SHA-1 …" and "Resolves: PROJ-42" all still match; only keys with a
lower-case letter drop out. So the published count, and `PU_tracker_keys_case_sensitive`, measure "keys
written with a lower-case letter", not "technical terms mistaken for tickets". A reader will take it for the
second. The spec's test plants only lower-case subjects, so it would not show this.
*Change.* The report states in one sentence what the count leaves in. Whether a second count is wanted is
the owner's decision and would be a dated addition. *Test.* Plant "Fix UTF-8 decoding" on the decoy; the
count must not move, and the report's sentence must say so.

**M8. Amendment 5's seeded-fault test is missing, and cannot be met as worded. [code] [reasoned]**
The spec says it covers the order of operations through step (f). Step (e) is section 9's test: five copies
of the code with one seeded fault each and five clean copies; "all three layers must flag each faulty copy".
The spec's tests mutate inputs, never code. And as worded the requirement cannot be met: layer 1 compares
inputs and cannot see a fault in the scorer; layer 2 exercises only the placebo path, so a fault in the Holm
step or the control draw passes it. What does flag every one-line fault is the seal's comparison of each code
file with its reference contents.
*Change.* Say which check is expected to flag which class of fault (seal: any change to a sealed file;
layer 2: a fault on the load and placebo path, or in the environment; layer 3: the rest), and run the
five-and-five test against that table. The wording in the amendment needs a dated correction.

**M9. Two of the four parts are not needed before scoring. [code] [reasoned]**
By Amendment 5 section 2's order: (d) needs the count; (f) needs the seal; (g) is the run. Layer 2 is not
ordered before scoring by the amendment, but it is the only evidence available beforehand that this code, on
these inputs, in this sandbox, reproduces a known output, and it is cheap. The reference scorer reads no
stored table, so the label tables and layer 1 are needed only by the comparison scorer and by the
sensitivities that name "the stored links". Building them now puts a second copy of every label on disk
before scoring, for a check that cannot fail (B4), in a schema that cannot serve its purpose (B4).

| part | needed before scoring? | recommendation |
|---|---|---|
| tracker-key count | yes, step (d) | keep; redefine as in B3 |
| the seal | yes, step (f) | keep; M3, M4, M5 |
| layer 2 | not ordered, but valuable | keep, in the sandbox layout the scoring job will use; or make it the scoring job's first step after `verify` |
| label tables, layer 1 | no | move to the comparison scorer's specification |

*How to test the smaller job:* list the protected root after a decoy run; it holds logs, copies and the
ledger, and no table.

### Minor

**m1. Three public items are new marginals of the label, and none is needed in public. [run] [reasoned]**
The row counts of `event` and `pool` are sums over commits of files per commit; the public marginals give
files and commits but not that sum. The stat manifest gives the byte size of each outcome file. On synthetic
data (300 window commits, 2 qualifying), the public marginal left a median of 5,147 of 44,850 candidate
label sets; adding the exact size left a median of 72. Size and row counts do not depend on order, so they
confirm a reconstruction; the SHA-256 mostly does not (m2). None of this relates an outcome to a predictor.
Phase B kept its manifests in scratch and published counts of differences only (`phase_b.py:569`,
`636-645`); do the same here, and keep protected row counts in the protected index.

**m2. The outcome file's SHA-256 is a weak guess-checker, by accident. [run] [reasoned]**
A session can compute candidate label sets, so in principle a public hash confirms "your reconstruction is
exactly right". In practice the file's bytes depend on the key order of its `commits` objects, which came
from set iteration under an unrecorded hash seed (B4): on synthetic data four hash seeds gave four hashes
for the same content at the same size. If the outcome files were built with a fixed, known hash seed this
protection is gone. Either way a confirmation gives a session nothing it could not get by running the public
code, so the hash may be published. For the later blinded study it needs a key (phase B review, m3).

**m3. The flag is a string.** `--i-am-the-owner` is as typeable as phase B's flag. With M6(d) and an
owner-made go-ahead file whose path sessions are told not to touch, a session would have to fake a terminal
on purpose. Still not a wall; say so in the same words as now.

**m4. The terminal rule contradicts the seal paragraph.** "The seal's own SHA-256 is printed" against "on
the terminal: stage names, repo names, ok or failed, the path of the report". Pick one; a hash on the
terminal is harmless but the list is meant to be closed.

**m5. Things two builders would write differently.** "The versions recorded below": none are. "The frozen
list": 40 `ok` repos, 20 that clear the HP floor, or 15 drawn among them (phase B review, m6). "Number by
number within 1e-9": absolute or relative; what if a key is missing; `power` is rounded to four places.
Which tables and checks a `scan_incomplete` repo gets (six have no outcomes). Where invariants 4 and 5 get
`file` and `touch` from. "With an import recorder": a wrapper that imports the module, or the script run as
`__main__`. The builder may not open phase B's real output directory, so `--phase-b` needs a decoy phase B
output and the spec should say the tests build one.

**m6. Two tests are weaker than they look.** Phase A's test 7 keeps SA3 patterns out of `tools/tables/`
(DECISIONS 23); nothing extends it to `tools/owner/`, where "never a copy" is now only a sentence. And the
marker test would miss a commit hash in the manifest of a clone's `.git`, where a loose object's name is
split by a slash; harmless here, but it shows the test proves less than "no hash anywhere".

**m7. The layer 2 sandbox binds twenty repos at once.** `sandbox_ro.Spec` has one `clone` field and the
guard checks one declared clone (`sandbox_ro.py:90`, `203-207`). Many clones can go in as plain inputs, as
`manifest_stat.take` does (`tools/tables/manifest_stat.py:69-70`); the guard still requires every mount under
a hidden root to be read-only. Say so, or the builder will ask for a change to `sandbox_ro.py`.

**m8. Layer 2 covers less than "the inputs".** A pass speaks for the universe, LOC, the HP file lists and
the four primaries of the 20 repos that clear the HP floor. It says nothing about the other 20 scored repos,
the other five outcomes, the commit lists, the pool, the 19 secondary predictors or the nesting files. The
report should say that in one line so that "layer 2: equal" is not read as more.

## Leakage: one row per public output

"New" means not derivable from `docs/sa3_outcome_marginals.json` and `docs/sa3_placebo.json`. In every row a
session that broke the rules could compute the item from readable inputs; the question is what the item
gives a session that keeps them.

| public output | which files are positive? | predictor-outcome relation? | new information about the label | verdict |
|---|---|---|---|---|
| tracker-key count, per repo | no | no | yes: the share of qualifying commits of one suspect kind; shows whether a repo near the 20-commit floor would fall under it | publish, as Amendment 5 promises; redefine (B3); owner told what it leaves in (M7) |
| "commits under HP in all" | no | no | no, it is the public marginal | publish |
| third integer | no | no | yes, small | drop or own-links only (B3) |
| layer 1 verdicts, per repo and tier | no | no | one bit each | harmless; but cannot fail (B4) |
| failed invariant: number and count | no | no | a count of outcome rows outside the universe or without a touch | publish |
| row counts of `repo`, `snapshot`, `file`, `measure`, `touch`, `link`, `marginal` | no | no | `touch`: window activity in total, computable from readable history | publish |
| row counts of `event`, `pool` | no | no | yes: files per qualifying commit, summed; an order-free check of a reconstruction | keep protected (m1) |
| layer 2 verdict | no | no | one bit | publish |
| layer 2 "largest absolute difference" | no | no; it is a difference between two placebo outputs, never a real predictor against an outcome | if integers differ, the size of a change in pairs or positives | publish, split into integers equal or not, and largest real difference (M2) |
| regenerated placebo file, if left in scratch | no | size surrogates and hash placebos against HP only, same class as the committed file | per-repo positives and pairs under today's labels | keep in the protected root (B1) |
| `seal.json`: predictor-side hashes, code, documents, clone heads | no | no | no | publish |
| `seal.json`: SHA-256 of each outcome file | no | no | confirms an exact reconstruction only if key order is guessed (m2) | publish |
| `seal.json`: SHA-256 of each link harvest | no | no | no | publish |
| stat manifest: label-side sizes and times | no | no | size is an order-free check of a reconstruction (m1); times show when a file was rewritten | publish the difference only; full manifests protected |
| stat manifest: clone `.git` entries | no | no | no | as phase B |
| `run_log.json`: stages, return codes | no | no | no | publish; **no reason text** (B1) |
| stage logs and results, if in scratch | **possibly**: an exception can carry a path or hash from an outcome file | no | yes | protected root only (B1) |
| terminal | as the run log | no | no | fixed words and validated repo names only (B2) |

## What I did not check

- Anything about the real data: whether real scan databases carry side files, whether the committed placebo
  reproduces, how many commits any pattern matches, whether any outcome file was built with a fixed hash
  seed, sizes, run times.
- Whether `sa3_outcomes.build()` finishes in reasonable time on the largest clones, and whether it
  reproduces the stored outcome files as sets. B3's proposal rests on both; the decoy rehearsal must show the
  second, and the first can only be learned on the real run, with a timeout that reports "not determined".
- The determinism test used copied arithmetic on synthetic arrays, not `stage_placebo` itself, and ran on one
  machine with a threadless reference BLAS. It is no evidence about OpenBLAS or another CPU.
- I did not import or run any SA3 module. Statements about the import closure come from reading import
  lines; a function-level import I missed in a file outside the closure I traced would not show.
- `tools/blind/` beyond `jobcore.py`; `blinding_spec.md`; `tables_spec.md` itself (invariants taken from
  `invariants.py`); the harness generator and whether it can already plant the merge and revert cases B3's
  test needs.
- Whether the scoring job, which is not specified yet, binds copies or originals, runs `lock` in a checkout,
  or writes `sa3_result.json` where `DOCS` points. M3 and M5 assume the shapes this spec implies.
- Other processes on the box that read or write the study directory between sealing and scoring.
- bwrap behaviour beyond one read-only bind of a throwaway directory.
