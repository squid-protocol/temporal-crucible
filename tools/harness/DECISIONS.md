# Harness: decisions the spec left open, every shim, every stage that could not run

`docs/process/harness_spec.md` is the brief. Numbers below are from runs of 2026-11-14 on seed 11, default
profile, `--years 10`, under `/home/joe/.claude/jobs/24bf9d40/tmp/harness_build/` (not committed).

## The sandbox

1. **Hide wide, re-expose narrow.** Rather than hiding `laws-study` minus the engine, the whole of
   `/srv/storage_16tb/projects` is an empty tmpfs (it holds laws-study, the clone pool, the v6 checkout this
   repository's `_engine.py` points at by default, and this worktree); the engine export alone is bound back,
   read-only. The home directory and `/tmp` are hidden the same way; WORK is bound back. Every hiding tmpfs is
   remounted read-only after the binds, so it cannot be written either (test 2 checks 20 paths).
2. **What is still writable inside besides WORK**: nothing found. `/dev` is remounted read-only (device nodes
   still work); `/dev/shm` is `WORK/shm`. Two host mounts show `rw` in the sandbox's mount table
   (`/var/lib/docker/overlay2/.../merged`, `/run/docker/netns/...`); both are root-owned and a write fails with
   EACCES (test 2 includes `/var/lib/docker`).
3. **The guard never touches a forbidden path from outside.** It reads `/proc/self/mountinfo` first and returns
   "not inside" before any `stat`; only when the study path is proven to be a mount does it compare its inode
   with `WORK/study`'s. `check_work` refuses a WORK under this repository or a data root by string comparison.
4. **Test 1 ("lands in WORK/study and nowhere else")** is checked as: the file appears in `WORK/study`, nothing
   else in WORK changed, and the study path lists exactly that file. The real study directory is not looked at
   (that would break the rule the sandbox exists for); that it was not reachable is the proof.

## Shims (inputs supplied from outside; no tool file is edited, no tool function replaced)

| # | shim | replaces | why |
|---|---|---|---|
| 1 | `WORK/<route>/tree/` = a copy of `tools/` (no `__pycache__`) and of `docs/sa3_registration_consolidated.md`, `docs/sa3_power.md` | the repository checkout | the tools read and write paths relative to the repository (`REPO_ROOT`, `docs/...`); the two docs are sealed by `sa3_score.SEALED` |
| 2 | the control repository copied to `WORK/<route>/pool/ctrl-NAME`; `EXPOSURE_POOL` = `WORK/<route>/pool` | the clone pool | `_engine.POOL_DIR` |
| 3 | `WORK/<route>/study` bound at the study path | the study directory | the spec |
| 4 | `HOME` = `WORK/<route>/home`, with linguist's `vendor.yml` and `documentation.yml` copied from `~/.cache/temporal-crucible/linguist-e0c78d62c42a/` | `laws_units.linguist_patterns`' download on first use | no network; the files are sha256-checked by the tool on every read |
| 5 | `PYTHONUSERBASE=/home/joe/.local`, the user site-packages bound read-only, its `__editable__.gitgalaxy-2.9.2...pth` blanked by `/dev/null` | — | HOME moved, so the user site (where `tree_sitter_language_pack` 1.20.0 is) must be named; the editable install's finder points into `/nvme-data` and is kept from loading at all |
| 6 | the host's `~/.cache/tree-sitter-language-pack/v1.20.0` bound read-only at the same place under `WORK/<route>/home` | `tree_sitter_language_pack.get_parser`'s download of grammars | without it every file is "not measured" and the nesting stage silently measures nothing (`sa3_nest_scan.py:47-51` swallows the download error); found on the first run |
| 7 | `GITGALAXY_PATH` = the engine export | the live v6 checkout (`_engine.py:18-20`) | `mod1_run` passes it to `laws_build --gg`; so route `own`'s MOD-1 scan uses the same frozen engine as `sa3_scan`. `laws_build` then records engine `""` (`git rev-parse HEAD` of an export). In the real study MOD-1's scans were made by the v6 checkout, not the export: not reproduced here |
| 8 | `docs/harness_draw.json` (`{"draw": [{"repo": NAME, "lang": LANG}]}`) and `mod1_run --draw docs/harness_draw.json --only NAME --out docs/mod1_prep.json` | `docs/draw40.json` | the draw file is the only way to name a repo to `mod1_run` |
| 9 | `mod1_lift --out docs/mod1/lift_NAME.json` | — | where `sa3_scan.py:211` reads the snapshot from |
| 10 | `sa3_scan --sha <manifest snapshot>` (route `manifest`) | the lift file | the spec's second run |
| 11 | `laws_history.py --repo NAME --language LANG --out <study> --c-family` (route `manifest`) | `mod1_run`'s call of it | the same arguments (`mod1_run.py:75`); route `manifest` skips `mod1_run`, whose cut scan it does not need |
| 12 | `docs/sa3_outcome_marginals.json`: one row built from the outcome file's own `status`, counts and `clears_floor`, `drawn: true` | the frozen file | no tool writes it (the spec) |
| 13 | after `lock` stops, route `manifest` only: a placeholder `docs/sa3_code_review.md` whose text says it is a placeholder; `lock` and `score` run again | the code review | to see what the seal does past that stop (it seals; item 23). `--no-shim-lock` skips it |
| 14 | git: `GIT_NO_LAZY_FETCH=1`, `gc.auto=0` and `maintenance.auto=false` (environment and a private global config), `GIT_CONFIG_NOSYSTEM=1`, `GIT_CEILING_DIRECTORIES` = WORK's parent, `safe.directory=*`, `TZ=UTC`, `LC_ALL=C.UTF-8` | the user's git configuration | the spec; determinism |
| 15 | `TMPDIR` = `WORK/<route>/tmp`, `/dev/shm` = `WORK/<route>/shm`, `PYTHONDONTWRITEBYTECODE=1` | — | nothing written outside WORK |
| 16 | every tool and the engine run with `/usr/bin/python3` (3.12, numpy 1.26.4, scipy 1.11.4, tslp 1.20.0) | the study's interpreters | `sa3_scan`/`laws_build` run the engine with `sys.executable`; the study's interpreter is not recorded anywhere this harness may read. A scan with and without the user site gave identical `file_data` and `fcall_data` |
| 17 | repo name `ctrl-<name>` | — | can never collide with a real study repo's file names |
| 18 | `docs/mod1_language_amend.json` not copied | — | `mod1_run` reads it only to amend named real repos |

`probe.py` is not a shim of a stage: it runs after the pipeline, inside the sandbox, and reads results by
calling the tools' functions unchanged (`mod1_lift.frame`, `sa3_outcomes.universe`, `sa3_score.load`,
`design_for`, `silent`, `Design.effect`, `laws_units.Excluder.why`). Its per-predictor effect equals what
`sa3_score score` wrote to `sa3_result.json` to the last digit on every run (the table shows both).

## Choices the spec did not make

19. **Two WORKs per control repository** (`own`, `manifest`), because `sa3_scan` skips a repo already scanned
    and both routes write the same file names in one study directory.
20. **Planted-effect row.** The statistic is `sa3_stats.Design(loc, y, bands(loc, paths)).effect(x)`, as the
    scorer computes it. Manifest side: the manifest's unit files, `loc` at the snapshot, positives = union of
    `positives` of labels with `counted: true`, `x` = the planted **count** (the scorer's primaries are counts),
    `max_nesting` its depth, `d_branches` the density change. Also given: the same on true fixes in the window,
    and a decomposition (manifest labels and counts on the files both sides call units → plus the pipeline's
    instrument and LOC → plus the pipeline's labels = the pipeline's number). Mapping property → predictor:
    branches → `struct_branch`, max_nesting → `nest_max`, calls_in → `in_degree`, calls_out → `out_degree`,
    pointer_ops + alloc_ops → `state_pointers_alloc` (the scorer sums the two families, so one row);
    `state_writes_in_branches` and `d_branches` have no predictor and are *undecided in the manifest* (the
    manifest names no instrument for them). **Agree = within 0.01**: the spec gives no tolerance; with equal
    universe, labels and counts the two numbers are identical, so any gap is a disagreement upstream.
21. **Manifest side of "bots"**: units in the walk that are bot-authored, or direct/squash units made only of bot
    commits. A human merge that brings in one bot commit is not a bot unit (first run counted them; corrected).
22. **Manifest side of "control pool"** is the spec's: units in the window, not fixes, not tree-wide, not bots,
    touching a snapshot unit file. It therefore includes ticket features and qualifying reverts, which HP counts
    and the code removes from the pool; the row lists the differences by type so these are visible as such.
    **"Keyword outcome"** likewise: fixes in the keyword convention with no reference.
23. **Diagnostics** (in the row's detail, never in a verdict): causes of each HP commit difference (positive
    outside the pipeline's universe; touched under a later path; before the pipeline's window start; the
    commit's message convention; for pipeline-only reverts, the target's time against the pipeline's cut); for
    branch keywords, the harness's own count of `else`/`case`/`default`/`&&`/`||`/`and`/`or` in each file (read
    with `git cat-file` outside the sandbox, from the generated repository only); for calls in, `in_degree`
    split into same-file and cross-file calls from the scan's `fcall_data`.

## Stages that could not run, or ran and stopped, with the line

24. `sa3_score.py lock` — `tools/sa3_score.py:512-514`: "cannot seal; missing: docs/sa3_code_review.md". Every run.
25. `sa3_score.py score` — `tools/sa3_score.py:344-347`: "LOCKED", no `docs/sa3_lock.json`. Every run.
26. With the placeholder review (shim 13): `lock` **seals** (rc 0, `sealed 9 files at  ->`, empty commit): WORK/tree
    is not a git repository, so `git status --porcelain` at `sa3_score.py:515-517` fails, prints nothing, and
    "nothing printed" is read as "no uncommitted changes"; `rev-parse HEAD` gives "". The seal fails open
    outside a git checkout. `score` then runs; with one repo every summary is "not fitted" (n = 1 < 3,
    `sa3_score.py:162-163`), and the per-repo effects are written.
27. `bot_merges`, route `own`: `mod1_run` stops at `tools/mod1_run.py:90-91`, "only 1 usable commits": every
    first-parent unit is a bot-authored merge, and the cut is taken over non-bot units only.
28. `bot_merges`, route `manifest`: `sa3_score.py placebo` crashes at `tools/sa3_score.py:264`
    (`IndexError: arrays used as indices must be of integer (or boolean) type`): no repo clears the HP floor, so
    `drawn` is an empty float array. Then `lock` stops (missing `docs/sa3_placebo.json`).

## Timing

29. One engine scan of a default-profile Python control repository (404 files in the archive): **2.4 s** wall
    (sa3_scan, first scan, load average 1.5 on 12 cores). Whole harness, both routes, three engine scans: 15-23 s
    per control repository. `tests/test_harness.py`: 5 passed in about 21 s.
