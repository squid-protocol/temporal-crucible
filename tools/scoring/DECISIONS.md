# Decisions — the scoring job

Every choice `docs/process/scoring_step_spec.md` (Revision 2) did not make, and what in it could not be done as
written. Built and tested on decoys only (2026-11-15). Numbers are cited by `tests/test_scoring.py`.

## The pin (section 3, step 1; section 9)

1. **`--commit` is required, 40 lower-case hex.** Refused unless `git rev-parse HEAD` of the checkout equals it,
   `git status --porcelain --ignored --untracked-files=all` lists nothing but ignored `__pycache__/` directories or
   `.pyc` files, and `refs/tags/sa3-score-C^{commit}` is the commit. `--untracked-files=all` is added to the spec's
   command: without it a new file inside an untracked directory shows only as its directory. **The real checkout
   holds an ignored `.pytest_cache/` today: the job refuses (`checkout_dirty`) until it is removed.** Test 4a.
2. **Run-2's report** (`owner_report.json` beside `--seal`) is checked before the seal is verified: its placebo
   verdict first (`bytes_equal`, else `run2_placebo`, the first row of section 6), then PASS with no codes, and the
   same target on the report and the seal (else `run2_not_pass`). Test 6c, 6d.
3. **The two seal verifications** run `tools/owner/seal.py verify` unchanged, each into its own new directory
   inside the protected directory (`verify-1`, `verify-8`; a later call takes `-1`, `-2`): step 1 from the
   checkout (there is no clone yet; the checkout is pinned), step 8 from the clone. On a real run step 8 passes
   `--real-docs <clone>/docs`. On a decoy `seal.py` reads `DIR/docs`, so the job gives it a view directory of three
   symbolic links (`study`, `pool` to the decoy's; `docs` to the decoy's at step 1, to the clone's at step 8).
   `seal.py`'s own `differs: <entry>` lines go to the terminal when they match a name pattern (entry names only).
   Its full output stays in `verify-N.log` in the protected directory.

## The fresh clone (steps 2, 3)

4. **The clone** is `git clone -q --no-hardlinks --no-checkout --template=` of the checkout's common git
   directory (`git rev-parse --git-common-dir`: the main repository), then `checkout -q --detach C`, on the host,
   with `-c core.autocrlf=false -c core.hooksPath=/dev/null -c gc.auto=0 -c maintenance.auto=false`. Checked: `.git`
   is a directory with no `commondir` and no alternates, HEAD is C, the status (with ignored and untracked) is
   empty, and every file under `.git/objects` has one link (review, minor 1).
5. **Step 3 hashes** every file the seal names, in the clone: `code` (SHA-256 of `tools/<module>.py`), `job_code`
   (SHA-256), `documents` (SHA-256 of `docs/<name>`) and `lock_expected` (git blob of the nine files). Test 3e.

## The inputs (steps 4, 5, 6)

6. **The copy stage is the owner job's, run unchanged from the clone.** The launcher builds the owner job's own
   `Job` object with the clone as its code root and calls its `copy` stage per ok repo and then its `seal_inputs`
   stage, so both run `<clone>/tools/owner/prepare.py stage ...` in the read-only sandbox. Each copy's nine role
   hashes (taken of the originals, before copying) must equal the seal's; each database copy must have passed its
   quick check with no side file left (`detail.json`); `seal_inputs` again must equal the seal's inputs, GitHub's
   lists and every clone's HEAD. The ok repos of the clone's marginals file must be exactly the seal's repos.
   Tests 5b (a scan database changed after step 1's verify), 2c.
7. **What the reference reads** in steps 6 and 9 is exactly what the owner job's placebo stage binds, for every
   ok repo: the history and scan copies at their study paths, the sidecar, the nesting file and the outcome file
   (originals), the clone at `<pool>/<repo>`, GitHub's two lists with `LAWS_LINGUIST_DIR` set; interpreter
   `/usr/bin/python3 -I -B`; the sandbox's environment. The harvest is not bound (the score does not read it).
8. **The predictor-side record** (section 2, step 2) is read from a fixed path in the commit,
   `docs/sa3_predictor_check.json`, in the shape of `predictor_check.py`: the verdict of
   `tools/compare/input_check.py`, the two table directories, and every file's SHA-256 per ok repo. Step 5 stops on
   a verdict other than `all_equal` and on any file whose hash differs; on a real run the directories must lie
   under the stored tables root (in tests only, a test-named protected root); on a decoy, under a scratch root. The
   deviation table is read from `docs/sa3_deviation_table.md`; step 5 also stops if it is missing. **Neither path
   nor shape is in the spec**; the session that does steps 2 and 3 of section 2 must write them there.
9. **The loader rehearsal is tools/compare/input_check.py's stage** with `--labels`: the reference
   `sa3_score.load(repo, True)`, `silent` and `design_for` unchanged from the clone, the real outcome file bound.
   Only ok or the exception's type leaves; the arrays stay in `runs/rehearse/<repo>/loader/` and are what step
   11's label-side check compares. Test 5c (a keyword path outside the universe in a repo the placebo does not
   load, so run-2 still passes: stopped at step 6 with `assertion`, no ledger entry).

## The stages

10. **This job's stages** run `<clone>/tools/scoring/score_sa3.py stage NAME` in `sandbox_ro`, the guard invoked
    in the command (`sandbox_ro.run(..., guard=False)` with `sandbox_ro.py exec --` first), because the lock and
    score layout binds no code tree with `tools/harness/` at its root. Results are read from the stage's
    `result.json` only and validated field by field (`schema.STAGE_RESULTS`); a failed stage is its exception's
    type (`prepare.code_of`, the owner job's fixed list).
11. **The import recorder.** Every stage records each module in `sys.modules` whose file lies in the clone's
    `tools/`, with its SHA-256. The launcher requires each path to be in `git ls-tree -r C` and its bytes to be that
    blob; otherwise the stage is `failed` with `modules_differ`. The owner job's `copy` and `seal_inputs` stages
    record nothing (their file is sealed code, hashed at step 3). The report lists every stage's modules. Test 2b.
12. **The reference `lock` and `score` are imported and called** (`stage_lock()`, `stage_score()`), as the owner
    job's placebo stage calls `stage_placebo()`, from `<clone>/tools`, the import's file checked. Their printing
    goes to `stage.log` in the protected directory: **the means are not on the terminal**, only in the report
    (review, minor 6).
13. **The layout of steps 7 and 9** (the review's, tested): read-write `[stage directory, <clone>/docs]`, then
    read-only `<clone>/.git` and `<clone>/tools`; the clone root itself is never bound, so nothing covers `docs/`.
    Inside: git reads C, `docs/` is writable, `tools/` and `.git` refuse writes. Tests 1f, 2d.
14. **After the lock:** `seal.py verify --after-lock` (the nine hashes), the lock file's shape and
    `sealed_at_commit == C` (review, minor 3), and on the host `git -C <clone> status --porcelain --ignored
    --untracked-files=all` exactly `?? docs/sa3_lock.json`. A lock made where git cannot read the repository writes
    real hashes and an empty commit: stopped at step 8. Test 4b.
15. **After the score**, the same status must be exactly the lock and the result. The result already exists then,
    so a difference does not stop the job (the spec: nothing after the score can strand the result): it is recorded
    in the report's provenance.

## Once (section 5)

16. **The ledger** is one JSON object per line, appended, flushed, fsynced (and its directory on creation), at
    `<protected root>/sa3_score_ledger.jsonl`: on a real run the protected root that contains `--protected` (the
    production one; in tests a test-named one). `--ledger` is for decoys only, and must lie outside the protected
    and public directories. Events: `started` (time, C, run-2's seal SHA-256, the `--rerun` reason, the protected
    directory's name), `completed` (the result's SHA-256), `resume`, and one the spec does not name: **`stopped`**
    (a code), written when a start left no result file, or one that does not parse. `stopped` is a start with no
    completion, so a second start needs `--rerun REASON`.
17. **The rule** (`ledger.decide`), read under the lock (item 32) before the plan is printed: no entry → first
    start; a start with no completion and `--rerun` → a second start (refused while that start's clone holds a
    parseable result: `result_exists_resume`); a completion → no start ever (`--rerun` too is refused);
    `--resume` needs a completion, or adopts the result in an open start's clone. Refusals exit 2 and create
    nothing but the lock file. Tests 1b, 1h, 3a, 3d.
18. **Every attempt is listed** although a failure in steps 1 to 8 writes no ledger entry: a second file beside
    the ledger, `sa3_score_ledger_attempts.jsonl`, records each attempt's start and its end (step and code). It
    decides nothing. The report and a stopped run's short report list it.
19. **`--rerun REASON`** is the owner's own text and is printed in the report's first lines and the ledger: it
    must match `[A-Za-z0-9 .,;:()/-]{1,200}`, so it cannot carry a path with a tilde, a shell expansion or a newline.

## The score and the result (steps 9, 10)

20. **The result is published first, ALWAYS** (build review, 2026-11-15). When the reference `score` returned 0
    and `docs/sa3_result.json` exists in the clone, its bytes are written atomically to the public directory,
    `completed` is appended with its SHA-256, and the receipt printed: `receipt sa3_result.json sha256 <S> commit
    <C> seal sha256 <seal>`; the lock file is published beside it. Only then is it checked by shape
    (`schema.check_result`: its ten top-level keys; every key a repo of the marginals file, an outcome, a predictor,
    a statistic or summary key built from fixed words; every string a fixed word, except `engine` and the nine
    `sealed` hashes; lists of at most two numbers; NaN allowed). A failure is a verdict, never a stop:
    `result_shape: unexpected` with the position in the result's schema where it failed (fixed words and the
    placeholders `<repo>`, `<key>` only, validated; never a value) in the report's first lines and as step 10's
    `result_shape` line (`result_shape_unexpected`) in run_log; the report then reads no number from the result,
    and steps 11 to 14 run, each failing with its own code if it must. `stopped` after `started` is written only
    when the score produced no result: a time-out, a crash, exit 2 (LOCKED), no file. `--resume` repeats the shape
    check. Test 3g (a result with an unforeseen key: published, completed, the verdict in the report, no rerun).
21. **Time-out of a day** for step 9 (`SCORE_TIMEOUT = 86400`), and for the three scoring loops after it
    (`compare`, `named`, each `variant`: on real data each is a full loop, estimated 27 to 34 minutes, and the
    owner job's 7,200 s would leave only a factor of four); every other stage keeps the owner job's 7,200 s. The
    `engine` field must be 7 to 40 hexadecimal characters (`sa3_scan.ENGINE_SHA` is 40) or a version string.

## After the score (steps 11 to 14)

22. **The parts** and their order: `labels` (step 11: the five label tables by `tables.label_rows`, outcome files
    bound read-only, then `input_check.compare_label` on the rehearsal's arrays against `derive` with those tables);
    `compare` (step 12: `scorer.Scorer` on the predictor tables and the label tables, sealed copies = the clone, then
    `cellmap.cell_map` against the clone's result file); `readings`, `named`, `hv_prepare` per repo, `hv_build` per
    repo and harvest copy used, `variant` twice (step 13). A part whose input failed is `dependency_failed`. Steps 12
    and 13 run in sequence (the spec allows side by side; done in parallel they would save about one scoring loop).
23. **The harvest variants are re-orchestrated, not re-implemented.** `harvest_variant.Layout` refuses a
    non-decoy study and `variants.variant_inputs` launches its sandboxes from the host, so the job runs the same
    library calls as its own stages: `harvest_variant.stage_prepare` and `stage_build` (each unchanged in the
    sandbox), then, in one sandbox per variant, `comparable`, `reorder`, `tables.build_label_tables`,
    `variants.apply_rebuilt`, `score_named`, `block`, in `variant_inputs`'s order and with its three reasons. The
    three results equal part 2's own `variants.run` on decoy P as parsed JSON, key for key. Test 2e. **No file of
    `tools/compare/` was changed.**
24. **What is published of the check:** the cell map's counts per class and per repo, the first not-equal R cell's
    position (repo / outcome / predictor, validated against fixed words and repo names) and the R cells after it;
    the label-side check's items per repo. The cells themselves, the comparison's result, the label tables, the
    arrays and the rebuilt outcome files stay in the protected directory.
25. **Section 6's sentences** are constants (`texts.SENTENCES`), one per row, printed on the terminal and in the
    report exactly when their case happens (`sentences_after`, `stop_sentence`). The gate's row is printed always
    (its case is always: the gate is fixed). "W or D differs" also adds "The check did not confirm this run." to
    the label line. **The table has no row for "the label check or the cell map did not run"**: such a part ends
    `failed: <code>` under the last row's sentence, and the label gains nothing. Test 1g; on blind copies 6a-6d.
    **Found on decoys (test 6e):** when the committed predictor tables' universe differs from what the reference
    read (an encoder fault the step-2 check missed), the comparison does not produce not-equal cells: `derive`
    refuses the label tables ("commit paths are not universe files"), so the label-side check ends not equal
    (that repo's code `value_error`) and the comparison scorer and named streams end `failed: value_error`. The
    terminal and report print the label-check sentence and the "failed to run" sentence; the cell map reads
    "failed".
    **Owner ruling of 2026-11-15** (after the build review): a check that cannot be computed is "not confirmed".
    When the label tables, the label-side input check (any repo ending with a code) or the comparison scorer
    end failed, so there is no complete cell map, the sentence "The check could not be computed: <code>" (the
    first failing part's code; a constant with one validated code in it) is printed with the same consequence as a
    W or D difference: the result stands as the registered output, the label gains "The check did not confirm
    this run", no hypothesis is called confirmatory until a decoy investigation places the cause. The last row
    ("failed to run") now covers only the corrected readings, named streams and the harvest variants. Tests 1g,
    3c, 6e.
26. **The report** is built from validated values only (`REPORT` in score_sa3.py; tools/owner/report.py's checker
    extended in `schema.py`) and fixed texts; numbers that are not finite are published as null. The first lines
    follow section 4; then the parts, the check, the readings beside, every variant in `variants.TABLE`'s order
    (the five reported equal and the two not run with `variants.py`'s own sentences, read from the clone's source by
    `ast`), the deviation table, the provenance, the ledger. The deviation table is the committed file with each
    `{{run:...}}` token replaced by fixed words (`report_md.fill_deviation`).
27. **A stopped run** writes a short `report.md` / `report.json` (step, code, its meaning, the sentence, the
    attempts, the ledger), validated.

## Resume

28. **`--resume --commit C2 --receipt S`** runs on the first run's protected and public directories. Before
    anything: the receipt equals the ledger's completed entry, the published result's SHA-256 and the clone's; the
    checkout is at C2 and clean (no tag needed: C2 may be a later commit). A `resume` entry is appended. If C2 is C,
    the parts run from the first clone; otherwise from a fresh clone of C2 inside `resume-N/`, and each part is
    labelled "run later, on <date>". The sealed copies are always the first clone's. Earlier report files are kept as
    `*.superseded-N`. **`resume` has no path to the score:** `step9_score` is referenced from `run_full` only, and
    nothing reachable from `resume` names it, `step7_lock` or a stage called `score` (test 1e, static); an
    in-process resume with both trapped completes (test 3b, dynamic); and three resumes after planted failures
    complete with one start in the ledger (test 3c).

## Tests only

29. **`SCORE_SA3_TEST_FAIL=<stage>`** plants an exception in one named stage (the review's "planted exception");
    honoured on decoys only, and its presence refuses a real run. **On a real run under a test-named protected
    root** (`OWNER_JOB_TEST_PROTECTED_ROOT`, the owner job's), predictor tables may lie under that root.
30. **The decoy route** (`decoy.py`): a full clone of this repository (so `8fb7fe0` is present and run-2's
    "unchanged since 8fb7fe0" holds), this worktree's `tools/` copied over it, the decoy's documents in `docs/`, the
    predictor-side record made by `input_check.py --decoy` on the decoy's tables, the deviation table draft,
    committed and tagged; run-2 is `prepare.py --decoy` from that checkout. The job then runs from that checkout as
    the owner runs it from this one. Routes and the main run are cached under `SCORING_ROUTE_CACHE`, keyed by every
    file of `tools/`.

## Run time (section 8)

31. **Measured on decoy P** (12 repos): the reference score 56 s; the comparison loop 49 s; named streams 50 s;
    the late-revert variant 53 s (the case variant deleted no row there: no loop); the whole job 230 s, so about
    20 s of checks. **Scaling method**: the ratio of the score's seconds per scored repo to the placebo stage's
    seconds per placebo repo, on the same decoy (56/12 against 4.4/11: about 12, or 15 with the placebo's one
    second of start-up removed), applied to run-1's real placebo stage (68 s for 20 repos) and the real 40 repos:
    one loop about 27 to 34 minutes. The job runs four or five loops (the reference, the comparison, named
    streams, the late-revert variant, and the case variant if any repo loses a row), plus about 15 minutes of
    checks scaled from run-1's log (two seal verifications, the copies, the rehearsal on 40 repos, the harvest
    copies and builds): **about 2 to 3 hours**; with the review's factor of three either way, 1 to 7 hours.

## The build review (docs/process/reviews/scoring_build_review.md), 2026-11-16

32. **B1. After `started`, only the result file decides.** `step9_score` turns every exception after `started`
    (`KeyboardInterrupt` included) into a stage result; `step10_publish` then looks at the clone's
    `docs/sa3_result.json` only. Present and a JSON object, whatever the stage's status or exit code: `completed`
    with its SHA-256 first, the receipt, the result's path in the protected directory, then the public copy inside
    `try`. A failed copy prints a fixed line and ends `STOPPED publish_failed` (exit 1), never `stopped`;
    `--resume` publishes from the clone when the public copy is missing (SHA-256 against the ledger and the
    receipt). Interrupted with the result recorded: `STOPPED interrupted` (exit 130), ledger `started,
    completed`, next command `--resume --receipt S`. Interrupted before any file: ledger `started, stopped
    (interrupted)`, next command `--rerun REASON`. A file that does not parse: `stopped (result_truncated)`,
    `--rerun` allowed. A launcher killed between the file and `completed` (ledger `started` only):
    `--resume` without `--receipt` on that run's protected directory (the name recorded in `started`) adopts it.
    A stage that ended failed after the file existed is published with a fixed line naming its code; for
    `modules_differ` the line says the result's code is not shown to be the pinned commit's. **Owner ruling of
    2026-11-16:** such a result is published as built and counts as NOT CONFIRMED, the same consequence as
    `not_computed`: the fixed sentence `code_unpinned` is printed and written, the label gains "The check did not
    confirm this run.", no hypothesis is called confirmatory until a decoy investigation, written up and dated,
    places the cause; report.json carries `unpinned: "modules_differ"`. Test 3m. `record`, `save_log`, `stopped()` and
    `finish()` never raise (`launcher.log`). Tests 3h to 3l.
33. **M1. One launcher at a time.** An exclusive `flock` on `<ledger>.lock`, taken in `main` before the ledger
    is read and held until the launcher ends; a held lock refuses with `ledger_locked`. `step9_score` reads the
    ledger and decides again just before appending `started`; a different answer is `ledger_changed`, nothing
    started. Test 1h.
34. **M2.** On a real run whose study or pool is the production path, the ledger is the constant
    `<production protected root>/sa3_score_ledger.jsonl` and `OWNER_JOB_TEST_PROTECTED_ROOT` is refused; any
    other study needs the test root, and its ledger and tables lie under it. Test 1i; test 8 unchanged.
35. **M3, M4.** The stopping lines follow the ledger read at the stop: the section 6 row sentence ("nothing has
    been scored") only while the ledger is empty; then one of three fixed ledger sentences (`texts.LEDGER_STATE`).
    After a `completed`, a stop writes `stopped-N.md` / `.json` and never touches `report.*`. Everything after
    `completed` is one `try` that ends in the report (`after_completed`). Tests 1j, 3b.
36. **M5.** The deviation table draft is rewritten against its sources (29 rows and a footnote: every defect from
    42 to 64, every name of `variants.TABLE`, the reference's `not_run` and `unavailable` keys). Test 1k.
37. **Minors.** (2) the pin refuses an index entry marked assume-unchanged or skip-worktree (`git ls-files -v`)
    and compares every module the launcher loaded from the checkout with the commit's blob; (3) each headline
    test is read in its own `try` and kept if it fits its shape, whatever the rest of the result; (4) the minimal
    report keeps the label's clause and the section 6 sentences; (5) `stopped()` never raises; (6) `started`
    records the protected directory's name; (7) the label stage gets the day's time-out; (8) stale words
    corrected; (9) the documented command is `python3 -I -B`, and the launcher sets a `sys.pycache_prefix` that
    does not exist, so it never reads the checkout's `__pycache__`; (10) covered by item 32; (11) report times
    carry US Eastern beside UTC. Minor 1 (`.pytest_cache/`) is the coordinator's to clear before the pin.
