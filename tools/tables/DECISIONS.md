# Stored tables, phase A: decisions the spec left open, columns left out, and what the spec gets wrong

`docs/process/tables_spec.md` is the brief. Numbers are from runs of 2026-11-14 (generator 1.3.0, seed 11,
`--years 10`, route `manifest`) under `/home/joe/.claude/jobs/24bf9d40/tmp/tables_build/` (not committed).

## Where it runs

1. **One stage of the harness, route `manifest` only.** `tools/harness/run.py --tables` sets `Ctx.tables` for
   route `manifest`; `tail()` then runs `tools/tables/build.py --repo NAME` after the probe, through the same
   `stage()` (bwrap and the in-sandbox guard). Nothing else in the harness changes; without `--tables` it runs
   exactly as before (`tests/test_harness.py`: 6 passed). The harness copies `tools/` into `WORK/tree`, so the
   stage is found at `tools/tables/build.py` there. A failed build is recorded as the stage's return code
   (`tables_rc`); the harness's own table is unaffected.
2. **The guard comes first.** `build.py` calls `sandbox.assert_inside` before importing any SA3 module (test 8 runs
   it outside: it stops with `SandboxError: refused`). `schema.py`, `canon.py`, `invariants.py` and `datacard.py`
   import no SA3 module and run anywhere.

## `file`

3. **The reason order.** The spec says its list follows "the order `laws_units` tries them", but `Excluder.why`
   tries vendored, documentation, generated, test, example (test is fourth, not first). The reason is decided in
   this order: (a) `language` — `laws_units.language_of(path)` not in `frame()["langs"]`, the first test of
   `sa3_outcomes.universe`'s `unit()`; (b) the verdict of `Excluder(attrs, include_tutorials=True).why(path,
   path in sidecar["generated"])`, built exactly as `universe()` builds it; (c) `not_in_archive`; (d)
   `not_scanned`; (e) `zero_loc`. `schema.REASONS` lists them in that order. Consequence: a file outside the
   repo's language is `language` even where a GitHub list also matches it (the base repositories' `docs/*.md`
   and `README.md` are `language`, not `documentation`).
4. **`tutorial` and `gitattributes` are attributions, not rules.** `why()` returns "example" for both example and
   tutorial directories and does not say whether `.gitattributes` decided. Both are read by calling the same
   function again: a verdict `example` that `Excluder(attrs, include_tutorials=False).why` does not give is
   `tutorial`; a verdict `vendored` or `generated` that `Excluder({}, include_tutorials=True).why` (no attributes)
   does not give is `gitattributes`. A path vendored both by its attribute and by a linguist pattern is
   `vendored` with the pattern (the base repositories' `vendor/thirdparty/`, matched by
   `(3rd|[Tt]hird)[-_]?[Pp]arty/`; the manifest names the attribute).
5. **`pattern`** is the first regex, in list order, of the Excluder's own compiled list (`ex.vendor` for
   vendored, `ex.docs` for documentation) whose `search` matches the path. It attributes a verdict `why()` has
   already given; it decides nothing. A `vendored`/`documentation` row without a pattern fails invariant 3.
6. **`history_can_touch` by running the history walk itself.** The walk's unit rule is a closure inside
   `laws_history.harvest`, so it cannot be called. Instead `harvest` is run unchanged on a scratch repository
   (under `WORK/tmp`) holding one root commit whose tree is the snapshot's tree (objects shared through
   `objects/info/alternates`), with the language and the C-family switch of the history's own `meta`
   (`units == "c+cpp"`); a path is touchable when that walk wrote a `touch` row for it. No unit logic is
   restated. Base repositories: 0 universe files untouchable; tests, vendored and other-language files untouchable;
   the export-ignored `experimental/` files and the generated file touchable (the walk applies no attributes and
   no first-5-lines flag).
7. **The tree, the archive, the scan.** The tree is `git ls-tree -r -z --full-tree <snapshot>` (bytes decoded with
   `surrogateescape`). `in_archive` reads the `git archive` stream with Python's `tarfile` rather than `tar -t`
   (which `universe()` uses and which quotes unusual names); the same for every control path. `scanned` = the path
   is in the scan's `file_data` after removing `src_root` exactly as `universe()` does; `loc` = `total_loc`, null
   when not scanned. Scanned paths that are not in the tree get no row; their count is `repo.scanned_not_in_tree`
   (0 in every run). `in_universe` is taken from `universe()`'s set, never from the reasons; invariants 2 and 3
   check that the two agree.

## `touch`, `event`, `pool`, `marginal`, `link`

8. **`touch` copies `sa3_outcomes.build`'s restriction** (lines 156-171): the frame's `where` clause on `commit_`,
   `ct` in (`window_start`, `end`] with `window_start` read from the outcome file and `end` from `frame()`, and the
   path in `universe()`'s set. Tree-wide commits are kept, as in that function's `touch` dict. `walk_pos` is the
   0-based position in `commit_` rowid order (the order `sa3_outcomes` reads the chain in); the spec's
   "first-parent position" is that only in a first-parent walk.
9. **`event.how` (spec: "own or inherited where the outcome file says").** The outcome file does not say: it
   gives each outcome's commits and files, and only counts of inherited events. `how` is set only where it
   follows from facts in the tables' inputs: `own` when the commit is not a merge in the history walk
   (`sa3_outcomes` gives inherited events only to merges), `inherited` when it is a merge with no row of its own
   in the body harvest's `link` table (an own event needs the commit's own links), and null otherwise. Counted in
   the data card (`event_how`). Base: 161 own; `merge_workflow`: 159 inherited, 0 null.
10. **`event` holds no KW column.** The outcome file gives KW's files and counts but no per-commit list (unlike the
    HP tiers and the control pool), so KW cannot be stored per (commit, path) without re-deriving it. Its
    `marginal` row is stored and not recounted.
11. **Invariant 6** recounts `n_files`, `n_commits` and the largest commit's share from `event` for HP,
    HP_allreverts, HP_revert, HP_cve and HP_fixref (tier rows count only with `hp = 1`, as the outcome file builds
    them), and `n_files`/`n_commits` of `control_pool` from `pool` (its `n_files` is the file's `n_files_any`).
    The share is compared within 0.0005 because the outcome file rounds it to three decimals. `clears_floor` is
    the outcome file's verdict, stored and not recounted: recounting needs the floor numbers.
12. **`link` has no resolved-target column.** `sa3_outcomes` resolves a revert's value inside `build()` (a nested
    `resolve`, unique 7-character prefix among commits reachable from HEAD); it cannot be called, `git rev-parse`
    is a different rule, and restating it would re-implement it. Identical `(sha, kind, value)` rows are one row
    with their count `n`; a NULL value would be stored as "" (none occurs).
13. **`measure`** holds, for every scanned path of the tree, the 16 `file_data` columns of `sa3_score.COLS`
    (`build.py` asserts the list equals `COLS[:-1]` at every build) and `amplified_cascading_flux` from
    `mitigation_telemetry` (the "branch-state value": registration section D); and `nest_max`, `nest_mean` for
    every universe file. `absent_means` states how `sa3_score.load` reads an absent value: a NULL column becomes
    NaN (`missing`); an absent telemetry key becomes 0 (`zero`; a telemetry string that does not parse is NaN, so
    `missing` on that row); a file missing from the nesting file stays NaN (`missing`). **Left out:** `in_degree`
    and `out_degree`, which the scorer derives by counting `fcall_data` rows (spec: raw measures only); phase B
    could store the raw edges instead.
14. **`touch` has no tree-wide flag**: deciding it needs the 10% / 20-file threshold; the outcome file gives only
    the count (`wide_commits`).

## Storage

15. **Canonical bytes** (`canon.py`): keys in schema order; `str` as a JSON string with every lone surrogate
    written as `\udcXX` (a non-UTF-8 path is held as a `surrogateescape` string, so the line stays valid UTF-8 and
    `json.loads(...).encode("utf-8", "surrogateescape")` gives the original bytes); `int` accepts a whole real;
    `bool` as 0/1; `real` as the `float.hex()` string, -0.0 written as 0.0, NaN and infinities refused; null for
    missing; separators without spaces. Rows sorted by the UTF-8 (`surrogateescape`) bytes of the key columns,
    column by column; a duplicate key is refused. Every key column is a string (checked by the schema at import).
16. **One file per build, never written over.** `<table>.<hash16>.jsonl` is written through a `.partial` name and
    renamed; an existing file of that name with identical bytes is accepted, with other bytes refused. A directory
    that already has an `index.json` is refused (one build per directory). If an invariant fails nothing but
    `build_failed.json` is written, and the exit code is 1.
17. **`index.json`**: per table its file, hash, rows, schema version and protected flag; the SHA-256 of every input
    file read (history DB, scan DB and its `-wal` file, sidecar, outcome file, body harvest, nesting file); the pool
    clone's tip, the snapshot, linguist's pinned commit; the SHA-256 of `tools/tables/*.py`; the known gaps. Input
    hashes differ between two runs of the pipeline (the engine's DB is not byte-stable); table hashes do not
    (test 5).

## The data card

18. **What it holds.** Counts, shares, Unix times and linguist pattern strings. It omits the repo name, the
    snapshot hash (although `snapshot` is not protected) and every directory name, so that no string from any
    table's key columns needs checking by hand. Shares are rounded to four places.
19. **Scan completeness against the tree**: over the tree's files whose `language` is one of the repo's (`langs`),
    the counts in the archive, scanned and in the universe, and every left-out file by its stored reason; the
    pipeline's own figure is printed beside it. Base: 387 files, 354 scanned (0.9147), 306 in the universe
    (0.7907), the pipeline's own 1.0. With `generic_dir_names`: universe 247 (0.6382), 83 vendored by reason,
    while the pipeline still reports 1.0.
20. **Largest directory.** The spec does not say which directory level. The card gives three (the file's own
    directory, the first path component, the first two) and, for each, the share of its files with no `touch` row
    in the window, plus the universe's untouched share. Added because on seed 11 the share alone does not reveal
    `vendored_half`: the base repository's largest two-component directory (`src/net`) already holds 0.562 of the
    universe, `src/contrib` under `vendored_half` holds 0.491. The untouched share does: 1.0 for `src/contrib`
    against 0.012 for `src/net`; universe untouched 0.494 against 0.0065.

## Tests

21. **Test 1, the causes of a difference** between `event` (HP) and the manifest's expected positives (labels with
    `counted: true` on first-parent units), per (commit, path): manifest-only: before the code's window start / after
    its end ("window offset"), touched under another path ("rename after the snapshot", confirmed from the
    manifest's path history), outside the universe; commit-level: a counted commit with no positive ("no file at
    the snapshot"); pipeline-only: after the manifest's window end, a revert whose target lies between the
    manifest's snapshot and the code's cut (counted as "window offset": the code's cut decides it, harness
    DECISIONS 32), or a label the manifest leaves ambiguous (listed apart, not a difference). Anything else is
    "UNEXPLAINED" and fails the test. The manifest side is read from the manifest alone; nothing is imported.
22. **Test 6** checks equality against every key string of the protected tables (a short `kind` such as
    `revert` is a substring of the outcome name `HP_revert`, so substrings cannot be the test for those), and
    substrings for every path and commit hash of the protected tables and every path of the tree, in both card
    files; and no 40-hex string at all.
23. **Test 7** reads the SA3 tools' source as text (`ast`, never imported): the registered numbers
    (`MAX_BROUGHT`, the floors, `MAX_COMMIT_SHARE`, `MIN_COMPLETE`, `WIDE_SHARE`, `WIDE_MIN_FILES`, `MERGE_SHARE`,
    `CUT_Q`, `WINDOW_DAYS`, `MIN_POSITIVES`), every `re.compile` pattern in `sa3_outcomes`, `mod1_lift`,
    `laws_history`, `hist_replicate`, `hist_meta`, `laws_units`, `hist_fixlabel`, `sa3_score`, laws_units' keyword
    sets, and linguist's cached lists; it fails if any appears in `tools/tables/*.py` (numbers as literals, patterns
    as substrings, words and linguist lines as string literals; the reason names, which are labels, are allowed).
    Test 1 uses 730 days for the manifest's window: that is the test, not the builder.

## What the spec gets wrong, leaves ambiguous, or asks for that cannot be had

24. "The order `laws_units` tries them" does not match the list given (item 3).
25. "Own or inherited where the outcome file says": the outcome file does not say (item 9).
26. "`marginal` ... compared with a recount from `event`" for every outcome: KW has no per-commit list (item 10),
    and `clears_floor` cannot be recounted without the floor numbers (item 11).
27. `link`'s "resolved target" cannot be had without re-implementing `resolve` (item 12).
28. "The branch-state value" is not named in the spec; read as `amplified_cascading_flux` (item 13).
29. Test 6 "no string from a protected table's key columns": the repo name is a key column of every table, and
    link kinds are substrings of outcome names (items 18, 22).
30. Test 2, `vendored_half`, "the largest-directory share shows it": not by the share alone on seed 11 (item 20).
31. Test 1 names three causes; two runs also need "ambiguous in the manifest" and the revert-target case of the
    window offset (item 21).

# Phase B: decisions `docs/process/tables_phase_b_spec.md` (Revision 2) left open, and what it gets wrong

Built and tested on decoys only (2026-11-14): seven control repositories (generator 1.3.0, seed 11, `--years
10`: Python and C base, `generic_dir_names`, `vendored_half`, `bot_merges`, `merge_workflow`, `mixed_language`)
run through the unmodified pipeline by the harness, plus six copies of the Python base (the review's four
imitated cases, and one carrying planted markers). Nothing was run with `--real`.

## Where it runs

32. **The launcher never looks at the study directory or the pool.** `phase_b.py` on the host names their paths
    to bwrap only (`--ro-bind-try`: a missing declared file is simply absent inside; the launcher stats nothing).
    Every read happens inside `tools/harness/sandbox_ro.py`'s sandbox, and every stage (`phase_b.py stage ...`,
    `silence.py stage`, `manifest_stat.py inside`) calls `sandbox_ro.assert_inside_ro()` first, before any SA3
    import and before any path is touched. The spec's "a guard, reading the kernel's mount table before touching
    any path, finds the study path and the clone mounted read-only" is this in-sandbox guard: on the host the
    study path is not a read-only mount, so a guard in the launcher could never pass. Test 1c runs the stage
    entry outside the sandbox under `strace` with the production paths: it refuses, and no syscall names
    laws-study, the pool, `/nvme-data` or `~/.blind`; in-process, the guard opens `/proc/self/mountinfo` and
    nothing else before refusing.
33. **The guard's conditions** (mount table and `/proc/net/dev` only): `/` read-only; each hidden root
    (`/nvme-data`, the projects root, home, `/tmp`) a read-only tmpfs; the study path and the pool path read-only
    tmpfs mounts; every mount at or under a hidden root read-only except exactly the declared read-write
    directories (`PHASEB_RW`), none of which may lie in a data root; the declared clone (`PHASEB_CLONE`) mounted
    read-only; no interface but `lo`. Test 1d binds a study file, a study directory, then the clone read-write
    (a test-only `unsafe_rw_for_tests` field) and the stage refuses each time (exit 3, nothing written).
34. **Mount order** (`sandbox_ro.bwrap_argv`): `--ro-bind / /`, `--dev /dev`, `--proc /proc`; `--tmpfs` over
    `/nvme-data`, `/srv/storage_16tb/projects`, `/home/joe`, `/tmp`; `--tmpfs` at the study path and at the pool
    path; `--bind` each read-write directory at its own path; `--ro-bind` the code; `--ro-bind-try` each
    declared input at its study path, the clone at `<pool>/<repo>`, GitHub's two lists under the hidden home;
    `--remount-ro` the six tmpfs mounts and `/dev`; `--unshare-net --unshare-ipc --unshare-pid --unshare-uts
    --die-with-parent --new-session --clearenv`; git with `GIT_NO_LAZY_FETCH=1`, `gc.auto=0`,
    `maintenance.auto=false`, no system config, `safe.directory=*`. **The engine export is not bound**: nothing in
    phase B runs it, and binding it would mean naming a laws-study path the job does not need.
35. **Read-write places**: per stage, its own scratch directory (`<scratch>/<repo>/<stage>/`, holding that
    stage's `HOME` with a private `.gitconfig`, `TMPDIR`, its result and its log); the tables stage also
    `OUT/<repo>/` (review m5: a later repo cannot touch an earlier repo's tables). OUT and the scratch directory
    must be new and under `~/.claude/jobs` or `/tmp` (the harness's rule).
36. **Terminal and logs.** The terminal gets `repo stage status` lines; each stage's stdout and stderr go to
    `<scratch>/<repo>/<stage>/stage.log`; OUT's `run_log.json` holds stages, return codes, a stage's own short
    reason, invariant numbers and counts, and the manifest's verdict. Phase B binds nothing outcome-side, so its
    logs cannot hold an outcome-side string (test 4g greps OUT, the scratch directory and the terminal for planted
    markers); they stay out of OUT all the same.

## Declared inputs, and what the SA3 functions need

37. **`frame()` needs the history database only** (`meta`: language, units, unit; `commit_`: ct, bot, merge). It
    does not read `dbs/` or `meta_mod1/` (those are `mod1_lift.measure`'s, which phase B does not call). No
    label-side input is needed for the cut or the window end. **`universe()` needs** the sidecar (`attrs`,
    `generated`, `src_root`, `snapshot`, `engine`), the scan database's `file_data` (`file_path`, `total_loc`),
    GitHub's two lists, and the clone only for its `git archive` (which gives `tree_unit_files` and `complete`).
    Importing `mod1_lift`, `sa3_outcomes`, `sa3_score` (either commit) and `build` opens nothing. Phase B uses
    from `frame()`: langs, merge_units, cut, end, usable_commits; from `universe()`: the file set and its three
    numbers.
38. **Per stage**: `preflight` and `copy` bind the originals (`history/R.db`, `sa3_scans/R.json`,
    `sa3_scans/R_master.db`, `sa3_nesting/R.json`, each database's `-wal`, `-shm`, `-journal` names) and, for
    preflight, the clone; `tables` binds the two database copies at the originals' study paths, the sidecar, the
    nesting file, the clone and GitHub's lists; `silence` the same without the clone, plus the stub at
    `sa3_outcomes/R.json`. Test 2c lists the study path from inside every stage of every rehearsal repo: exactly
    those names; never `meta_sa3`, `meta_mod1`, `dbs`, `sa3_tables`, a real outcome file or another repo.

## SQLite and git

39. **The copy.** In the `copy` stage each database is copied with its side files into scratch (plain reads; the
    original is never opened by SQLite), the COPY is opened read-write, checkpointed (`wal_checkpoint(TRUNCATE)`)
    and set to rollback mode (`journal_mode=DELETE`), and `quick_check` run. The tables and silence stages bind
    the converted copy read-only at the original's path, where a rollback-mode database opens with no side file.
    This handles every state of the review's table (M2) without skipping a repo: WAL clean with side files, no
    side files, frames in `-wal` with or without `-shm`, rollback mode; a hot journal is copied with it and rolled
    back on the copy. Test 3 builds each state and checks the copy's rows against the true content and the
    original directory's listing and stat. One state remains undetectable: a database moved without its `-wal`
    (rows lost at scan time). A `pool/<repo>` that is a symbolic link to a clone elsewhere is bound as its target
    (bwrap follows the source), mounted read-only, and covered by the manifest (test 8). `immutable` and `nolock` are never used. The preflight reads the header (bytes 18
    and 19) as bytes, and the side files' sizes. Originals are hashed (SHA-256, `index.json` `inputs_sha256`).
40. **The archive** is streamed (`tarfile` mode `r|` on `git archive`'s pipe, exit code checked; review M11),
    never held in memory. Phase A's `archive_paths` is unchanged and not used by phase B; on every control
    repository both give the same file table (test 4b). If `git archive` fails (a blobless clone: tree available,
    archive not), `in_archive` is null, the reason `not_in_archive` cannot be had and such a file shows as
    `not_scanned`, `repo.pipeline_complete` and `pipeline_tree_unit_files` are null, and count 4's registered
    figure is "archive unavailable", with `universe()`'s own `complete 0.0` printed beside it as "not a zero"
    (review M1). Nothing is fetched (`GIT_NO_LAZY_FETCH=1` and the read-only bind; test 4c: the blobless clone's
    pack list, reflog and config unchanged). `history_can_touch` still works on a blobless clone (alternates).

## The tables

41. **`repo.status` and `why`** come from the public, frozen marginals file (`docs/sa3_outcome_marginals.json`;
    for a decoy its `docs/`), the only outcome-derived values phase B reads; `pipeline_unit_files`,
    `pipeline_complete`, `pipeline_tree_unit_files` are `universe()`'s return values (the outcome file stores
    exactly that dictionary: `sa3_outcomes.build`, `out.update(u)`).
42. **`snapshot.window_start` = the later of `frame()`'s cut and the snapshot's commit time** (`git show -s
    --format=%ct`). This RESTATES one line of `sa3_outcomes.build` (Amendment 1 rule 10, as Amendment 5 section 5
    states it), which cannot be called: it runs only inside `build()`, after the label-side inputs. One difference:
    `build()` falls back to the cut when `git show` fails; phase B stores null. On every control repository it
    equals the outcome file's `window_start` (test 4f). The reviewer should decide whether this restatement is
    acceptable; the alternative is a null column and count 2 reported as the two times only.
43. **Invariants in phase B**: 1, 2, 3 and 8 stop the repo's tables (its counts are still written, with the
    failures' numbers and counts); 7 (the window) is reported and does not stop them, since it is count 3's
    subject (`PU_window_assertion`); 4, 5 and 6 need `touch`, `event`, `pool`, `marginal` and are not run. The
    messages go to scratch only; OUT gets number and count. `bot_merges` fails invariant 7 (1 row) and gets its
    tables, as phase A does not.

## The counts

44. **Count 2's 15 repos** are those the frozen marginals file marks drawn, `ok` and clearing the HP floor
    (review m6); every repo's count 2 is computed and the flag `drawn_ok_clearing_HP` marks the 15.
45. **Count 4, against the tree**: scanned files over the files of `git ls-tree` that pass the unit rule
    (language and `Excluder`: reasons null, `not_in_archive`, `not_scanned`, `zero_loc`), with every file of the
    repo's languages by stored reason beside it. Amendment 5 does not define "completeness against the
    snapshot's tree with stored reasons"; this is the registered ratio with `ls-tree` in place of `git archive`.
46. **Count 5**: a file of the repo's languages whose verdict is `vendored`, and which no rule excludes once the
    four patterns are removed from laws_units' own compiled list (`Excluder.vendor`, an attribute; no rule is
    restated), is "excluded only by" them; per pattern, those it matches; with scan rows. The four patterns are
    read from the registration's own `PU_generic_dirs_restored` row and checked, inside the sandbox, to be lines of
    GitHub's list: phase A's test 7 forbids GitHub's patterns as literals in `tools/tables/`.
47. **Count 6**: universe files with `history_can_touch` false; tree entries whose mode is not `100644`/`100755`
    (symbolic links, submodules), from `ls-tree`; `scanned_not_in_tree`. Nothing more (spec M8).
48. **Count 9**: per repo the number of `.gitattributes` texts, the longest in characters, how many are exactly
    200,000 (the sidecar's cut; a text of exactly that length cannot be told from a truncated one), and whether
    any reaches it.
49. **Count 10**: SHA-256 of GitHub's two lists as bound; linguist's commit in laws_units and in the history's
    `meta`; the history's unit rule and units (C family = `c+cpp`); engine id, hash seed and archive file count from
    the sidecar; the nesting file's grammar pack.
50. **Count 1.** `silence.extract` writes every `tools/*.py` as at `edc5c53` and at `8fb7fe0` into
    `<scratch>/code/<commit>/tools/` by `git show` (no lazy fetch, no gc; SHA-256 of each in
    `code_sha256.json`); only `sa3_score.py` and `sa3_outcomes.py` differ between the two, and the latter only
    inside `build()`. Each version's `load(repo, True)` runs from that copy in its own sandbox, with the stub at
    the outcome path; `silent` is called as that version defines it (one argument at `edc5c53`, two at `8fb7fe0`,
    told apart by `inspect.signature`). The stub has the real file's outcome keys with every list empty. Cells
    are (repo, measure) for every repo where `load()` runs; the (repo, outcome, measure) cells are the outcomes the
    frozen marginals file says clear the floor, by the scorer's own loop rule (non-primary predictors only on HP
    and KW), so no label is read. `SCORED_OUTCOMES` repeats `stage_score`'s loop tuple, which cannot be read
    without running it. The `8fb7fe0` column is checked automatically against `docs/sa3_placebo.json` (four
    primaries per repo). On the control repositories the stub and the real outcome file give the same value in
    every cell under both versions (test 5: 7 repositories x 23 measures x 2 versions).

## The manifest

51. **What it covers**: every declared input of every repo by its in-sandbox name, including the side-file
    names a database could grow, and every file and directory of each clone's `.git`, with type, size, mtime,
    ctime, inode, mode; each take in its own read-only sandbox, the "after" in a `finally`. A file created on the
    host beside the declared ones under another name is not seen (binding the directories would expose other
    repos and the label side). The manifests list clone object names, so they stay in scratch; OUT's run log
    holds counts and the verdict. Test 2a: a stage that tries to write to the study path, create a side file,
    `chmod`, write a pack or the reflog, open the original read-write with SQLite, `git gc`, `repack`, `fetch`,
    `update-ref`, `reflog expire`, `config` fails at every one and leaves the manifest unchanged; test 2b: changes
    made from outside (touch, a created `-wal`, chmod, an added pack, an emptied reflog) are each reported.

## Phase A changes

52. **`build.py`**: `main()`'s body split into `read_scan`, `file_table`, `measure_table`, `repo_row`,
    `snapshot_row` (`file_table` takes `arch` and `touchable`, either of which phase B may pass as None; phase A
    never does). At import the guard is chosen: with `PHASEB_SANDBOX=1` the read-only sandbox's, else the harness
    sandbox's as before; both before any SA3 import (test 7). The two-tier `SystemExit` no longer names the
    commit and path (review B1). **The nine table hashes are unchanged**: the original `build.py` and the new one,
    run inside the same harness sandbox on the same inputs, gave identical hashes for all nine tables on six
    controls (the seventh, `bot_merges`, fails invariant 7 under both); the Python and C hashes are recorded in
    `tests/test_tables_phase_b.py` (`PHASE_A`).
53. **`invariants.py`**: a failing `event` or `pool` row is reported as "invariant N: K rows of protected table
    T fail (rows not named)"; `touch` rows are still named (not protected). Test 6 plants rows with marker hashes
    and paths and finds them in no message, nor in phase A's `build_failed.json` and output.
54. **Phase A's test 4 updated (with the coordinator's leave, after review).** Plant 5 expected the old message
    naming `pool('r', '2222...', 'src/a.py')`; it now expects "invariant 5: 1 row of protected table pool fail
    (rows not named)" and asserts the planted hash and path are in no message. A new plant (an `event` row outside
    the universe with no touch row) checks invariants 4 and 5 the same way. No other plant changed.
55. **A literal spelt oddly**: `phase_b.py` writes the docs directory as `Path("docs/")`, because phase A's test
    7 forbids the bare word `docs` (one of laws_units' example-directory names) as a string literal in
    `tools/tables/`.

## What the spec gets wrong, leaves ambiguous, or asks for that cannot be had

56. "The phase A tests must still pass" and the required `invariants.py` change conflicted (item 54; resolved).
57. "A guard ... finds the study path and the clone mounted read-only" can hold only inside a sandbox (item 32).
58. The window start must be restated or left null: `sa3_outcomes.build` cannot be called without the label
    side (item 42). Count 2 depends on that choice.
59. "Expected ... the indicator and the nesting measures": only `nest_max` (a count) is affected by the narrowed
    rule; `nest_mean` is a continuous score and its rule did not change. On the control repositories
    `def_safety` (a count) also differs.
60. Count 4's "against the tree with reasons" is not defined (item 45); "cells" of count 1 are (repo, measure)
    for silence and (repo, outcome, measure) in Amendment 5 (item 50).
61. Rehearsal case 4, "a `.gitattributes` line ... written into the decoy's sidecar and tree": a line written into
    the tree is a new commit, so a new snapshot and a different decoy. It is written into the sidecar only (what
    `universe()` and the tables read). **Finding:** on the base repository, switching vendoring off for
    `vendor/thirdparty/` re-includes nothing: the frozen engine never scanned that directory, so its 24 files
    become `not_scanned`, the universe is unchanged, count 6 stays 0 and the registered completeness falls to
    0.927. A re-inclusion reaches count 6 only for a directory the engine scanned: on a copy of
    `generic_dir_names`, `**/cache/** -linguist-vendored` adds the 14 `cache/` files to the universe, count 6 = 14
    (the manifest's number), and those 14 have no nesting value (count 8 falls to 0.9464), since the nesting
    scan ran on the original universe. Likewise the engine never scanned the `dist/` files: count 5 gives
    `(^|/)dist/` 15 files excluded only by it, 0 with scan rows.
62. "The engine export read-only and never run": not bound at all (item 34).
63. Review M2's "non-empty `-wal` or a journal: skip the repo" is superseded by the copy, which reads both states
    correctly (item 39).
