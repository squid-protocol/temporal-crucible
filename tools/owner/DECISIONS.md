# Decisions — the owner-run preparation job

Every choice `docs/process/owner_job_spec.md` (Revision 2) did not make, and everything in it that could not be
done as written. Numbers are cited by the tests (`tests/test_owner_prepare.py`) and by the build report.

## Where it runs

1. **The protected root** is `sandbox_ro.PROTECTED_ROOT` = `/srv/storage_16tb/projects/temporal-crucible-protected`
   (a constant). `check_rw` accepts a directory strictly inside it (never the root itself), still refusing the
   study path, laws-study, `/nvme-data`, the pool, `~/.blind` and this repository; everything else under the
   projects root is refused as before. It lies under the projects root, which every sandbox covers with a
   read-only tmpfs, so no sandbox sees it unless it binds one of its directories. A test names another root with
   `name_protected_root_for_tests`, which accepts only a directory under a session scratch root (so it can never
   widen where a real run may write). The guard is unchanged: a protected run directory is a declared read-write
   directory like any other. Test 1c.
2. **The protected directory's layout**: `code/tools/` (the stages and the guard, read-only), `ref/tools/` (the
   reference root's code, read-only) and `ref/docs/` (read-write; a copy of the marginals file only),
   `committed/sa3_placebo.json` (a copy, read-only), `runs/<stage>/<repo|all>/` (each stage's HOME, TMPDIR,
   `args.json`, `stage.log`, `result.json` and outputs), `launcher.log` (the launcher's own traceback, if any). Two
   copies of `tools/` because sandbox_ro binds read-write directories before code: a writable `docs/` inside a
   read-only code tree would be covered by it. Both copies are checked byte for byte against the code root's
   `tools/` before any stage (otherwise `setup_failed`), and the report carries the loaded modules' hashes.
3. **The public directory is bound into no sandbox.** The launcher writes it only through `report.py`, each file
   atomically (a temporary name, then rename). A stage that tries to see or write it finds nothing (test 5b,
   `print`). It must be new or empty, outside the protected roots, the data roots, the stored tables root and
   this repository's `tools/`, and the two directories may not contain one another.
4. **Stage results.** A stage writes `result.json` (atomically) and nothing else the launcher reads. A failed stage
   writes exactly `{"status": "failed", "code": C}`, where C is its exception's **type** mapped to a fixed list
   (`input_missing`, `key_error`, `assertion`, `database_error`, `write_refused`, `os_error`, `value_error`,
   `type_error`, `git_error`, `memory`, `import_error`, `unclassified`); the message is never looked at. The
   traceback goes to stderr, which is `stage.log` in the protected directory. Where no result exists the launcher
   adds `timeout`, `sandbox_refused` (guard exit 3) or `no_result`. The launcher opens `stage.log` only to hand
   it to the child as stdout, write-only; strace shows no other open (tests 5a, 5b).
5. **The validator** (`report.py`): one schema per public file and per stage result; dicts must have exactly their
   keys; map keys are values too and are validated (repo names against the marginals file, modules against the
   code root's `tools/*.py`, packages against the host's installed distributions, lock keys against the
   reference scorer's SEALED list read from its source by `ast`, never imported outside a sandbox). A failure
   raises `ReportError` whose text is `invalid report value: <field>` with the schema's own path
   (`repos.<repo>.count`): never the value, never the key that failed. 40-hex values are allowed only under the
   seal's `code.*.blob`, `documents.*.blob` and `lock_expected`, all computed by the launcher itself from code and
   public documents; no stage-provided value of that shape can reach a public file.
6. **On an invalid value** the launcher stops: the terminal gets `invalid report value: <field>`, the report's
   path and `FAIL invalid_report_value`; `run_log.json` names the stage (`invalid_in_stage`) and is marked
   incomplete; `owner_report.*` is a minimal FAIL. Nothing of the offending result is written anywhere public.

## The count

7. **How `build()` finds the harvest.** `sa3_outcomes.META = mod1_lift.STUDY / "meta_sa3"`, a module-level path
   (`/srv/.../laws-study/pilot/meta_sa3`); `harvest_bodies` and `build` open `META / f"{repo}.db"`. The two calls
   are two sandboxes that differ in one bind at that path: the harvest copy (A) and the stripped copy (A'). The
   function is not edited or patched. The history, scan database and harvest are copies made in the `copy` stage
   (phase B's method: plain byte copies with side files, the copy opened, checkpointed, set to rollback mode, so
   it opens from a read-only bind with no side file); the sidecar and the clone are the originals, read-only.
8. **The A' copy** deletes, by rowid, every `link` row with kind `issue_fix`, a hyphen in `value` and
   `value != value.upper()` (Python's `upper`, not SQLite's ASCII `upper()`); `meta` is untouched and the stage
   checks `done`, `with_merges`, `sa3_links` are still `1`. A harvest without them makes `build()` try to delete
   it: the read-only bind refuses, and the repo is "not determined", code `write_refused` (test 3a).
9. **Published only if A equals the stored file.** "A equals the stored outcome file's primary commits, as a set"
   compares `build()`'s HP commit keys with the stored file's. On "no" the count is `null` ("not reported").
   "Not determined" (count `null`, never 0) when A's build status is not `ok` (`unprepared`, `scan_incomplete`,
   `no_meta`, `build_status_other`), when A' has another status (`aprime_status_differs`), when the stored file's
   status is not `ok` (`stored_not_ok`), or when a stage failed (its code). A, A − A' and A' − A stay in the
   protected directory (`runs/count/<repo>/count_detail.json`).
10. **The pattern disagreements**: for each body row, each match of `hist_meta.RX["issue_fix_sa3"]` (imported, not
    copied; test 2c checks no pattern string is in `tools/owner/`) on subject + newline + body counts one if
    "has a hyphen" and "the key alternative matched" (`m.lastindex == 2`) differ; plus, per commit, each value in
    exactly one of {keys the pattern finds} and {stored hyphenated `issue_fix` values}. Over the whole harvest, not
    only the window.
11. **`Fixes: deadbeef-1` in a subject** is counted: case-insensitively the key alternative comes before the hash
    alternative and takes `deadbeef-1`, a key with lower-case letters. In a body the same line is also a `Fixes:`
    trailer, a fix reference of its own, and is not counted.
12. **The frozen list** is the marginals file's rows with status `ok` (the reference `scored_repos()`); the placebo
    repos are those that also clear the HP floor (as `stage_placebo` selects them).

## The placebo

13. **Run from the copy** `ref/` (its `ROOT`), unchanged, imported (not run as `__main__`; `main()` only
    dispatches) and called. The comparison runs in the same sandbox: bytes; else same structure, strings and
    booleans equal, every number within 1e-9 **absolute** (NaN equals NaN); a missing key or a length difference
    counts as a differing number. Integer fields are reported as equal or not apart from the largest difference
    (review M2). The regenerated file stays in `ref/docs/`.
14. **The clones are bound** for the placebo stage: `universe()` runs `git archive` on each, and the confirmatory
    run will do the same, so the layer tests that layout. The result of the archive is not used by `load()`.
15. **The import recorder** is `sys.modules` after `stage_placebo` returned, filtered to files in `ref/tools`, with
    the SHA-256 of each loaded file. It found the review's twelve exactly. The launcher compares each hash with
    the code root's file; a difference makes the verdict `failed`, code `code_copy_differs`. `hist_meta` is sealed
    by name (the scorer does not load it). If the placebo stage fails, the seal uses the review's twelve.
16. **The runtime fingerprint** is its own stage, `runtime`, in the same sandbox layout: it imports the reference
    scorer and runs its `fit_size_model` and `sps.t.ppf` on made-up numbers, then records the interpreter and its
    SHA-256, every loaded top-level module's distribution and version (by name where Debian's distributions have
    no RECORD), git and tar with their SHA-256, every linear-algebra and Fortran runtime library mapped in
    `/proc/self/maps` with its SHA-256, and the environment variables of a fixed list. `seal.py verify` takes the
    identical fingerprint. The placebo stage's own library map is sealed beside it as `placebo_libraries` (not
    re-verified: that needs the placebo run). Environment values are `null`, a small integer, or the SHA-256 of the
    value (a path never appears).

## The seal

17. **Inputs**: per repo, nine roles: history, scan database and harvest, each with its `-wal` (the spec names only
    the scan database's; a history or harvest in write-ahead mode would need it too), the sidecar, the outcome
    file, the nesting file; `null` where absent. No `-shm`, no `-journal`. Hashed in the `seal_inputs` stage, read
    as bytes inside the read-only sandbox. The `copy` stage hashes the same files again; any difference is
    `inputs_changed_during_run` and the seal is not written.
18. **Clones**: the SHA-256 of `git rev-parse HEAD`'s output, not the 40-character id (item 5).
19. **The six documents**: the reference `lock` names five (`sa3_registration_consolidated.md`, `sa3_placebo.json`,
    `sa3_outcome_marginals.json`, `sa3_power.md`, `sa3_code_review.md`); the sixth is `sa3_registration.md`, which
    holds Amendment 5 and which Amendment 5 section 2 says the seal covers. Plus `job_code`: this job's five files
    and the two sandbox modules.
20. **The nine expected lock hashes** are SHA-1 of `blob <length>\0<bytes>` of the files under the code root and
    the docs directory; test 2e checks each equals `git hash-object` (the reference `blob()`), and test 4 that the
    reference `lock`, run unchanged in a git checkout inside the sandbox, writes exactly them.
21. **"Unchanged since 8fb7fe0"**: `git cat-file -e 8fb7fe0^{commit}`, then one `git cat-file --batch-check` of
    `8fb7fe0:tools/<m>.py` on this checkout (`GIT_NO_LAZY_FETCH=1`, `gc.auto=0`, `maintenance.auto=false`, no
    optional locks), compared with the blob of the code root's file, for every module the import recorder found
    and `hist_meta`. **A PASS condition** by the owner's ruling of 2026-11-14 (the spec's PASS definition had
    omitted it): a module that differs, or is absent at 8fb7fe0, gives FAIL `reference_code_changed`; a check that
    cannot be made (git missing or failing, the commit absent) gives `null` in the seal and FAIL
    `reference_code_unchecked`. The report's seal section says yes, no or n/a; it names no module beyond the list
    it already carries. `--reference-git` (decoys only) names the checkout looked up, so a test can make the check
    impossible. Tests 7a, 7b; `verify` still names a changed module.
22. **The label-side manifest** covers every declared input of every repo (label side included, with side-file
    names) and each clone's `.git`, as phase B's: type, size, times, inode, mode; a `-shm` by presence only (an
    ordinary read by anyone changes it). Taken and compared inside the sandbox; only "unchanged" and the entry
    count leave it. Sizes of label-side files appear nowhere public (test 2e).
23. **The reference `lock` outside a checkout writes real hashes, not empty ones** (`git hash-object` needs no
    repository; only `sealed_at_commit` is empty). Empty hashes arise when git itself fails, for example on the
    `.git` file of a linked worktree whose main repository is not bound, which is this checkout's case in any
    sandbox that does not bind the main repository. Test 4 makes the empty-hash lock that way; `--after-lock`
    refuses it and accepts the one written in a git checkout.

## The terminal, the run, the refusals

24. **The terminal** gets `stage repo ok|failed` lines (`*` for all repos), `report: <path>`, and last the PASS or
    FAIL line (the spec puts the path after it; the build brief asks for PASS or FAIL as the last line, so the path
    comes just before). Stage output never reaches it.
25. **Refusals** (exit 2), all string tests before anything is created: no target; `--decoy` with `--real`;
    `--real` without `--i-am-the-owner`; `--code-root` or `--reference-git` with `--real`; a missing `--protected` or `--out`; on a real
    run a protected directory not strictly inside a protected root; a protected directory `check_rw` refuses; the
    public directory in the places of item 3; a decoy inside a data root or the projects root. Then, on a real run
    only, the plan is printed and one line read from an injectable reader (the default refuses when standing input
    is not a terminal); anything but an empty line refuses. Only then are the directories checked for emptiness
    (a non-empty one is refused) and created. Exit 0 is PASS, 1 FAIL.
26. **A partial run** leaves `run_log.json` with `complete: false` and the last finished stage; a stage killed
    outright shows as the previous one. There is no `INCOMPLETE` word: the spec defines PASS and FAIL only.
27. **`--code-root`** (decoys only) names the directory whose `tools/` is copied in; the tests use it to run a
    misbehaving copy of `tracker_keys.py` with the reference files untouched.
28. **Tests build decoys by planting commits in a control repository before the harness runs the unmodified
    pipeline**, so the clone, history, harvest and outcome file are all genuine products of the reference code;
    the "committed" placebo file is the reference `placebo` stage over the whole decoy inside the harness sandbox.

## Found in review

29. **This directory's modules are loaded by file, under unique names** (`owner_module(name)` ->
    `sys.modules["tools_owner_<name>"]`), never by bare name. The first build imported `seal` by bare name inside
    `launch()`; in a process that had already imported `tools/blind/seal.py` (pytest running `test_blind.py` first)
    that name was taken, `seal.compose` did not exist, and the in-process real-path test ended `FAIL
    launcher_error` (AttributeError at the seal step). A fresh `python3 tools/owner/prepare.py` never had that
    module loaded, so the owner's run was not affected; the fix removes the dependence anyway. The tests load
    `prepare.py` the same way, and each test now asks for the fixtures it reads (`run1`) instead of reading another
    test's directory; every test passes alone and in reverse order.
30. **`OWNER_JOB_TEST_PROTECTED_ROOT`** (tests only) names a second protected root for a fresh process. It is
    honoured only under `/tmp/pytest-of-<user>/` or `~/.claude/jobs/`, and through
    `sandbox_ro.name_protected_root_for_tests` (which refuses data roots); anything else is refused (exit 2), and
    when in force the job says so on stderr. Test 8 runs the real path as the owner will, in a new interpreter, with
    Enter typed into a pseudo-terminal, then `seal.py verify --real` the same way.
