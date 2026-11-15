# The comparison scorer, part 1: decisions the spec left open, and findings

`docs/process/comparison_scorer_spec.md` (Revision 2) is the brief; `reviews/comparison_scorer_spec_review_claude.md`
supplied the verified facts it relies on. Runs of 2026-11-15 on decoys only, under
`/home/joe/.claude/jobs/24bf9d40/tmp/compare_build/` (not committed).

## Tables (section 1)

1. **The canonical writer takes a table definition.** `tools/tables/canon.py`'s `row_bytes`, `key_of`,
   `table_bytes`, `table_hash` and `write_table` take an optional `spec` (a definition in `schema.TABLES`'s
   shape); with `spec` a key column may be `"int"`, which sorts as a number (position 10 after 9). With no `spec`
   the code path is the old one (string keys as UTF-8 bytes). `schema.TABLES` is not changed, so phase A's
   `build.py` (which writes every table of `schema.TABLES`) is untouched. Every phase A and phase B hash is
   unchanged: `tests/test_tables_phase_b.py` (PHASE_A) and `tests/test_tables.py` pass; `test_10b` recomputes
   phase B's stored hashes with the old key rule.
2. **`flux`** holds, for every scanned path, `value` (real or null), `special` (`inf`, `-inf` or null: the loader
   keeps an infinite value, and the writer refuses non-finite reals), `loader_stops` (valid JSON that is not an
   object: the loader's `.get` raises `AttributeError`, which it does not catch) and `case` (section 2's row, by
   name). The value is computed with the loader's own expression (`float(obj.get(key, 0) or 0)` inside
   `except (ValueError, TypeError)`). With two scan rows for one path, the later record that parses wins and a
   later unreadable one leaves the earlier value (the loader's `pass`).
3. **`call_degree`** holds every scanned path's counts (zeros included); a universe path absent from it reads 0.
   A call row counts when its target function is resolved: toward the target file's in-degree and the source
   file's out-degree, whatever the other end (a call into a non-universe file, or to a file id that is not in
   `file_data`, still counts for its source). Two scan rows for one path: both ids count.
4. **Label tables** are protected (written under `protected/`); `position` is 0-based in the parsed outcome
   file's object order (`json.loads`: a repeated key keeps its first position and its last value, as the
   loader's dict does). A commit with no path keeps its commit row (`n_paths` 0). A path repeated inside one
   commit's list is stored once and counted (`repeated_paths`): the flags it sets are the same. Two positions
   carrying one hash cannot come from a JSON object; a damaged table that has them is refused by the reader with
   the count, never the hash. `commits_in_order` also refuses gaps and a path count that disagrees with the file
   rows. The label CLI refuses `--real`: on real data these tables are built only inside the scoring job.
5. **The predictor tables are built in `sandbox_ro`**, one sandbox per repo with phase B's declared inputs, by
   phase B's own `stage_copy` (unchanged) followed by `tables.predictor_rows` on the copy. Label tables of
   decoys are built directly from the decoy's outcome files.

## Derivation (section 2)

6. **Universe, size, nesting.** Universe: phase B's `file` rows with `in_universe = 1` in Python string order.
   Size: the `measure` row `total_loc` (a real); a missing or non-positive size stops the derivation
   (`DeriveError`, counts only). Scan columns and `nest_max`/`nest_mean` come from `measure` (null: missing);
   `amplified_cascading_flux` from `flux`, never from `measure`.
7. **The predictor list** is a literal copy of `sa3_score.PREDICTORS`; `test_2e` compares it, and the scorer's
   constants, with the reference's source read by `ast` (never imported).

## The input check (section 3)

8. **Two sandboxes per repo**, as phase B's silence count: phase B's `copy` stage (unchanged, run with
   `phase_b.run_stage`), then this module's `stage`: the copies, the sidecar and the nesting file at their study
   paths, `tools/tables/silence.stub(repo)` at `sa3_outcomes/<repo>.json`, linguist's two lists, no clone, the
   tree under test's `tools/` (a scratch copy) as code. The stage imports that tree's `sa3_score` and calls
   `load(repo, True)`, `silent(x, p)` and `design_for(d, y, valid)` unchanged, and writes the arrays (floats by
   `float.hex`) to its own scratch directory. The comparison runs in the launcher.
9. **One item beyond the spec's list:** `in_use:<predictor>` compares the files in use and their recomputed
   bands (and so 5 against 10) with the reference's `design_for`. Predictor side only, no label.
10. **Equality** of arrays is `numpy.array_equal(..., equal_nan=True)`: exact, NaN equals NaN, and 0.0 equals
    -0.0 (the canonical writer stores -0.0 as 0.0, and no statistic tells them apart).
11. **The public output** is, per repo of the marginals file's `ok` rows, `code` (a member of the owner job's
    fixed `STAGE_CODES` or `none`: an exception's type, never its text), `items` (each `true` equal, `false` not
    equal, `null` not compared) and `flux_flagged` (the flagged `flux` rows among the universe's files; reported
    even when the loader stopped). It is checked by `tools/owner/report.py`'s `check` (loaded by file under the
    name its own loader uses; `WORDS` and `STAGES` are not touched) against this module's schemas before
    anything is written; the text rendering uses fixed words only. `test_7` plants markers and bad values.
12. **The universe differs:** the predictor side marks `universe` not equal and every other item `null`; the
    label side reports only "not comparable" (review M8: no bit about named files).
13. **The label side** compares each outcome's flag vector, and the commits in order with each commit's files as
    a set (the loader lists a commit's paths in the outcome file's order, the table in path order; the flags are
    identical). Decoys only: the outcome file may be bound only from under `~/.claude/jobs` or `/tmp`.

## The comparison scorer (section 4)

14. **Sealed copies** are a directory: `tools/sa3_stats.py`, `tools/sa3_score.py` (read as text for test 2e only),
    `docs/sa3_outcome_marginals.json`, `docs/sa3_placebo.json`, `docs/sa3_lock.json`. The statistics module is
    loaded in-process under a name that carries its hash, after an `ast` check that it imports only `sys`, `numpy`
    and `scipy.stats` (`test_9b`); it is the only SA3 module this process runs.
15. **The bookkeeping keys**: `valid` from the sealed placebo file; `sealed` = the sealed lock file's `files`
    (null if absent); `engine` from phase B's `repo` table of the first `ok` repo (the reference reads the same
    repo's sidecar); `unavailable` and `not_run` transcribed constants. A copied value is not a check of
    anything but the copy.
16. **The loop's steps are methods** (`repo_order`, `outcome_order`, `on_silent`, `control_draw`, `finish_cell`) so
    the stream tests change one step in a subclass in the test file; `scorer.py` holds no fault switch. The
    control draws first and checks after; a dropped draw has used the stream.
17. **Output** is `json.dumps(res, indent=1)` without `default=` (every value already a JSON type), read back, and
    compared with the reference's file read back.

## The cell map (section 5)

18. **Cells** are the leaves of both JSON trees; an empty object or list is a cell; a key present on one side
    only is a not-equal cell ("which cells exist", class W, or R under an R container). Equality: same JSON type
    (an integer is not a real, `true` is not 1) and, for a real, the same 64 bits; NaN equals NaN; null equals
    null. **Key order is not compared**: the spec's W class is "which cells exist", and the stream tests require a
    swap of two repos to leave W equal; the order of repos is seen through R cells.
19. **Classes by path**, from the review's table: R = `null_sd`, `perm_p`, `specificity.*`, `random_effects.*`,
    `side_counts.*.above/below/across`, `tests.<confirmatory>.minus_control/reading/allreverts_reading`, and every
    `summaries` key whose statistic is `minus_control`; D = the other reals (including `holm_level`,
    `sign_test_p`, `ci95`, every summary's `mean/se/level/ci/p`); W = the rest (`status`, `n`, `dropped_null`,
    summary `n/positive/negative/reading`, the bookkeeping keys).
20. **Positions**: (repo, outcome, predictor) for a cell; (repo, "control", predictor) for the matched control;
    ("study", section, key) for the rest. The first not-equal R cell in the reference file's order (which is the
    loop order) is named; later ones are marked "may follow from the first" and counted; "R cells after it:
    n equal, m not equal" is printed (review M5).

## Decoy studies (section 7)

21. **The recipe** (`decoy_study.RECIPE`; study P adds `--effect branches=0.5` to every repo):

    | repo | generator | edit after the pipeline | condition |
    |---|---|---|---|
    | django | python, seed 41, `--years 12` | | cut names |
    | circuitpython | c, 42, 12 | | cut names, C |
    | mediawiki | python, 43, 12, `merge_workflow` | | merge workflow, cut names |
    | freebsd-src | c, 44, 12, `--files 850` | | 600+ files in use (S7), cut names, C |
    | go | c, 45, 12 | | cut names, C |
    | bun | c, 46, 12 | pool cut to its first 15 commits (HP has 81) | new-language name; more HP commits than pool commits: the control's second draw |
    | racket | python, 47, 12 | 16 telemetry records planted (every readable case); nesting file cut to 40 paths | new-language name; missing flux values; `nest_max` under the pair floor, `nest_mean` silent |
    | ctrl-mw2 | python, 48, 12, `merge_workflow` | `struct_branch` NULL on all but 296 files (15 of 311); pool replaced by 400 commits with no path, 6 touching only files with no value, 2 ordinary | 296 files in use: 5 bands, not 10; control draws dropped for every predictor and for `struct_branch` alone; commits with no path |
    | ctrl-short | c, 49, `--years 10` | `window_days` set to 671 in its marginals row and outcome file | a window under 730 days |
    | ctrl-plain | python, 50, 12 | pool cut to 12 commits plus one decoy commit touching every universe file | pool smaller than HP and the control covering every file: every draw dropped after both draws used the stream |
    | ctrl-early1 (not drawn) | python, 51, 12 | pool cut to 3 commits | K under 5: control skipped |
    | ctrl-early2 (not drawn) | c, 52, 12 | HP `clears_floor` false in the outcome file and the marginals row | status ok, the primary outcome under its floor |

    10 drawn (5 C, 5 managed: both family cuts fitted), 2 not. Silent predictors occur naturally (`state_danger`,
    `risk_concurrency`, ...); HP_revert and HP_cve fail their floors in every repo. Repo names are given when the
    harness outputs are laid out (files renamed, the `repo` fields of the JSON files rewritten).
21b. **A gate-failed variant of study P** (`decoy_study.gate_variant`): the reference WORK copied, the committed
    placebo file's `valid` set to false (an edit to the decoy's own document), committed, then `lock`, `score` and
    the traced `score` again; its sealed copies beside it. It reaches the "NO FINDING" reading, and the cell map
    compares it like the two studies (`test_3d`). A failed gate turns every reading into that one, so it cannot be
    part of study P itself.
22. **`--years 12`, and a short window by edit.** With seed 11 and `--years 10` the pipeline's cut leaves a 671-day
    window, so `--years 12` is used to keep every other repo at 730. For ctrl-short, `--years 10` with seed 49
    still gave 730 days (the window depends on the seed's commit times), so its marginals row (the only place
    `stage_score` reads `window_days`, `tools/sa3_score.py:487`) and its outcome file say 671.
23. **The reference side** is one harness WORK per study (`tools/harness/sandbox.py`, unchanged): the decoy study
    bound at the study path, every clone under WORK/pool, WORK/tree a git checkout of `tools/` and `docs/` (the
    marginals file, the sealed documents, and a placeholder code review whose text says it is one, as harness
    shim 13 does). `placebo` runs first and its output is committed; then `lock` (refused unless it wrote a commit
    and nine non-empty hashes), `score`, and `score` again under the line tracer; the traced result is checked to
    be byte-identical to the plain one.
24. **Each study is built once** and reused: `decoy_study.build` writes `built.json` with a hash of the recipe, the
    building functions' source and the code they run; tests reuse a finished build under `COMPARE_STUDY_CACHE`
    (a directory under `~/.claude/jobs` or `/tmp`), else under pytest's session directory.
25. **"The control's checks moved before its draws" needs a pool smaller than HP.** When the pool is at least as
    large as HP the second draw takes no random number (`range(len(hp))`), so a check moved before it changes
    nothing; ctrl-mw2's empty draws (first plant) never made the fault bite. When the pool is smaller, every pool
    commit is drawn in every draw, so the control set is the same each time: the fault bites only if that set
    fails its check in every draw. ctrl-plain is planted so (its pool covers every file); the fault (test 4)
    checks the control set right after drawing it and drops the draw before the second. ctrl-mw2's pool was also
    thinned (6 + 2 non-empty commits among 408) so that about one draw in six is empty.

## Coverage

26. **The tracer** is `trace.Trace(count=1, trace=0)` with the interpreter's and the site directories ignored,
    running `stage_score` unchanged inside the harness sandbox; executable lines are the standard library's own
    (`trace._find_executable_linenos`) inside the four functions; each function's `def` line runs at import,
    before the tracer starts, and is not listed. Unexecuted lines are matched to `decoy_study.REASONS` by text;
    `test_8` fails on any line with no reason.

## The blind runner

27. **The seal layer** is a SHA-256 manifest of the reference side (`tree/tools`, `tree/docs` but the lock and
    result files the reference writes, `study/` but `-shm` files, each clone's HEAD), taken from the pristine side
    with `blind_runner.py seal`. `tools/owner/seal.py verify` needs an owner-job seal of the decoy; the manifest
    stands in for it on decoys.
28. **The placebo layer** re-runs the reference `placebo` from a scratch copy of the copy and compares its output
    with the sealed committed placebo file, exactly (the cell map's equality).
29. **The cell-map layers**: the copy's tree is committed as it is into a fresh scratch git repository, so the
    reference `lock` seals whatever the copy holds (the seal is a layer of its own, and withholding it must mean
    the faulty code is scored); the comparison result is computed once from the pristine tables and the sealed
    copies. A reference that writes no result fires both cell-map layers.

## Tests

30. **"One call row removed"** (test 1) is made in the degree table: one fewer in-degree for a file with one,
    and one fewer out-degree for another file (the table holds counts, not call rows).
31. **"A silent predictor made to draw"** (test 4) still records "instrument silent" (else a W cell changes,
    which the spec rules out): it consumes 200 block permutations of the predictor's values. It uses
    `state_danger`, which has a value in every file (a predictor with no value draws nothing: review m5).
32. **"Two repos swapped"** (test 4) swaps the first two repos. See finding F4 for other swaps.

33. **The unmodified comparison result is kept beside each build** (`comparison-<key>.json`, the key a hash of
    `tools/compare/*.py`, the sealed copies and the tables' indexes), so that tests run one per process do not
    recompute it; every faulted scorer of test 4 runs afresh.
34. **The label-side "commit with no path dropped"** (test 1) uses ctrl-mw2's pool, which holds 400 such commits.

## Findings: where section 2 or 4 differs from the reference, or the spec is wrong or unclear

F1. **Duplicate paths (section 2, "the later row's values win")** — the loader keeps, per scan column, the later
    **non-null** value (`tools/sa3_score.py:99-101`, `if v is not None`), and for the telemetry record the later
    record that **parses** (a later unreadable one leaves the earlier value: `:102-105`, `except ...: pass`); both
    rows' ids count toward the degrees (`:98`, `:125-130`). Moot for stored tables: phase B's `read_scan` refuses a
    duplicate path (`tools/tables/build.py:146-147` of `read_scan`). `test_2a`/`2b` plant both cases.
F2. **A null nesting element (section 2)** — the loader reads `[3, null]` as (3, missing), the missing value for
    that element only (`tools/sa3_score.py:147-149`: None into a float array is NaN). Phase B's `measure_table`
    cannot store it: `float(got[i])` stops on None (`tools/tables/build.py:218`, `measure_table`), and it reads an
    entry `[]` as missing where the loader's `(a, b)` unpacking stops. The spec's rule is right; the table route
    could not be built for such a file (review m2c).
F3. **Non-finite telemetry (section 2's case table)** — `{"…": Infinity}` and `1e400` read as +inf in the loader
    (not missing); `{"…": NaN}` and `"nan"` read as missing without any exception. The table has no row for them
    ("a number" covers them literally). `flux.special` holds the infinities.
F4. **A swap of two repos moves D cells (section 5 classes; the blind-test row "two repos swapped in the
    marginals file … cell map R only")** — every study summary is a mean over repos in loop order
    (`tools/sa3_score.py:162-164`, the values in `eff`'s insertion order, `:403`), so the summation order follows
    the repo order: swapping repos 0 and 5 of study N changed 114 D cells (study summaries and tests, rounding
    differences of at most 1e-12 relative; `test_4c`) besides the R cells. Swapping the first two leaves every D
    cell equal (a + b = b + a). The blind test's expectation for that fault should read "cell map R, and D
    summaries unless the two repos are adjacent at the head of the order".
F5. **"Missing when … a null element" vs `[]`** — see F2; also an entry naming a path with a leading slash that
    the universe lacks is simply not used (the tiny test's `/src/pkg/edge.py`).
F6. **Section 3 "the count of flagged flux rows"** — only rows of universe files can stop the loader (the loader
    skips other paths before parsing, `:95-97`), so the count is over the universe's files.
F7. **Section 8 test 4's "a silent predictor made to draw" and "two outcomes swapped"** are only stream faults if
    the cell records stay as they were; written that way (31). With the record changed, W cells change too.
F8. **Section 7: the placebo layer of the blind test is not defined beyond its name**; 28 is the reading taken.
F9. **No difference was found between section 4 and the reference**: the cell map is all-equal on both studies,
    every key the reference writes, every class.
