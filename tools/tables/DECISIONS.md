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
