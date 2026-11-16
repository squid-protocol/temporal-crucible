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

# Part 2: the corrected readings, the named streams, the sensitivities

`docs/process/comparison_scorer_part2_spec.md` (Revision 2) is the brief; `reviews/comparison_scorer_part2_spec_review.md`
and the owner's note `docs/sa3_amendment5_note_reading_draft.md` supplied the rulings. Runs of 2026-11-15 on
decoys and synthetic inputs only, under `/home/joe/.claude/jobs/24bf9d40/tmp/part2_build/` (not committed).

## The reading rule (section 2)

P1. **`reading.py` is the first build.** `coded` and `corrected` are one function with two switches: change 1
    replaces the coded stop condition (`primary != "supported"`) by `primary not in ("supported",
    "contradicted")`; change 2 replaces `reading == "supported" and residualised != "supported"` by `reading is
    not the Holm sentence and primary != residualised`. Nothing else differs. Holm order is Python's stable sort
    on `p`, as the reference's `sorted(CONFIRMATORY, key=...)`. A reading outside the four is refused
    (`ValueError`); `control` is compared with "supported" only.
P2. **"Differ" and "more supported" in section 2.1's counts**: an input differs when the three words are not all
    the same; "more supported" when the rule gives more words beginning "supported" than the coded rule. With
    those, `counts_729` gives 135/51, 604/0, 631/51 and the plain null the same (test 1a).
P3. **Change 2 read literally** (owner ruling 1): primary "not fitted" against residualised "not detected" reads
    "not robust to the statistic". So does any "not fitted" against anything else. In the 729 space this cannot
    occur; in the table it is most of the "F -> NR" rows. The spec does not single the case out; the literal
    reading was kept.
P4. **The predicate** (`applies`): change 1 applies when, in Holm order, a primary "contradicted" comes before a
    primary "supported"; change 2 when any test's two readings differ. Equality on its complement holds on all
    851,968 inputs of section 2.4 (test 1b); the predicate is wider than needed (a contradicted test after a
    stop by "not detected" sets it without changing a word), which the spec allows.
P5. **The table** (`docs/process/reading_rule_table.md`): every combination of (primary, residualised,
    control supported or not) for the three tests in Holm order, with the gate: 4 x 4 x 2 cubed x 2 = **65,536
    rows, 30,408 differ**, all with the gate passed. Codes are used to keep it at 4 MB; a legend and the count of
    each word change head it. Which of B, C, D sits at a position does not change the words (the rule reads
    positions only), so names are not rows.
P6. **Against the reference itself** (test 1f): the Holm block's 21 lines are compared, as text, with a literal
    copy held in the test; then the reference's own `stage_score` runs in `sandbox_ro` with its module globals
    rebound to synthetic inputs (`load`, `scored_repos`, `silent`, `design_for`, `S`, `churn_any`,
    `control_effects`, `summarize`, the paths, the lock check emptied, `PREDICTORS` cut to the four primaries),
    each statistic's value encoding which test and statistic it is so the stand-in `summarize` can return the
    chosen reading and p. The Holm block runs as written. 65,536 inputs in B, C, D order with both gates, and
    every weak order of the p-values on every 16th combination (26,624): all equal to `coded`, words and order.
    On the decoys (N, P and P's gate-failed variant) `coded` reproduces every stored reading (test 1g).
P7. **Sections 2.2 and 2.3** are in `reading.py` as `beside` (coded, corrected, "same" or the sentence; it refuses
    a result whose stored reading is not the coded rule's), `level_word` / `exploratory_word` (defect 47) and
    `allreverts_same_repos` (defect 48: the drawn repos whose marginals rows clear both the HP and the
    HP_allreverts floors, as the spec says; a repo in that set whose HP_allreverts cell is not `ok` gives no value).
P8. **The second build** (`reading_b.py`) is compared with `reading.py` on all 851,968 inputs, plus the same with
    the control reading "contradicted", "not fitted" or empty (test 1e); skipped, with the reason, when the file
    is absent. This builder did not read `reading_b.py`.

## The named streams (section 3)

P9. **The hook** is `Scorer.stream(key, rng)`, returning `rng`; the loop asks it once per (repo, outcome,
    predictor) before the silence check (the generator goes to `on_silent` and to the 200 block permutations) and
    once per repo for the matched control. Keys: `("perm", repo, outcome, predictor)`, `("control", repo)`. Part 1's
    cell maps stay all-equal on both studies (test 2b, and part 1's own 3a/3b).
P10. **Spawn keys exactly as section 3**: `(r, 0, o, p)` and `(r, 1)`, r a Python int of up to 64 bits (numpy splits
    it into two 32-bit words; harmless, review minor 2). Repo name: the marginals row's `repo`, UTF-8. Outcome
    index in (HP, HP_allreverts, HP_revert, HP_cve, HP_fixref, KW); predictor index in `derive.PREDICTORS`
    (the reference's order, part 1's test 2e). Test vectors, `Generator(PCG64(SeedSequence(2982,
    spawn_key=K))).random(3)` as `float.hex`:

    | key | spawn key | first three draws |
    |---|---|---|
    | ("perm", "bun", "HP", "struct_branch") | (635298010877155848, 0, 0, 5) | 0x1.9637eb8542ca7p-1, 0x1.0023445ff2650p-3, 0x1.d054f708354dap-1 |
    | ("control", "bun") | (635298010877155848, 1) | 0x1.7e5e656551998p-3, 0x1.eea28f0cd2800p-7, 0x1.23efcb47b8c34p-2 |
    | ("perm", "django", "KW", "in_degree") | (9046051841603672498, 0, 5, 0) | 0x1.f7f9044a69754p-3, 0x1.8933d9cf5c0fcp-3, 0x1.640df4143d995p-1 |

P11. **"Dropping one predictor"** is read as dropping it from the scored set of every repo (the scorer's
    `PREDICTORS`, patched in the test). The spec's exception for "the matched-control cells of that repo" was
    allowed for and measured: under named streams the other predictors' control cells did not change either (the
    draws do not depend on the predictor list).

## The sensitivities (section 4)

P12. **Harvest copies reuse the owner job's code by path**: `tools/owner/prepare.py`'s `stage_copy` (copy,
    checkpoint, rollback mode, and its A' harvest through `tracker_keys.strip_harvest`) runs inside this module's
    `prepare` stage, unchanged; the late-revert copy is made from the same converted copy. The builder runs in a
    second stage with the chosen copy bound at `<study>/meta_sa3/<repo>.db`, the history and scan copies, the
    sidecar, the clone and GitHub's two lists.
P13. **The late-revert resolution as built**: the stored value lower-cased (git hashes are lower-case; the
    pattern is case-insensitive); fewer than 7 characters (the empty value of a quoted `Revert "` line) does not
    resolve; unique prefix among the commits reachable from the clone's HEAD (`git log`); time = the commit time,
    or for a commit brought in by a merge, that merge's (the earliest merge of the history walk, `commit_` by
    rowid, whose later parents reach it without passing through the walk); late = time > the frozen outcome
    file's `cut`. Every `issue_fix` row of a commit with at least one late target is deleted; `trailer:*` and
    `cve` rows are not (so a kernel-style revert whose `Fixes:` trailer names its target still qualifies, review
    M4). No gating on the merge workflow: in a repo whose walk is every non-merge commit no walk commit is a
    merge, so nothing is "brought in", as in the reference.
P14. **Checked against the reference's own split** (test 3e): for every unit commit of the frozen all-reverts
    outcome whose links can qualify it only through reverts, and every merge that inherits from exactly one
    such commit, the reference puts it in the primary outcome exactly when the resolution finds a target at or
    before the cut. 103 cases in study N and 103 in P; **no disagreement**. The merge-time clause never decides a
    case on the decoys (the generator merges promptly: 0 brought-in commits made before the cut and merged after
    it), so it is tested on a synthetic repository (test 3f), not against the reference.
P15. **Which repos are rebuilt**: only those whose harvest copy lost a row; the others keep the frozen file. A
    rebuilt file is used only when the builder, on the unmodified copy, reproduces the frozen file (parsed JSON,
    the over-cap sample left out); otherwise the frozen file stands and the output says so. On real data the
    owner job checked exactly that ("A equals the stored file"). On the decoys, bun's and ctrl-early2's outcome
    files were edited by the recipe (pool cut, floor failed), so the late variant's rows there (1 and 2) are not
    applied.
P16. **A variant with no input changed is not scored again**: its result is the baseline's (the inputs are
    identical); the output says "no row deleted". On both decoy studies the case-sensitive variant deletes no row
    (the generator writes upper-case keys only).
P17. **Floors**: a rebuilt repo's marginals row takes `n_files`, `n_commits`, `largest_commit_share` and
    `clears_floor` of each outcome from the rebuilt file (`variants.apply_rebuilt`); the scorer is given that row
    list in place of the sealed one.
P18. **Output**: per variant, for each of the four primaries on each of the six outcomes, the bAUC summary over
    the drawn repos (`summaries["<oc>|<p>|bauc|all_drawn"]`, at 95%), its n and "above zero" / "below zero" /
    "not detected" / "not fitted (fewer than three repos)", and the difference of n, mean and interval ends
    from the baseline. One fixed sentence heads it. `run` refuses to return an output in which "supported",
    "contradicted", "holm", "0.9833" or "0.975" appears (case ignored); the test also shows the search finds them
    in the reference's own `tests` block.
P19. **What the variants changed on the decoys** (cell by cell against the baseline): `PU_named_streams` against
    the frozen run: R cells only (W and D all equal) in all twelve repos; `PU_tracker_keys_case_sensitive`:
    nothing; `PU_late_revert_ticket_dropped` against `PU_named_streams`: the matched-control cells of django,
    go and racket only (one HP commit fewer in each; the HP files are unchanged because those commits' files are
    also touched by other fix commits), and the study cells built from them. The same in N and P.

## Findings

F10. **"On an unedited decoy, the rebuilt file equals the frozen one"** (section 5, test 3) holds for the
    case-sensitive variant (no row deleted) but not for the late-revert one: the generator writes reverts that
    quote a ticket, some of them late (2 rows in django). Test 3c therefore expects the planted commits plus the
    natural ones, the natural set measured on the unedited copy of the same repo and required to be disjoint from
    the plants.
F11. **A decoy whose outcome file was edited after the pipeline** cannot be rebuilt to the same file; see P15.
F12. **`PU_named_streams` has no stated baseline in section 4's table**; the frozen run is taken.
