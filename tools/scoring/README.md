# The scoring job

Amendment 5's step (g): the reference `lock`, then the reference `score`, **once**, with the comparison scorer,
the corrected readings and the sensitivities beside it. Built to `docs/process/scoring_step_spec.md` (Revision 2),
on decoys only. Every choice the spec did not make is in `DECISIONS.md`.

## The command (section 3)

```
tmux new -s sa3
cd /srv/storage_16tb/projects/temporal-crucible-wt-seat
python3 -I -B tools/scoring/score_sa3.py --real --i-am-the-owner --commit <C, 40 hex> \
    --seal <run-2's public directory>/seal.json \
    --protected /srv/storage_16tb/projects/temporal-crucible-protected/score-1 --out ~/sa3-score-1
```

It prints its plan and waits for **Enter** (anything else, or no terminal, stops it with nothing written). Run it
inside `tmux`: the sandbox dies with its terminal. The checkout must be at C, with nothing untracked, modified or
ignored but `__pycache__` (an ignored `.pytest_cache/` refuses), and the annotated tag `sa3-score-C` on C.
`owner_report.json` beside the seal must say PASS on the same target with the placebo `bytes_equal`.

The ledger is `/srv/storage_16tb/projects/temporal-crucible-protected/sa3_score_ledger.jsonl` (a fixed path; any
entry refuses a start, whatever directory is named). After a start with no completion (a crash, a time-out, a
power cut): the same command with a new protected and public directory and `--rerun "REASON"` (letters, digits,
spaces and `. , ; : ( ) - /`). After a completion: never again; only

```
python3 -I -B tools/scoring/score_sa3.py --resume --real --i-am-the-owner --commit <the checkout's HEAD> \
    --receipt <the result's SHA-256 from the receipt line> --protected <the first run's> --out <the first run's>
```

which re-runs steps 11 to 14 from the result (from a fresh clone of the given commit if it is not C:
those parts are labelled "run later, on <date>") and cannot start the reference `score`.

Decoy mode, which the tests use: `--decoy DIR --ledger L` instead of `--real --i-am-the-owner`, run from a
decoy checkout (`tools/scoring/decoy.py` builds the whole route of section 2 on throwaway directories).

## Once the result exists (build review B1, M1)

One launcher at a time: each holds an exclusive lock on `<ledger>.lock` for its whole life, taken before the ledger
is read (a second one is refused, `ledger_locked`), and the ledger rule is decided again just before `started`.
After `started`, only the clone's `docs/sa3_result.json` decides: if it exists and parses, `completed` is written
first, then the receipt, then the copy to the public directory. If the copy fails the job says so and ends
`STOPPED publish_failed`: run `--resume` with the receipt (it publishes from the clone). After Ctrl-C with the
result recorded: `STOPPED interrupted`, then `--resume`. If the launcher died after the file was written and before
`completed` (the ledger shows a start with no completion), `--resume` without `--receipt`, on that run's protected
directory, adopts the result; `--rerun` is refused while that clone holds a result. With no result file (or one cut
short): `stopped`, and a second start needs `--rerun REASON`. A failed `--resume` never touches the published report:
its record is `stopped-N.md` / `stopped-N.json`.

A real run on the production study and pool always uses the production ledger and refuses
`OWNER_JOB_TEST_PROTECTED_ROOT`; any other study needs that test root (tests only).

## What the owner sees (a passing decoy run of study P, 3 min 50 s)

```
step 1 pin * ok
step 1 run2_report * ok
step 1 seal_verify * ok
step 2 clone * ok
step 3 sealed_files * ok
step 4 copy django ok
...                                   (one line per repo)
step 4 seal_inputs * ok
step 5 tables * ok
step 6 rehearse django ok
...                                   (one line per repo)
step 7 lock * ok
step 8 seal_verify * ok
step 8 after_lock * ok
step 9 score * ok
step 10 publish * ok
keep this line somewhere other than this machine: receipt sa3_result.json sha256 <64 hex> commit <C> seal sha256 <64 hex>
step 11 labels * ok
step 12 compare * ok
step 13 readings * ok
step 13 named * ok
step 13 hv_prepare django ok
...                                   (one line per repo)
step 13 variant * ok                  (PU_tracker_keys_case_sensitive: no row deleted on this decoy)
step 13 hv_build django ok            (the unmodified harvest copy, then the late-revert copy, per repo that lost rows)
...
step 13 variant * ok                  (PU_late_revert_ticket_dropped)
step 14 report * ok
The placebo gate is the `valid` field of the sealed placebo file, fixed since 2026-11-14; it cannot newly fail in this run.
report: <out>/report.md
SCORED
```

The last line is `SCORED` (the result is published), `SCORED; parts failed: <parts>` (a part after the score
failed; it never stops the report; run `--resume`), or `STOPPED <code>` (see below). The means are in the
report, not on the terminal. Any fixed sentence of section 6 that applies is printed just before `report:`.

## Stopping codes

Steps 1 to 8 stop with nothing scored and **no ledger entry** (a new attempt in new directories is still the
first scoring); steps 9 and 10 stop after `started` was written (a second start needs `--rerun REASON`). Each
code's meaning is `texts.STOP_CODES`; the step names are `texts.STEPS`.

| step | codes |
|---|---|
| before anything (exit 2) | `ledger_has_entry`, `ledger_completed`, `rerun_needs_start`, `ledger_unreadable`, `nothing_to_resume` and the command-line refusals |
| 1 | `head_differs`, `checkout_dirty`, `tag_differs`, `run2_placebo` (sentence 1 of section 6), `run2_not_pass`, `seal_not_verified`, `git_error` |
| 2 | `clone_failed`, `clone_not_clean` |
| 3 | `sealed_file_differs` |
| 4 | `copy_failed`, `input_differs`, `copy_unusable` |
| 5 | `predictor_check_missing`, `predictor_check_not_equal`, `table_hash_differs` |
| 6 | `rehearsal_failed` (sentence 3) |
| 7 | `lock_refused`, `lock_failed`, `modules_differ` |
| 8 | `after_lock_differs`, `lock_commit_differs`, `clone_status_after_lock` |
| 9, 10 | `locked`, `score_crashed`, `score_timeout`, `no_result`, `result_exists` (the score produced no result) |
| any | `invalid_report_value` (the field is named), `launcher_error` (traceback in `<protected>/launcher.log`) |
| resume | `receipt_differs` |

Once the reference score has written its result, nothing stops the job: the result is published, `completed`
written and the receipt printed first; a result whose shape is unexpected is reported as `result_shape:
unexpected` with its schema position (step 10's `result_shape` line, code `result_shape_unexpected`) and the
parts after it run, each failing with its own code if it must. A check that cannot be computed (the label tables,
the label-side check or the comparison failed) prints "The check could not be computed: <code>" and the label
gains "The check did not confirm this run" (owner ruling of 2026-11-15).

A part after the score ends `failed` with a stage code (an exception's type), or `dependency_failed`,
`code_differs`, `invalid_value`, `timeout`, `no_result`, `sandbox_refused`.

## Public files (`--out`)

`sa3_result.json` (the reference's file, byte for byte; its shape is checked after it is published), `sa3_lock.json` (the reference
lock's file), `report.md` and `report.json` (validated values only; first lines: the label of Amendment 5
section 8, any `--rerun` reason, SA3-B/C/D with the mean and interval at the Holm level and the reading as coded
and as corrected with "same" or the sentence, SA3-A's exploratory reading, the placebo gate, the check's verdict,
the sentences of section 6 that apply, every attempt and resume), `ledger.jsonl` (a copy of the ledger),
`run_log.json` (every step: name, repo, ok/failed, a code, seconds). Not published: the label tables, the
comparison's own result, the cells of the cell map, per-file values, lists of positive files: they stay in the
protected directory.

## Files

| file | what |
|---|---|
| `score_sa3.py` | the launcher (steps 1 to 14, `--resume`, the refusals) and the in-sandbox stage entry (`score_sa3.py stage NAME`) |
| `stages.py` | the in-sandbox stages: the reference `lock` and `score` and the loader rehearsal, unchanged; label tables, the label-side check, the comparison scorer and the cell map, the readings, named streams and the harvest variants, as a library from the clone's `tools/compare/` |
| `ledger.py` | "once": the ledger's rule and the attempts file |
| `schema.py` | the fixed shapes (tools/owner/report.py's checker, imported by file, plus this job's word lists) and the shape check of the reference's result |
| `texts.py` | every fixed sentence: section 6, the label, the report's paragraphs, the stopping codes, the plan |
| `report_md.py` | `report.md` from validated values; the deviation table's last column |
| `predictor_check.py` | the record of the predictor-side check (section 2 step 2) that step 5 reads: `score_sa3.py predictor-check` |
| `decoy.py` | the decoy route of section 2 for tests and the timed loop |
| `deviation_table_draft.md` | the deviation table's rows, a DRAFT for review (section 7); its last column is tokens the job fills |
| `tests/test_scoring.py` | the tests of section 9 on decoys |

Nothing here edits `tools/owner/`, `tools/harness/`, `tools/compare/` or any sealed file; they are imported by
file and called.
