# The harness — run the existing SA3 code on a control repository (build specification)

**Status: specification, 2026-11-14. Nothing built.** This is step 0 of `research_codebase_spec.md` and phase 2
of `control_repo_spec.md`. Built by one session from this document; reviewed by a different model.

**Purpose.** Push a generated repository with a known answer through SA3's pipeline **as it is**, and report,
rule by rule, where the pipeline and the manifest agree. No SA3 tool is edited. The first product is a table,
not a fix.

## The one hard requirement: the real study data cannot be touched

The SA3 tools are hard-wired to the study directory (`/srv/storage_16tb/projects/gitgalaxy/laws-study/pilot`),
write there, and one deletes an input there. A promise not to run them wrongly is not enough (defect log 49).
So every SA3 tool, the engine and every git call of the pipeline runs **inside a sandbox made with `bwrap`**
(installed at `/usr/bin/bwrap`), in which:

- the whole filesystem is read-only;
- the study directory's path is a fresh temporary directory (`WORK/study` bound over
  `/srv/storage_16tb/projects/gitgalaxy/laws-study/pilot`), so the unmodified tools read and write the
  temporary one;
- the rest of `/srv/storage_16tb/projects/gitgalaxy/laws-study` is hidden, **except** the frozen engine export
  `engine-f71181aae7`, bound read-only (it is code);
- `/nvme-data` (the corpus clones), `/srv/storage_16tb/projects/temporal-crucible-pool`, `~/.blind`, `~/.ssh`
  and `~/.claude` are hidden;
- the network is unshared;
- only `WORK` is writable. The repository pool is `WORK/pool` (the tools take it from the `EXPOSURE_POOL`
  environment variable). The tools run from a **copy** of `tools/` and the `docs/` files they read, under
  `WORK/tree`, because several read and write paths relative to the repository.

`WORK` is under pytest's temporary directory or the session's scratch directory, never in the worktree.

**Tests of the sandbox itself (they run first, and need no engine):**

1. Inside the sandbox, a write to the study directory's path lands in `WORK/study` and nowhere else.
2. Inside the sandbox, a write anywhere outside `WORK` fails.
3. Inside the sandbox, the corpus directory and `~/.blind` are empty or absent, and a network connection fails.
4. The harness refuses to start a pipeline stage outside the sandbox (a guard in the runner, tested).

Outside the sandbox the builder never opens, lists or stats the study directory, `/nvme-data` or `~/.blind`.
The proof that they were untouched is that they were not reachable.

## What runs

For one control repository (`DIR/repo`, `DIR/manifest.json`), the SA3 route in the order the code needs it.
The inventory of 2026-11-14 gives this order; the builder confirms it from the code:

`laws_history` (the commit walk) → `mod1_lift` (the frame: cut, window, snapshot) → `sa3_scan` (the engine
scan of the snapshot) → `sa3_outcomes` (which harvests commit bodies through `hist_meta` and builds the
outcome file) → `sa3_nest_scan` → the marginals file → `sa3_score placebo` → `sa3_score lock` and `score`.

- **Unmodified code.** Where a tool cannot run on a generated repository without a change, the harness
  supplies the missing input from outside (a file it writes into `WORK`, an environment variable, a
  command-line argument). Each such supply is a **shim**, listed in `DECISIONS.md` with what it replaces and
  why. Editing a file under `tools/` (other than `tools/harness/`) is not allowed; if a stage cannot be made
  to run without that, the harness stops there and reports the stage, the line and the reason.
- **The snapshot.** Run twice: once letting the pipeline choose its own snapshot, once passing the manifest's
  snapshot. Both are reported; the comparisons below use the second.
- **The marginals file** is written by no tool. The harness builds it from the outcome file's own
  `clears_floor` values, and says so.
- **`lock` and `score`** need committed files and a code-review document. Go as far as the code allows; report
  where it stops.
- **Time one engine scan** of a default-profile control repository before anything else and write the number
  down: the size of every later test suite depends on it.

## What is compared — the first three-way table

For each row: what the pipeline produced, what the manifest says, and one of *agree* / *differ* / *undecided in
the manifest*. A row is never empty.

| rule | pipeline side | manifest side |
|---|---|---|
| snapshot | the commit the pipeline chooses | `points.snapshot` |
| window | start and end | snapshot + 730 days |
| universe | the unit files (`sa3_outcomes.universe`) | files with `is_unit` at the snapshot, each difference with the manifest's reason |
| scan completeness | the share the pipeline computes | 100% expected |
| LOC | the scan's `total_loc` per unit file | `properties.snapshot.loc` |
| branch keywords | the scan's `struct_branch` | `branches`, by the stated mapping |
| nesting | `sa3_nest_scan` | `max_nesting` |
| calls in | `in_degree` as the scorer computes it | `calls_in` |
| pointer and allocation counts (C) | the scan's keyword families | `pointer_ops`, `pointer_declarations`, `alloc_ops` |
| bots | commits flagged bot | commits of type `bot` and bot-authored merges |
| tree-wide commits | the pipeline's set | the manifest's |
| HP qualifying commits | the outcome file's commit list | `expected_labels` with `counted: true`; ambiguous ones listed apart |
| HP positive files | the outcome file's file list | the union of expected positives |
| keyword outcome | the KW list | fixes with the keyword convention and no reference |
| control pool | its commits | commits that are not fixes, not tree-wide, not bots |
| floors | `clears_floor` | recomputed from the manifest |
| planted effect | the scorer's effect for each planted property against HP | the same statistic (`tools/sa3_stats.py`, called directly) on the manifest's expected labels |

Run on, at least: a negative control and a positive control (`--effect branches=0.5`), Python, default profile,
`--years 10` (so the window is a full 730 days); the same pair in C; and these mutations of the Python negative
control: `merge_workflow`, `bot_merges`, `sweep_labelled_fix`, `renames_after_snapshot`, `vendored_half`,
`mixed_language`. For each mutation the report says, in one line, what the pipeline did with the planted fault.

## Deliverables

```
tools/harness/
  sandbox.py     build and enter the bwrap sandbox; the guard
  run.py         run the pipeline on one control repository: python tools/harness/run.py --control DIR --work WORK
  compare.py     the three-way table: JSON and a Markdown report
  README.md
  DECISIONS.md   every shim, every choice this document did not make, every stage that could not run
tests/test_harness.py   the four sandbox tests (always); one small end-to-end run, skipped with a clear reason
                        if the engine export or the tree-sitter pack is absent
```

Reports go under `WORK`. The builder does **not** write a report into `docs/`; the reviewer does, after
checking it.

## Rules for the builder

- Write only `tools/harness/` and `tests/test_harness.py`. No commits.
- Read `tools/` and `docs/` freely. Read the engine export only as far as needed to invoke it.
- No study data, no corpus clone, no `~/.blind`, by any route. No network.
- One pipeline run at a time; the machine is shared. Git with `GIT_NO_LAZY_FETCH=1` and `gc.auto=0`.
- Do not "fix" a disagreement by changing what is compared. A disagreement is the product.
- When finished, report: what was built; the scan time; the sandbox test results; every shim; the three-way
  table for each run, summarised (rows that agree, differ, undecided), with the largest differences described
  concretely; every stage that could not run; anything in this document that is wrong or impossible.
