# SA3 harness

Runs the **existing, unmodified** SA3 pipeline on a generated control repository (`tools/control_repo/`) inside
a `bwrap` sandbox, and writes the first three-way table: per rule, what the pipeline produced, what the
manifest says, and *agree* / *differ* / *undecided in the manifest* (or *not run*, with the stage that stopped).
Built to `docs/process/harness_spec.md`. Every choice that document did not make, every shim and every stage
that could not run is in `DECISIONS.md`.

## Use

```
python3 tools/control_repo/generate.py --out DIR --seed 11 --years 10 [--language c] [--effect branches=0.5] [--mutation NAME]
python3 tools/harness/run.py --control DIR --work WORK [--name NAME] [--routes own,manifest] [--no-shim-lock]
python3 tools/harness/compare.py --work WORK --name NAME --control DIR      # re-make the table from a finished run
python3 tools/harness/sandbox.py shell --work WORK -- CMD...                 # run anything inside the sandbox
python3 -m pytest -p no:cacheprovider tests/test_harness.py                  # 5 tests, about 20 s
```

`WORK` must be under `/tmp` or `~/.claude/jobs/` (the sandbox refuses anything inside this repository or a data
root). The report is `WORK/report/NAME.md` and `NAME.json`; the raw run record (every stage's argv, return
code, time and output tail) is `WORK/report/NAME.run.json`. One default-profile control repository takes about
15 s for both routes (each engine scan about 2.4 s).

## What runs

Two routes, each in its own sandbox WORK (`WORK/own`, `WORK/manifest`) with its own copy of `tools/`, its own
study directory and its own clone:

| route | stages (all unmodified tools, all inside the sandbox) |
|---|---|
| `own` (the pipeline chooses its snapshot) | `mod1_run.py` (history walk, MOD-1 body harvest, the cut, `laws_build` scan of the cut) → `mod1_lift.py --out docs/mod1/lift_NAME.json` → `sa3_scan.py` |
| `manifest` (the manifest's snapshot handed in) | `laws_history.py` with `mod1_run`'s exact arguments → `sa3_scan.py --sha <points.snapshot.hash>` |
| both, then | `sa3_outcomes.py` (runs `hist_meta.py`) → `sa3_nest_scan.py` → the marginals file (written by the harness from the outcome file; no tool writes it) → `sa3_score.py placebo` → `lock` → `score` → `probe.py` |

The table uses route `manifest`; the snapshot row compares route `own`'s choice with the manifest. In route
`manifest` only, after `lock` stops for its missing code review, a placeholder review is written and `lock` and
`score` are run again, to see what they do past that stop (shim 13 in `DECISIONS.md`; `--no-shim-lock` skips it).

## The sandbox (`sandbox.py`)

Mount order (bwrap applies arguments in order; bind sources are resolved on the host):

1. `--ro-bind / /`, `--dev /dev`, `--proc /proc`
2. empty tmpfs over `/nvme-data`, `/srv/storage_16tb/projects` (the rest of laws-study, the pool, every other
   checkout, this worktree), `/home/joe` (`~/.blind`, `~/.ssh`, `~/.claude`, `~/.cache`) and `/tmp`
3. `--ro-bind` the engine export `laws-study/engine-f71181aae7`, and the user site-packages (where
   `tree_sitter_language_pack` 1.20.0 lives), with its gitgalaxy editable-install `.pth` blanked by `/dev/null`
4. `--bind WORK/study` at the study directory's path, `--bind WORK WORK`, `--bind WORK/shm /dev/shm`, and the
   host's tree-sitter grammar cache v1.20.0 read-only under `WORK/home/.cache/`
5. `--remount-ro` every tmpfs of step 2 and `/dev`
6. `--unshare-net --unshare-ipc --unshare-pid --unshare-uts --die-with-parent --new-session --clearenv`, an
   explicit environment (HOME = `WORK/home`, `EXPOSURE_POOL` = `WORK/pool`, git with `GIT_NO_LAZY_FETCH=1`,
   `gc.auto=0`, no system config, a ceiling directory), `--chdir WORK/tree`

The guard (`sandbox.py exec`, `sandbox.assert_inside`, `run.stage`) decides "inside or not" from
`/proc/self/mountinfo` before it touches any path: it needs a mount at the study path, read-only tmpfs over every
hidden root, a read-only `/`, the study path being WORK/study itself (same device and inode) and no network
interface but `lo`. Every stage is started through it.

## Files

- `sandbox.py`: the mounts, the environment, the guard, `run()`.
- `run.py`: the two routes, the marginals file, the run record.
- `probe.py`: runs inside the sandbox; reads what the pipeline produced through the tools' own functions
  (`frame`, `universe`, `sa3_score.load`, `design_for`, `silent`, `Design.effect`) into `WORK/<route>/probe.json`.
- `compare.py`: the three-way table (JSON and Markdown). Imports only `tools/sa3_stats.py` (pure functions).
