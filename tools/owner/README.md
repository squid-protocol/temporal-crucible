# The owner-run preparation job

The last count, the placebo reproduced, and the seal, built to `docs/process/owner_job_spec.md` (Revision 2).
It does **not** score SA3. Every choice the spec did not make is in `DECISIONS.md`.

## The command

```
python3 tools/owner/prepare.py --real --i-am-the-owner \
    --protected /srv/storage_16tb/projects/temporal-crucible-protected/run-1 --out <a new public directory>
```

`--protected` must be a new (or empty) directory inside `/srv/storage_16tb/projects/temporal-crucible-protected/`
(the job creates it, mode 700). `--out` must be new or empty, outside the protected root and every data root. The
job first prints what it will bind and where it will write, and waits: press **Enter** to start; anything else, or
no terminal, stops it with nothing written. A second run needs a new protected directory: nothing is resumed or
overwritten.

The ordinary mode, which the tests use: `python3 tools/owner/prepare.py --decoy DIR --protected P --out O`, with
`DIR` holding `study/` (laid out like the study directory), `pool/<repo>` and `docs/`.

## What the owner sees

For a passing decoy run (two repos), exactly this, in about 4 seconds:

```
setup * ok
manifest_before * ok
seal_inputs * ok
copy ctrl-base ok
build_A ctrl-base ok
build_Aprime ctrl-base ok
count ctrl-base ok
copy ctrl-mw ok
build_A ctrl-mw ok
build_Aprime ctrl-mw ok
count ctrl-mw ok
placebo * ok
runtime * ok
manifest_after * ok
seal * ok
report: O/owner_report.md
PASS
```

The last line is `PASS`, or `FAIL` followed by reason codes. The report's first line is the same word.

- **PASS**: every repo on the frozen list (the marginals file's `ok` rows) has a determined count, the reference
  builder reproduces its stored outcome file (A equals the stored file), and the hyphen rule and the reference
  pattern never disagree; the placebo verdict is `bytes_equal` or `numbers_equal`; the seal was written; every
  module the reference scorer loaded, and `hist_meta`, is unchanged since `8fb7fe0` (checked with git on this
  checkout; owner ruling, 2026-11-14); the label-side manifest is unchanged.
- **FAIL** codes: `count_not_determined`, `a_differs_from_stored`, `pattern_disagreements`, `placebo_differs`
  (stop: nothing after this job proceeds), `placebo_failed`, `placebo_not_run`, `seal_not_written`,
  `inputs_changed_during_run`, `reference_code_changed` (a reference module differs from `8fb7fe0`),
  `reference_code_unchecked` (git could not make the check: git unavailable, or the commit absent),
  `manifest_changed`, `manifest_failed`, `setup_failed`, `no_repos`,
  `invalid_report_value` (a stage returned a value outside its fixed shape; the terminal names the field),
  `launcher_error`.

Do not paste anything from the protected directory into a session. Do not re-run to see if it passes.

## Public files (`--out`)

`owner_report.md` / `.json` (per repo: determined, reason, the count, A equals the stored file, disagreements; the
placebo verdict, largest difference, how many numbers differ, versions; the seal's entry count and the modules
found; the manifest's unchanged yes/no and entry count), `seal.json` (hashes only), `run_log.json` (stages, repo,
ok/failed, a reason code, seconds). Written only by `report.py`, after every value has passed a fixed shape.

## The seal

```
python3 tools/owner/seal.py verify --seal O/seal.json --protected P2 --real --i-am-the-owner [--after-lock]
```

recomputes the seal (in the read-only sandbox, into a new protected directory P2) and prints `differs: <entry>`
for each entry that changed, then `VERIFIED` or `DIFFERS N`. `--after-lock` also checks `docs/sa3_lock.json`, after
the owner has run the reference `lock`, against the nine hashes it is expected to hold.

## Files

| file | what |
|---|---|
| `prepare.py` | the launcher, the refusals, and every in-sandbox stage (`prepare.py stage NAME`) |
| `tracker_keys.py` | the A' harvest, the two unchanged calls of `sa3_outcomes.build`, the count and its checks |
| `placebo_check.py` | the reference `stage_placebo` from a copy, the comparison, the import recorder, the runtime fingerprint |
| `seal.py` | the seal's composition, `verify`, `verify --after-lock` |
| `report.py` | the fixed lists, the schemas, the validator, the only writer of the public directory |
| `tests/test_owner_prepare.py` | 21 tests on decoys, about 1 to 2 minutes |

The one change outside this directory: `tools/harness/sandbox_ro.py` allows directories strictly inside the
protected root as read-write locations.

## For the scoring step

The reference `lock` must be run where git works on a real checkout of this repository. Observed on decoys
(`tests/test_owner_prepare.py`, test 4), with `python3 -I -B <root>/tools/sa3_score.py lock` run unchanged inside
`tools/harness/sandbox_ro.py`'s sandbox, `<root>` holding copies of `tools/` and of the decoy's `docs/`:

- `<root>` carrying only the `.git` file of a linked worktree (`gitdir: <a directory that does not exist>/worktrees/x`),
  which is what this checkout looks like in any sandbox that does not also bind its main repository: `lock` exits 0
  and writes `docs/sa3_lock.json` with `"sealed_at_commit": ""` and all nine `"files"` values `""`.
  `seal.py verify --after-lock` then prints `differs: lock.<file>` for each of the nine and `DIFFERS 9` (exit 1).
  The reference `score` would compare empty with empty and proceed.
- `<root>` with no `.git` at all: `lock` writes the correct nine blob hashes (`git hash-object` needs no
  repository) and an empty `sealed_at_commit`.
- `<root>` a git repository with everything committed: `lock` writes the nine hashes `seal.json` expects (its
  `lock_expected`) and the commit; `verify --after-lock` prints `VERIFIED`.

So the scoring job must run `lock` where git can read the repository (a linked worktree needs its main repository's
`.git` bound too), and must run `seal.py verify --after-lock` after `lock` and before `score`.
