# Review of `tables_phase_b_spec.md` — stored tables, phase B

Reviewer: Claude (independent session, 2026-11-14). Read-only on the worktree; this file is the only file
written. No real study data, corpus clone, pool or `~/.blind` path was opened, listed or statted. No SA3 tool,
harness or `tools/tables/build.py` was run. Experiments used throwaway data under
`/home/joe/.claude/jobs/24bf9d40/tmp/phaseb_review/` (`g/` git, `sq/` SQLite, `ov/` mounts, `c1/` the silence
rule, `inv/` invariants and hashes).

Each finding is marked **[code]** verified in code, **[run]** run under bwrap on throwaway data, or
**[reasoned]** reasoned, not run.

## Verdict

**Safe after changes. Not safe to run as written.** The read-only design does what it claims for damage: under
a bwrap read-only bind, every git and SQLite write I tried failed and left the files byte-, time- and
listing-identical, including the exact command that caused defect 49. The leakage side is not ready. As
written the job (1) prints and stores the paths and commit hashes of positive files when an invariant fails,
(2) publishes `touch`, which is the label with one regular expression left to apply, next to `measure`,
(3) cannot compute count 1 the way the spec says, and the obvious way round reads labels and predictors in one
process, and (4) targets the real data by default with no guard named. Each has a cheap fix with a test. The
job is also larger than Amendment 5 section 7 needs: nine of the ten counts need no outcome list, no link
table, no `touch`, and four of them no clone.

## Findings

### Blockers

**B1. A failed invariant names positive files. [code] [run on synthetic tables]**
`invariants.py` names the failing rows by key. Invariants 4 and 5 run over `event` and `pool`. `build.py`
lines 314–318 print every failure to stdout and write them to `build_failed.json` in the output directory. On
synthetic tables with one planted positive outside the universe the output was:
`invariant 4: event('r', 'abab…', 'src/secret/positive_not_in_universe.py'): path not a universe file`.
That is a labelled file and its fixing commit, in a public file and on the launching session's terminal. Up to
25 rows per invariant. `build.py` line 285 does the same through `SystemExit` ("… is in two exclusive tiers").
The spec says a failure is "reported … with the invariant's name and the row count". The code it reuses does
not do that. A failed invariant is the likeliest thing to happen on first contact with real data, and it is the
same kind of event as defect 26.
*Change:* in phase B, a failure that comes from a protected table carries the invariant number and a count
only. Row names go to a file outside the output tree, or nowhere. Stdout and stderr of each repo go to a file,
not the terminal; the terminal gets `repo, status`. *Test:* plant one violation of each of invariants 4, 5 and
the two-tier clash on a decoy; assert that no path or hash from `event`, `pool` or `link` occurs in any public
file or in captured stdout/stderr.

**B2. The command's default target is the real data, and no guard is specified. [code] [run]**
`phase_b.py --out DIR [--decoy DIR]`: leave the flag off and the target is real. Phase A's guard cannot be
reused: `sandbox.inside()` requires the study path to be `WORK/study` (same device and inode), which is false
for a read-only bind of the real directory. The spec names no replacement. Without a guard, a direct run opens
the real study directory read-write-capable. That is not harmless: I ran a `mode=ro` SQLite open of a WAL-mode
database in a writable directory and it **created `-shm` (32,768 bytes) and `-wal` (0 bytes) beside the
database and left them there**. The engine's scan databases are WAL mode (header bytes 18–19 are `2 2` in a
control decoy under `tmp/tables_build/`, with exactly those two side files). So "only reads" is false for
`universe()` outside a read-only bind.
*Change:* the real target needs an explicit `--real` plus an owner-made go-ahead file; with neither flag the
command exits 2 before bwrap is started. `phase_b.py` checks, before importing any SA3 module, from
`/proc/self/mountinfo` only: the study mount and every clone mount carry `ro`; root `ro`; the hidden roots are
read-only tmpfs; no interface but `lo`. It must never test read-only by trying a write. I confirmed mountinfo
shows `ro` per bound path. *Test:* no flags → exit 2 and a stub in place of bwrap is never called; guard
refuses when the study mount is `rw`; guard refuses outside a sandbox.

**B3. `touch` is not public in any honest sense, and nothing in the design stops it meeting `measure`. [code] [reasoned]**
What `touch` holds: for every commit in the window, which universe files it touched. The label is that table
restricted to commits whose message matches patterns that Amendment 5 section 5 prints verbatim. For a
non-merge commit that is one regex over the subject and body. So `touch` plus readable messages **is** the
label, exactly for own events and nearly for inherited ones. Without any message, `touch` joined to `measure`
gives the predictor-against-"touched in the window" association. Every positive file is a touched file. The
scorer's own registered comparison `minus_churn_any` is built from the same thing.
Is it worse than the history database? By content, no: `touch` can be rebuilt from the history database, the
scan and public rules. By access, yes. The history database sits in a directory every session is forbidden to
open and the sandbox hides. Phase B would copy its outcome-side content, already cut to the window and the
universe, into the directory sessions are told to read, keyed by the same `(repo, path)` as `measure`, under
the word "public". The careless join that defect 26 was becomes two lines.
What the blinding does and does not achieve here: it does not keep the label secret from a session that reads
history and messages; the label is a deterministic function of readable inputs and public code. It can only
(a) keep predictor and outcome out of one computation, and (b) keep outcome-side data out of easy reach. The
spec's test ("the card builder is given the public tables …") passes `touch` and `measure` to the same
function, so it enforces neither.
*Change:* three classes, not two: predictor-side (`repo`, `snapshot`, `file`, `measure`), outcome-side
(`touch`, `marginal`), protected (`link`, `event`, `pool`). No count in the spec needs `touch`; do not build
it in phase B. Build it in the owner-run job with the protected tables. *Test:* a non-interference test on a
decoy. Shuffle `measure` values among paths: every outcome-side output must be byte-identical. Shuffle `touch`
and `event` paths: every predictor-side output, and every one of the ten counts except 7, must be
byte-identical.

**B4. Count 1 cannot be computed "from `measure` only", and the obvious alternative reads labels. [code] [run]**
I read `silent()` at both commits and called both, each in its own process, on synthetic arrays inside a
sandbox with the study path absent. Findings:
- Silence does **not** depend on any outcome. `silent(x, p)` is called on the predictor over all universe
  files, before `design_for`. Missing values are dropped inside `silent`. This part of the spec is right.
- Its input is the scorer's **derived** predictor (`sa3_score.load`, the `x` dictionary), not a raw measure.
  `in_degree`, `in_degree_per_loc` and `out_degree` come from `fcall_data`, which `measure` does not hold
  (`DECISIONS.md` 13). `state_pointers_alloc` is a sum that carries missing through. The branch-state value
  reads absent as 0 and a bad JSON string as missing. Ten of the 23 predictors are counts, and the three
  un-silenced "count measures" of defect 46 are not named anywhere I could read. Rebuilding `x` from `measure`
  is a second implementation of `load`, and for three predictors it is impossible.
- The scorer's own `load()` gives `x` exactly, but it also reads the outcome file and builds every label vector
  in the same process. That is the thing the design exists to prevent.
- "The cells the scorer would score" depends on `clears_floor` (the frozen marginals file, already public)
  and, **after** silence, on the pair floor, which depends on the outcome and on which files lack a value. If
  the count reports "scored", it reads labels. It must report silence only.
- The two rules differ on more than 14 cells. On synthetic arrays `nest_max` and `risk_safety_nonzero` are
  silent at `edc5c53` and not at `8fb7fe0` whenever they are non-zero in 10% of files; those are the "two
  measures" Amendment 4 did disclose. The 14 are what is left after those two. The spec gives no expected
  value, so a builder cannot tell a right answer from a wrong one. "Cell" is (repo, measure) for silence and
  (repo, outcome, measure) in the spec; 14 is unreachable to check until that is fixed.
- The two commits' files cannot be "read from the two commits" inside the sandbox: the projects root, and so
  this repository's `.git`, is hidden. They must be extracted before, and their hashes recorded.
- Importing `sa3_score` at either commit is feasible. Module-level code only defines paths; with the study
  path absent both imports worked. Signatures differ: `silent(x)` and `silent(x, name)`.
*Change:* compute `x` by calling the `8fb7fe0` `load(repo, True)` unchanged, with its module global `OUTCOMES`
pointed at a stub directory holding an outcome file with empty lists. No label is read and no rule is
rewritten. Then call each commit's `silent`. Enumerate cells from the frozen marginals file. Publish
(repo, measure) with the outcomes it applies to, mark the two disclosed measures apart, and state the expected
remainder (14). *Tests:* on control repositories, `x` from the stub call equals `x` from the real `load`
element for element, missing positions included (the harness probe already has it). On real data there is one
known answer that reads no outcome: `docs/sa3_placebo.json` holds `silent` per repo for the four primaries
under the `8fb7fe0` rule; the count's `8fb7fe0` column must equal it.

### Major

**M1. `universe()` swallows a failed `git archive` and returns a different answer. [code] [run]**
Lines 82–86 never check git's exit code. I ran the same pipeline against a clone whose objects were out of
reach: git exited 128, the listing was empty, no exception. `universe()` then returns `tree_unit_files = 0`
and `complete = 0.0`; the file set is unaffected. The same family: `sa3_outcomes.build` line 164 falls back to
the cut when `git show` fails, so a stored `window_start` equal to the cut may be an artefact of an unreadable
clone at build time. *Change:* phase B never uses `universe()`'s second return value. It runs its own archive
with the exit code checked, and compares snapshot time against the cut itself (count 2). *Test:* point the
decoy at a clone with its objects hidden; the job must record "archive unavailable", not 0%.

**M2. Whether a scan database opens under a read-only bind depends on leftover side files. [run]**
SQLite 3.45.1, Python `mode=ro`, bwrap read-only bind:

| state of the database | read-only bind | writable directory (every SA3 reader so far) |
|---|---|---|
| rollback mode, clean | works | works |
| rollback mode, hot journal | error "attempt to write a readonly database" | same error |
| WAL, no side files | **error "unable to open database file"** | works, **creates `-shm` and `-wal`** |
| WAL, `-shm` and empty `-wal` left by an earlier `mode=ro` reader | works | works |
| WAL, frames in `-wal`, `-shm` present | works, sees all rows | works |
| WAL, frames in `-wal`, no `-shm` | error | works |
| WAL, frames in `-wal`, opened with `immutable=1` | **silently returns the old rows (100 of 250)** | same |
| WAL file moved without its `-wal` | error | **silently returns 100 of 250** |

Nothing was written in any read-only case. So the bind fails safe. But the rehearsal passes for a reason that
may not hold on real data: decoys carry the residue because phase A just read them. A real scan database
whose `-shm` was ever cleaned up or not copied will fail. The tempting repair, `immutable=1`, gives stale
data without an error. *Change:* a preflight inside the sandbox, per database, before any query: header bytes
18–19, and the presence and size of `-journal`, `-wal`, `-shm`. Non-empty `-wal` or a journal: skip the repo
and tell the owner. WAL with no `-shm`: skip and tell the owner; do not work round it. Forbid `immutable` and
`nolock`. *Test:* the table above, as a test.

**M3. The protected tables do not belong in this job. [code] [reasoned]**
Mode 700 does nothing against a session: every session runs as the same user. It stops other Unix users and
nothing else. What the copy does do is put the labels, per (commit, path), in a second place that is not
forbidden and not hidden by the sandbox, under the same root as files sessions are told to read. A recursive
`grep`, `ls -R` or `**/*.jsonl` reaches them. "Nothing new is revealed" is true of content and false of
exposure. Only count 7 needs any of it. *Change:* phase B writes no `link`, `event` or `pool`. They are built
in the owner-run job, into a root on the sandbox's hidden list. *Test:* after a decoy run, no file under the
output root contains a key from the decoy's outcome file.

**M4. The before/after hash check adds little as specified and misses what went wrong last time. [run] [reasoned]**
Inside a read-only bind the job cannot change the files, so hashing them from inside mostly proves the bind
works, which the sandbox tests already prove. What it does add: a ledger of inputs for the external seal, and
detection of a change made by something **outside** the sandbox during the run (a timer, a worker, another
session). What it misses:
- **the corpus clones**: the spec hashes only the study directory. Defect 49 was a clone.
- files created or deleted, which a list of hashes of files that existed before does not show;
- a crash: an "after" taken by the job itself never runs if the job dies;
- an edit that restores the modification time. Change time catches it: I reset a file's mtime to itself and
  its ctime still moved.
Access times do not move under a read-only bind (run: a file with an old atime kept it after a read through
the bind, and lost it on an ordinary read).
Cost: SHA-256 here runs at 2 GiB/s, but `/srv/storage_16tb` is a rotational disk, so the disk sets the pace,
roughly 2–4 minutes per 30 GB per pass if sequential. Not risky, but "every file it is allowed to read" is the
whole study directory if the whole directory is bound, and I could not look at how big that is. It also means
the hashing process reads every label file.
*Change:* the launcher, not the job, takes a stat manifest (path, size, mtime, ctime, inode, mode) of every
bound path, clones' `.git` included, before and after, each in its own small sandbox call so the "after" runs
even on a crash. Content is hashed once, as each input is read. Bind declared files only (M5). *Test:* during
a decoy run, from outside, touch a file, create a file, chmod a file, add a pack to the clone; each must be
reported.

**M5. The spec binds the whole study directory; its parent specs say declared inputs only. [code] [run]**
`research_codebase_spec.md` section 5 and Amendment 5 section 2: "only the declared inputs bound in". Phase B
binds "the real study directory". That puts MOD-1's files, every other harvest and every outcome file within
reach of code that needs six files per repo. I ran file-level binds into an empty tmpfs directory: a WAL
database bound with its two side files opens and reads correctly, and everything else is absent. *Change:*
per repo, bind only the files that repo's step declares. *Test:* inside the sandbox the study path lists
exactly the declared names.

**M6. Six of the 46 repos are `scan_incomplete`; phase A's code gives them no tables and no counts. [code]**
The public marginals file lists 40 `ok` and 6 `scan_incomplete`. For those the outcome file has no `outcomes`
and no `window_start`. `build.py` then fails invariant 6 ("marginal row for HP is missing") and invariant 7,
writes `build_failed.json`, and stops. Counts 3, 4 and 5 are wanted most for exactly these repos. A repo with
no sidecar or no history raises an uncaught exception in `universe()` or `frame()`, not `build_failed.json`;
"the run continues" is then false unless each repo is its own process. *Change:* the spec states, per status
(`ok`, `scan_incomplete`, `no_meta`, `unprepared`), which tables and counts are built and which invariants
apply. *Test:* a decoy of each status (delete scan rows; delete the harvest; delete the sidecar).

**M7. The partial-clone fallback rests on data that does not exist, and names the wrong failure. [code] [run]**
The spec: "its `file` table is built from the scan and the archive listing the scan sidecar already holds".
The sidecar holds `archive_files`, a number (`sa3_scan.py` line 75; confirmed on a control decoy). There is no
listing. And on a blobless clone, the kind in defect 49, I ran both with `GIT_NO_LAZY_FETCH=1`:
`ls-tree -r` **works** (12 of 12 paths; trees are present); `ls-tree -r -l` and `archive` **fail** ("could
not fetch … from promisor remote"), archive on the first `.gitattributes` blob. So the real case is "tree
available, archive unavailable": `in_archive` and the reason `not_in_archive` cannot be had, and applying
export-ignore by hand would be a rule written twice. Phase A's `history_can_touch` method does work against a
blobless clone through alternates (run). *Change:* state three clone states (full; tree only; neither) and
what each yields; in "tree only", `in_archive` is null and count 4's new measure is marked "archive
unavailable". *Test:* make a blobless clone of a control repository over `file://` (it needs no network) and
rehearse on it.

**M8. Count 6 "by cause": three of the four causes are undefined, and the code sees only one. [code]**
Phase A derives `history_can_touch` by walking a one-commit copy of the snapshot's tree. That finds unit-rule
differences (the `.gitattributes` re-inclusion, the generated flag, the C-family switch). It cannot find the
others. A path spelled differently never gets a `file` row at all; it lands in `scanned_not_in_tree`.
`tree_paths()` drops the mode, so a symbolic link or submodule entry looks touchable. "Reachable only off the
first-parent chain" is a property of commits, not of a file at a snapshot; a merge's first-parent diff carries
the change. The rehearsal plants only the first cause. Amendment 5 asks only for the total. *Change:* publish
the total and the first cause now; define the other three as rules, each with a planted control case, before
they are published. *Test:* one control mutation per cause with a known count.

**M9. Phase B cannot call phase A's builder, and may not edit it. [code]**
`build.py` runs `SB.assert_inside(HARNESS_WORK)` at import and is one 200-line `main()`. The rules forbid
editing it. So the builder must copy it. "Hash for hash equal to phase A" then tests the copy against the
original, which is useful, but two builders now exist and will drift. *Change:* allow one listed refactor:
`build.py` exposes `build_tables(repo, paths)`; the guard is passed in. *Test:* phase A's 14 tests pass and
every table hash in the two base repositories is unchanged.

**M10. Count 7: what it tells, and what it cannot compute. [code] [reasoned]**
*Leakage.* It reads no predictor and names no file. A session could compute it from readable messages and the
printed pattern. It does tell more than the marginals: the share of a repo's qualifying commits that are of a
suspect kind, and so whether a repo near the floor would drop under `PU_tracker_keys_case_sensitive` (two
scored repos are within five commits of the 20-commit floor in the public file). That is knowledge about the
label, not about its relation to any predictor. My judgement: publishable, as Amendment 5 promises, but by the
letter of the spec's own test ("something … the existing public marginals do not") it does; the owner should
see that sentence before deciding. Either way it must run as its own step, because it is the only reason
anything in this job would open the link table.
*Method.* (a) "Lower-case" cannot be tested with the pattern: phase A's test 7 forbids any SA3 pattern in
`tools/tables/`. The stored value works instead: a tracker key is the only `issue_fix` value containing a
hyphen. That is still a rule and must be written down. (b) "Only" needs to know a revert did not qualify;
`link` has no resolved target. `event.tier == issue_fix` with `hp = 1` says it. (c) Trailers are stored under
their own kinds and count as fix references in the outcome builder; they must be counted as "another link".
(d) For a merge, the linking commit is not recorded, so the count is undetermined for inherited events.
Seven of the 15 confirmatory repos are merge-workflow. *Change:* publish per repo "own events: n; inherited
events: m, not determined". *Test:* planted commits covering: lower-case key only; lower-case key plus `#N`;
lower-case key plus a `Fixes:` trailer; lower-case key plus an unresolved revert; a merge inheriting one.

**M11. What the rehearsal cannot tell. [code] [reasoned]**
"Hash for hash" is achievable: the decoy is built by the harness (which runs the outcome builder) and phase B
then only reads it. But a pass says little about:

| real condition | can a control repository imitate it? | otherwise |
|---|---|---|
| earlier-eight: snapshot after the cut | yes, the supplied-snapshot route already offsets the window | — |
| `scan_incomplete`, no harvest, no sidecar | yes (M6) | — |
| merge workflow | yes, `merge_workflow` exists | count 7 undetermined part (M10) |
| C-family with `.h`, C and C++ together | C base exists; I did not check a C++ case | assert `units` is one of the known values |
| partial clone | yes, blobless clone over `file://` (M7) | — |
| clone with alternates or a worktree link | yes (I built both) | preflight, below |
| WAL side-file state | only if the test removes the residue (M2) | preflight |
| clone tip moved since the history was walked; snapshot object gone | partly | compare `pool_tip` with `history_head`; fail the repo |
| non-UTF-8 or quoted paths | add one file to the generator | `scanned_not_in_tree > 0` fails the repo |
| very large repos | no | fail safe, below |
| outcome files rewritten after the leak (defect 44) | no | compare `marginal` with the frozen file; report count of differing cells |

Very large repos: `build.py` line 105 holds the whole `git archive` output in memory and then copies it into a
`BytesIO`. For a tree of several gigabytes that is twice that in RAM, on a box shared with other workers. The
3,600 s timeouts raise an exception nothing catches. *Change:* stream the archive (`tarfile` mode `r|` on the
pipe); a memory limit on the sandbox; a timeout becomes a recorded per-repo failure. *Test:* both methods give
the same set on every control repository; peak memory on a synthetic 2 GB repository stays flat.

**M12. The data card: "the counts below and nothing else" contradicts the card that exists. [code] [run on synthetic tables]**
`datacard.compute` already holds the marginals, row counts of the protected tables, own/inherited counts, and
three "share of the largest directory's files untouched in the window" figures. The last is computed from
`touch` and paths. On synthetic tables it read `share 0.5, untouched 1.0`: the largest directory is nameable
from the public `file` table, so this says every file in it is a negative under every outcome. For half a
universe of imported code with distinctive predictor values that is coarse information about the relation the
study tests. It is not one of Amendment 5's counts. *Change:* phase B's card holds the ten counts only; the
untouched shares move to the owner-run job. *Test:* the non-interference test of B3.

### Minor

**m1. "Bound read-only, one repo at a time" is enough for safety, not for correct answers. [run]** With only
the clone bound, a clone that borrows objects through `objects/info/alternates` fails `ls-tree` ("not a tree
object") while `rev-parse HEAD` still succeeds; a linked worktree fails everything ("not a git repository").
Both are clean failures in `build.py`'s checked calls and silent in `universe()` (M1). Preflight inside the
sandbox: `.git` is a directory; no `alternates`; no `commondir`; note `extensions.partialclone`.

**m2. Lazy-fetch protection, three layers, each run.** This git is 2.43.0 and does honour
`GIT_NO_LAZY_FETCH=1`. Without the variable but under the read-only bind, the fetch was attempted and died on
"Unable to create temporary file … Read-only file system"; the clone's listing was unchanged. On a writable
copy the same command took the pack count from 4 to 52, which is defect 49 reproduced. `git gc` and
`git fetch` under the bind failed on their lock files. The sandbox test should assert the variable is honoured
rather than assume it, since that depends on the git build.

**m3. Unsalted hashes of protected tables are a guess-checker. [run on synthetic rows]** `index.json` publishes
the SHA-256 of `event`. With 300 window commits and a marginal of 2 qualifying commits, I recovered the exact
event table and its positive files in 43,863 guesses. Infeasible blind for 20 or more commits, but it confirms
any reconstruction from messages exactly. For SA3 that is small beside B3. For the blinded study the hash
needs a key the owner holds.

**m4. Writable places are unspecified. [code]** "The output directory is the only writable place", yet the
method needs a scratch git repository, Python and SQLite temp files, a `HOME` with a git config, and GitHub's
two lists (hidden with home). If the lists are missing `laws_units` tries `mkdir` and a network fetch; both
fail cleanly in the sandbox (reasoned). Say where each lives.

**m5. One sandbox per repo. [reasoned]** Binds are fixed when bwrap starts, so "one repo at a time" means one
sandbox per repo. Bind only that repo's output subdirectory read-write, or a later repo's step can alter an
earlier repo's tables.

**m6. "The 15 drawn repos" is not defined in the spec. [code]** In the public marginals file, 38 repos are
drawn; 15 is drawn and `ok` and clearing the HP floor. Say so, and take the list from the frozen file.

**m7. Count 9. [code]** `attrs` is a dictionary, one text per `.gitattributes` file. The cut is 200,000
characters after decoding with replacement, not bytes. A text of exactly 200,000 cannot be told from a
truncated one. Report per repo: files, longest length, how many are exactly 200,000.

**m8. Count 10. [code]** The harvest's flags are in the `meta` table of the database that holds the links.
Read them in the count-7 step. The history's own `meta` records the linguist commit; include it.

**m9. The sandbox tests check hashes and modification times. [run]** Add change times, and a listing, so a
created file or a reset mtime is caught.

**m10. The run log is an output. [code]** "What may leave the job" lists files. Stdout, stderr and tracebacks
also leave (`KeyError` on a hash, the `SystemExit` messages). See B1.

## Leakage, one row per count and per public output

"Predictor-side" means computable from scans, the tree and rules, with no outcome, link or touch.

| item | reads | can it tell a session which files are positive, or a predictor–outcome relation? | verdict |
|---|---|---|---|
| count 1, silence under two rules | predictors; frozen marginals for which cells exist | no, **if** computed without `load`'s labels and without the pair floor (B4) | publish after B4 |
| count 2, window start equals cut | history, snapshot time | no | publish |
| count 3, window, usable commits | history | no | publish |
| count 4, completeness, two measures | tree, archive, scan | no | publish |
| count 5, files excluded by four patterns, with scan rows | tree, scan | no | publish |
| count 6, universe files history cannot touch | tree, rules | no; it must stay rule-based and never use "has no touch" | publish total and cause 1 (M8) |
| count 7, lower-case-key-only commits | link, event, messages | no file, no predictor; says more about the label than the marginals do | publish, own step, owner informed (M10) |
| count 8, share with a nesting value | nesting file | no | publish |
| count 9, `.gitattributes` length | sidecar | no | publish |
| count 10, how inputs were made | sidecars, `meta` | no | publish |
| table `repo` | history, sidecar, outcome scalars (`status`, `why`, `complete`) | no | public |
| table `snapshot` | history, clone, outcome scalar `window_start` | no | public |
| table `file` | tree, scan, rules | no | public |
| table `measure` | scan, nesting | predictors only | public |
| table `touch` | history, cut to window and universe | **yes**: with messages it is the label; with `measure` alone it is the activity relation | not public; not built in phase B (B3) |
| table `marginal` | outcome file | already public as a committed file; 33 outcome cells have 1–5 positive files, harmless without `touch` | public; report differences from the frozen file as a count |
| `index.json` | hashes, row counts | protected-table hashes confirm a guessed label (m3); `event` row count is a new marginal | drop protected hashes from phase B |
| data card, existing fields | `touch`, `event` | untouched share of the largest directory marks a nameable group all-negative | remove from phase B (M12) |
| `build_failed.json`, stdout | invariants over `event`, `pool` | **yes**, names positive files and commits | fix first (B1) |
| `protected/` | outcome file, harvest | holds the labels; mode 700 is no barrier to a session | not built in phase B (M3) |

## SA3 functions the job would call, and what they do under a read-only bind

| function | opens | subprocesses | under a read-only bind |
|---|---|---|---|
| `mod1_lift.frame` | `history/R.db`, `mode=ro` (rollback mode) | none | reads; writes nothing |
| `mod1_lift.ro` | any database, `mode=ro` | none | rollback: fine; WAL: needs `-shm` present, else clean error (M2) |
| `sa3_outcomes.universe` | `sa3_scans/R.json`; `R_master.db` (WAL) | `git archive SNAP` piped to `tar -t` | reads; archive failure is **silent**, `complete` becomes 0.0 (M1); needs no clone for the file set |
| `laws_units.Excluder`, `linguist_patterns` | GitHub's two lists in the cache under home | none; on a missing list `mkdir` and an HTTPS fetch | lists present: reads; absent: clean error |
| `laws_units.language_of`, `Excluder.why` | nothing | none | pure |
| `build.py` `tree_paths` | — | `git ls-tree -r -z --full-tree` | works; works on a blobless clone; clean error without objects |
| `build.py` `archive_paths` | — | `git archive`, whole output in memory | works on a full clone; clean error on a blobless clone; memory (M11) |
| `build.py` `history_touchable` → `laws_history.harvest` | scratch repo and scratch database under `TMPDIR` | `git init`, `rev-parse --git-path`, `commit-tree`, `update-ref`, `rev-list`, `log -M --name-status` | writes only under `TMPDIR`; clone untouched, blobless included (run) |
| `build.py` other git calls | — | `git show -s --format=%ct`, `git rev-parse HEAD` | work; need commits only |
| `build.py` reads | outcome JSON, nesting JSON, `meta_sa3/R.db`; hashes each input and `-wal` | none | reads; **the outcome and link reads are what phase B should not do** |
| `sa3_score` import at either commit | nothing at import | none | feasible with the study path absent (run) |
| `sa3_score.silent` | nothing | none | pure |
| `sa3_score.load` | history, sidecar, scan database, **outcome file**, nesting file | via `universe()` | reads labels; use the stub of B4 |
| not called, for contrast: `sa3_outcomes.build` | deletes and rewrites `meta_sa3/R.db` through `hist_meta` | `hist_meta.py`, `git log`, `git show` | would fail on the first write; the spec is right to exclude it |

No call in this list writes to a clone or to the study directory under the bind. In every read-only run the
before and after listings (name, size, mtime, ctime, mode) were identical.

## Is the job larger than it needs to be? Yes

Inputs each count needs:

| count | history db | sidecar | scan db | nesting | clone | outcome file | link db |
|---|---|---|---|---|---|---|---|
| 1 | ✓ | ✓ | ✓ | ✓ | — | — (stub) | — |
| 2, 3 | ✓ | ✓ | — | — | commits only | — (compare snapshot time with the cut) | — |
| 4 | ✓ | ✓ | ✓ | — | tree and archive | — (or two scalars) | — |
| 5 | ✓ | ✓ | ✓ | — | tree | — | — |
| 6 | ✓ | ✓ | ✓ | — | tree | — | — |
| 8 | ✓ | ✓ | ✓ | ✓ | — | — | — |
| 9 | — | ✓ | — | — | — | — | — |
| 10 | `meta` | ✓ | — | `pack` | — | — | `meta` only |
| 7 | ✓ | ✓ | ✓ | — | — | ✓ | ✓ |

The smallest safe job is two steps.
**Step 1, predictor-side:** build `repo`, `snapshot`, `file`, `measure` and counts 1–6 and 8–10. Bound per
repo: the history database, sidecar, scan database with its side files, nesting file, the clone. No outcome
file, no harvest. If the stored `window_start`, `status` and `complete` are wanted, a separate ten-line
extractor reads the outcome file and emits those top-level scalars only; its test asserts the output holds no
path and no hash.
**Step 2, count 7 and the harvest flags:** its own sandbox with the harvest database and the outcome file
bound; output is two integers and three flags per repo.
`touch`, `marginal`, `link`, `event`, `pool` wait for the owner-run job, which needs them for Amendment 5
section 9 layer 1.

How to test this proposal: the non-interference test of B3 passes trivially for step 1, because nothing
outcome-side is bound; assert that by listing the study path from inside step 1's sandbox.

## What I did not check

- Anything about the real data: whether real scan databases have their side files, a non-empty `-wal` or a
  journal; whether any real clone is partial, shallow, borrows objects or is a worktree; sizes; whether mount
  points sit inside the study directory. All of these are for the job's preflight to find.
- Whether the engine checkpoints its database before `sa3_scan.py` moves the main file alone. If it does not,
  rows were lost at scan time and nothing now can show it. I could not read the engine.
- I did not run the harness, phase A's tests, or any SA3 tool; phase A behaviour is from reading code and from
  finished control outputs under `tmp/tables_build/`.
- The control-repository generator's code: what mutations it can already make is taken from the specs.
- `blinding_spec.md`, `harness_spec.md`, and `research_codebase_spec.md` outside sections 4, 5 and 12.
- `tar -t` name quoting against `tarfile`, on odd paths.
- Read speed of the 16 TB disk; the hashing estimate uses a typical figure for a rotational disk.
- Overlay mounts as a stronger tripwire: this bwrap (0.9.0) has no overlay option, so I dropped the idea.
- Other processes that write into the study directory or the pool while the job runs (timers, workers). The
  stat manifest of M4 would show them; I did not look for them.
- Which three count measures and which 14 cells defect 46 means; that needs the real scans.
