# The scoring job's build — independent review

Reviewed: `tools/scoring/` and `tests/test_scoring.py` at `66b6c2f` (branch `sa3/build`), against
`docs/process/scoring_step_spec.md` (Revision 2, with the ruling that a check which cannot be computed is "not
confirmed" and that the result is always published once it exists). Reviewer: an independent Claude session that
did not write the code. 2026-11-16. Decoys only; nothing was run with `--real` outside the existing test 8; no
forbidden path was opened.

## Verdict

**Ready after changes. Not ready for the owner as it stands.** The design holds: the stages run from the fresh
clone, `--resume` has no path to the reference `score`, `started` is written and fsynced before the score starts,
the pin refuses what it should, and the report reads the right keys of the reference's result. But one family of
failures breaks the two rules that matter most on a run that cannot be repeated. If the public directory stops
taking writes while the score runs, or the score stage ends "failed" after the reference has already written its
file, the result exists in the clone, the ledger shows a start with no completion, and the job prints "no result
was published: a second start needs --rerun REASON". Nothing in the code can adopt that result; the only way
forward it offers is a second start of the reference score. That is one blocker. Five majors sit beside it: two
launches can both pass the ledger rule; a test variable moves the ledger of a `--real` run; a failed `--resume`
overwrites the published report with "nothing has been scored"; the stopping sentences are chosen by step number,
not by what the ledger holds; and the deviation table draft lacks rows its own sources name. All are small
changes with a decoy test each. Counts: **1 blocker, 5 major, 11 minor.**

## Blocker

### B1. A result that exists can be stranded, and the job then asks for a second start

*Run on decoys (experiments E2, E3 below) and verified in code.*

The spec (section 3, "the result is published the moment it exists; nothing after it can strand it"; section 6,
"the ledger records `completed` regardless") is met only on the path where the score stage reports `ok` and every
write to the public directory succeeds. Three paths leave a written result unpublished and the ledger open:

1. **The public directory stops taking writes during the score** (full disk, a permission change, the mount
   gone). `run_stage` ends with `self.record(...)` (`score_sa3.py:290`); `record` calls `save_log`
   (`:236`), which writes `run_log.json` in the public directory with `atomic` (`:245`) and catches only
   `ReportError`. The `OSError` leaves `run_stage` for step 9 before `step10_publish` is ever called. `main`'s
   last handler (`:1222`) turns it into `stopped(... "launcher_error")`. In `step10_publish` itself the same
   holds for every line before `completed`: `tmp.write_bytes` (`:627`), `os.replace` (`:628`), the lock file's
   copy (`:629-630`), the re-read (`:632`). `completed` is written only at `:633`, after all of them.
2. **The score stage ends `failed` although the reference wrote its file.** The reference writes
   `docs/sa3_result.json` at `tools/sa3_score.py:500` and only then prints its summary (`:501-507`) and
   returns. Anything that raises after line 500 — the print loop, a write to a full `stage.log`, the stage's own
   `loaded_modules()` or its `result.json` write (`score_sa3.py:143-146`), a launcher-side `modules_differ`
   (`:283-284`) — gives `res["status"] != "ok"`. `step10_publish` looks at the stage's status first
   (`:611-612`) and at the file last (`:617`): it writes `stopped: score_crashed` and raises `Stop(10)`.
3. **Ctrl-C, or a kill of the launcher, between the reference's write and line 633.** `KeyboardInterrupt` is not
   an `Exception`; nothing is written.

In each case `stopped()` prints (`:990-992`) "A start is recorded in the ledger and no result was published: a
second start needs --rerun REASON", and `render_stopped` writes the same into `report.md`
(`report_md.py:291`). `ledger.decide` then allows `--rerun` (`ledger.py:98-99`) and refuses `--resume`
(`ledger.py:89-90`, `nothing_to_resume`). `resume()` also needs the public copy (`score_sa3.py:1058-1061`). So
the only route the job offers is to start the reference score a second time, with a first result lying in
`<protected>/clone/docs/`. "Once" (section 5) says a second start is allowed because "nothing was seen" — true
of the owner, but the result exists, and the stage log beside it holds the printed means.

How likely: low. The disks have room today, and I found nothing in the reference's last lines that raises on the
decoys. But this is the one case the spec's Revision 2 was written to close, the run is the only one, and the
cost of the fix is small.

**Fix.**
- In `step9_score`/`step10_publish`, after `started`, decide on the *file*, not on the stage's status: if
  `<clone>/docs/sa3_result.json` exists and parses as a JSON object, a result exists. Then, in this order:
  append `completed` with its SHA-256 (the ledger is on the same disk as the clone); print the receipt and the
  result's path in the clone; only then copy to the public directory, inside `try`. A failed copy prints one
  fixed line ("the result exists and is recorded; it could not be published; run --resume") and ends non-zero,
  never through `stopped()`.
- Make `--resume` publish the result from the clone when the public directory lacks it (SHA-256 checked against
  the ledger's `completed` and the receipt), instead of `receipt_differs`.
- `Job.record` and `save_log` must not raise: catch `OSError`, write the traceback to `launcher.log`.
- Wrap steps 9 and 10 so that *any* exception after `started` goes through the same "does the file exist?"
  decision. A file that exists but does not parse (a write cut short) is `stopped` with its own code.
- If the stage ended `failed` with `modules_differ` and a result exists, the result is not known to be the
  pinned code's. That case needs the owner's ruling now (publish with a fixed sentence, or `stopped`); either
  way the job must say that a result file exists.

**How to test the fix.** (a) Experiment E2 as a test: make the public directory read-only as the score stage
starts; expect ledger `started, completed`, the receipt on the terminal, a non-zero exit with the fixed line;
then restore the directory and `--resume`: `SCORED`, and the public result equals the clone's byte for byte.
(b) Experiment E3 as a test: let the stage wrapper report `failed` after the file is written; expect published
and `completed`, no `--rerun` allowed. (c) Write half a JSON document into the clone's result path and report
the stage `failed`: expect `stopped`, and `--rerun` allowed. (d) Raise `KeyboardInterrupt` in the wrapper after
the file exists; then `--resume` must adopt the result.

## Major

### M1. Two launches can both start the score; `--rerun` can start one beside a running one

*Run on decoys at unit level (E4); reasoned for the full job.*

The ledger is read once, in `main` (`score_sa3.py:1187`), before the plan. `step9_score` (`:595`) appends
`started` without reading it again and without a lock. Steps 1 to 8 take minutes on a decoy and longer on the
real study; a second launch inside that window, with other directories, also reads an empty ledger, gets
`first`, and reaches step 9. Both start the reference score. Likewise, while a first score is running the ledger
holds `started` with no completion, so `--rerun REASON` in a second window is accepted (`ledger.py:98`). E4:
two `decide` calls on an empty ledger both return `first`; two `step9_score` calls on one ledger start the stage
twice and leave `started, started`.

**Fix.** Take an exclusive `flock` on `<ledger>.lock` in `main` before `decide`, hold it until the process ends,
refuse with a fixed message if it is held. In `step9_score`, re-read the ledger and repeat `decide` immediately
before the append. **Test:** E4 turned round (the second `step9_score` must raise and start nothing); a child
process holding the lock makes `main` exit 2 with nothing created.

### M2. `OWNER_JOB_TEST_PROTECTED_ROOT` moves the ledger of a `--real` run on the real study

*Run (E5: string tests only, nothing opened) and verified in code.*

`places()` calls `P.test_root_from_env()` first (`score_sa3.py:1119`). On a real run the ledger is
`next(r for r in SR.protected_roots() if r in prot.parents) / LEDGER_NAME` (`:1146-1147`). With the variable
set and `--protected` under the named root, a `--real --i-am-the-owner` run with the *default* study and pool
paths gets its ledger under `~/.claude/jobs/...`. E5 printed exactly that: ledger under my scratch root, study
`…/laws-study/pilot`, `real: true`. `allowed_tables_dir` (`:511`) accepts the same root. So the answers to the
brief's questions are: the production default is exactly
`/srv/storage_16tb/projects/temporal-crucible-protected/sa3_score_ledger.jsonl`; `--ledger` is refused on a
real run (`:1144-1145`); `SCORE_SA3_TEST_FAIL` is inert on a real run (refused at `:1120-1121`, never read
again: `Job.fail_stage` is `None` when `tgt.real`, `:229`; the sandbox clears the environment); but **the
owner job's test variable is not inert**. It needs a deliberate act and is announced on stderr and in the plan,
so it is not a blocker. The reverse also holds: `--real --real-study <elsewhere>` under the production root
writes `started`/`completed` into the production ledger and would shut out the real run.

**Fix.** On a real run, when the study or pool path is the production one, refuse the test variable and use the
constant `SR.PROTECTED_ROOT / LEDGER_NAME`; when either path is not the production one, require the test root
(so the production ledger can only ever record the production study). **Test:** `places()` with the variable
set and default paths is `Refused`; test 8 still passes; `--real-study X` without the variable is `Refused`.

### M3. A failed `--resume` replaces the published report with "nothing has been scored"

*Run on decoys (E1) and verified in code.*

`resume()` sends every early failure to `stopped()` (`score_sa3.py:1061-1069`, `:1091`), and so does `main`'s
last handler for any later one. `stopped()` calls `write_stopped` (`:994`), which writes `report.json`,
`report.md` and `ledger.jsonl` in the public directory with `atomic` (`:944-946`) — no `superseded` copy; that
is done only in `write_report` (`:914-919`). A mistyped receipt, a checkout that is not clean, or a HEAD that
moved is enough. E1 (a wrong receipt on a copy of a completed decoy run): the full report was replaced by a stopped record saying nothing has been scored, with no copy kept.

**Fix.** `stopped()` must never touch `report.*` when the ledger holds `completed`; write
`resume_stopped-N.md` instead (or supersede first). **Test:** E1 with the assertion that `report.md` and
`report.json` are byte-identical before and after.

### M4. The stopping sentences follow the step number, not the ledger

*Verified in code; the resume case run on decoys (E1).*

`stop_sentence` (`score_sa3.py:950-957`) and `render_stopped` (`report_md.py:286-292`) pick the sentence from
`step` alone. Wrong sentences result:

- `--resume` stopped at "step 1" prints "A check before the score failed … nothing has been scored. The ledger
  has no entry, so a new attempt is still the first scoring." after a completed score.
- A `--rerun` attempt that stops in steps 1 to 8 prints "The ledger has no entry" while it holds `started`.
- An exception after `started` but before the score's `record` (e.g. `run_stage`'s `mkdir`, an invalid stage
  result at `:278`/`:282`) is reported by `main` as the last *recorded* step, 8 (`:1221`, `:1225`): the
  "before the score" sentence, with `started` in the ledger.
- A launcher error after `completed` (any `OSError` from `record`, `:636`, `:663`, or in steps 11 to 14 outside
  `part`) is reported as step ≥ 9: "no result was published: a second start needs --rerun" — false; and steps
  11 to 14 do not run, and `finish` is skipped.
- A launcher error whose last recorded step is 6 prints the rehearsal sentence.

Section 6 wants each row to print exactly its sentence. **Fix.** Choose from the ledger's state read at that
moment: no entry → rows 2/3; `started` without `completed` → the step-9 line (after B1's file check);
`completed` → "the result is published; run --resume", never a "nothing scored" line. Everything after
`completed` should be inside one `try` that ends in `finish`. **Test:** one unit test per bullet, asserting the
exact terminal lines and that `SENTENCES["before_score"]` is absent when the ledger is not empty.

### M5. The deviation table draft is not complete against its named sources

*Reasoned, not run: read against the documents by a second reader I briefed; I spot-checked the citations
marked †.*

Section 7 names Amendments 4 and 5, both errata, the reading note and defect-log entries 42 to 64. Against
those, the 19 rows cover defects 42-48, 54-59, 61, 62 and 64, and the four corrections of Amendment 5 section 4
are exactly rows 1 to 4. Missing or wrong:

Rows to add:
1. **S5** (tree-wide commits left in): registered, never coded, reported not run. The draft has S8 only
   (`docs/sa3_registration.md:196`, `:518`†; `tools/sa3_score.py:358`).
2. **`dampened_flux`**: a registered D secondary the pinned engine does not emit (`sa3_registration.md:519`†;
   `tools/sa3_score.py:69`).
3. **"Every one is run" is not met**: five reported equal from counts, two not run.
   `docs/process/comparison_scorer_part2_spec.md:197-199`† says this deviation is "stated here and in the
   result's deviation table". The draft never states it.
4. **The size-surrogate adjustment**: each primary is also reported minus its surrogate mean (Amendment 4,
   `sa3_registration.md:504-506`). Row 18 covers the gate only.
5. **The rest of the post-leak scorer changes** in Amendment 4's "Scorer faults fixed" table
   (`sa3_registration.md:512-516`†): the matched control filled a missing value with zero and now uses the same
   rows (this touches the "defect-specific" reading); eight registered-but-not-coded items were coded after the
   leak. Row 5 names two of five.
6. **A bot's brought-in commit taints a merge** (registration `:304` against Amendment 5 section 5,
   `:682-684`).
7. **Trailers are read from the body only and need a value** (`:670-672`).
8. **Two keyword rules stay as coded** (owner ruling, `:777`).
9. **Defect 60** (the placebo stage crashes when no repo clears the floor†): one line, "cannot occur on the
   frozen list"; and a footnote that entries 49, 50-53 and 63 are not SA3 code-or-registration differences. The
   spec names 42 to 64, so a reader will look for each.

Rows to correct:
- Row 3: "for every summary of every cut" is wider than defect 47 (outside the three confirmatory tests,
  including the exploratory measure and when the gate has failed); the exploratory test's corrected words are
  "positive"/"negative", not "above/below zero".
- Row 4: the corrected set also requires the cell's status to be ok (`tools/compare/reading.py:159-167`). "18
  repos against 15" are floor counts from the marginals file, not the n compared; say "up to".
- Row 5: the silence change is "the clause applies to continuous scores only" (it also un-silenced the yes/no
  indicator and nesting depth, `sa3_registration.md:513`†); "14" is the count measures only.
- Row 6: the registration does fix the draws and the seed (`:287`); what it leaves open is one stream or many.
- Row 10: the sentence is in the registration itself (Amendment 3, `:430`), not only the consolidated text.
- Rows 11 and 16, "who decided": the decision not to run is part 2's spec, not Amendment 5 section 6 or
  Amendment 4's words.

**How to test:** a test that every defect number 42 to 64 appears in the committed table (row or footnote), that
every name in `variants.TABLE` and both keys of the reference's `not_run` and `UNAVAILABLE` appear, and that
every `{{run:...}}` token is one `fill_deviation` knows (this last one holds today).

## Minor

1. **The checkout is refused today.** `.pytest_cache/` is ignored and present; `pin_problems` returns
   `checkout_dirty` (`score_sa3.py:183`). *Verified (git status).* DECISIONS item 1 says so; the hand-over must
   tell the owner to remove it. My own test runs used `-p no:cacheprovider` and added nothing.
2. **The pin does not see a file hidden from `git status`.** *Run on a scratch copy (E7), result below.* The
   launcher's own modules run from the checkout and are never compared with `git ls-tree` (the stages' are).
   Fix: hash the launcher's loaded `tools/**.py` against the commit's blobs in step 1, as `modules_match` does.
   Test: E7 must give `checkout_dirty`.
3. **An unexpected shape withholds every headline number** (`score_sa3.py:772-776`), although each number read
   is validated one by one by `REPORT`. I checked `schema.check_result`'s keys and words against
   `tools/sa3_score.py:356-499` and found none missing, so this should not fire; if it does, the owner's first
   report has no means. Reading the three tests in their own `try` would cost nothing. Test: test 3g, asserting
   the means are present.
4. **`minimal_report`** (`:1043-1049`) writes the plain label: no "the check did not confirm this run", no
   section 6 sentence, though both were just printed. Reasoned.
5. **`stopped()` can itself raise** (`LG.append` at `:983`, `save_log` at `:999`): a traceback on the terminal
   and no `STOPPED` line. Reasoned. Wrap both.
6. **The `started` entry does not record the protected directory**, so a `--rerun` cannot check the first run's
   clone for a result (see B1). Reasoned. A directory *name* under the root would pass a fixed pattern.
7. **The label stage keeps the 7,200 s time-out** (`after_score`, `:701`) and builds and checks 40 repos in one
   stage; it was never timed on real sizes. A time-out there now reads "the check could not be computed" and
   adds "did not confirm" to the label. Give it the score's time-out. Reasoned.
8. **Stale words.** `ledger.py:14-15` ("completed … after the result was checked and published"; "stopped … an
   invalid result"), DECISIONS item 16 ("a result without the reference's shape"), README ("byte for byte, after
   a shape check") describe the build before the "published first" change. `score_sa3.py:88`: the "TESTS ONLY"
   comment sits on `VERIFY_NAME`, not on `TEST_FAIL_ENV`.
9. **The launcher is started as plain `python3`**: it reads the checkout's `__pycache__` and honours
   `PYTHONPATH`. The pin allows ignored `__pycache__`. Tell the owner to delete them and start with
   `python3 -I -B`, or refuse `.pyc` files beside launcher modules. Reasoned.
10. **`step10_publish` order differs from the spec's** (publish, then `completed`; the spec says `completed`,
    then publish). Covered by B1's fix.
11. **Report times are UTC.** A public file, so defensible; the owner reads Eastern. Reasoned.

## What I checked and found sound

- **`--resume` cannot reach the score.** `resume()` (`:1052-1107`) calls `shape_check`, `step2_clone` (other
  code only), `safe_after`, `finish`. `after_score` names only `labels`, `compare`, `readings`, `named`,
  `hv_prepare`, `hv_build`, `variant`; it passes no `rw` directory, so the clone's `docs/` is never writable.
  `st_score` refuses when a result exists (`stages.py:111-112`). `stage score` by hand needs the sandbox
  (`:128`). No environment variable selects a stage. Verified in code; tests 1e, 3b pass.
- **`started` before the score.** `ledger.append` writes, flushes, fsyncs, and fsyncs the directory when new
  (`ledger.py:61-74`); it is the first line of `step9_score`; an exception there starts nothing.
- **The pin.** HEAD, `--ignored --untracked-files=all`, the tag's commit (`:174-189`); tests 4a pass.
- **The clone from this linked worktree.** Decoys launch from a plain clone; the real launch is from a linked
  worktree. I ran step 2's exact git commands from this worktree into my scratch directory: clone of the common
  directory, detached at HEAD, status empty, no alternates, no `commondir`, no hard links, `8fb7fe0` present.
- **Stages run the clone's code.** `argv` names the clone's `sandbox_ro.py` and `score_sa3.py` (`:262-264`);
  `-I -B`; every hidden root is a tmpfs, so the checkout is absent inside; `loaded_modules` and `modules_match`
  compare bytes with `git ls-tree`. The recorder cannot see a module outside the clone's `tools/`, but none is
  reachable inside the sandbox except the system's packages, which the seal's runtime entry covers.
- **Real mode, line by line.** `check_rw` takes its protected-root branch for every read-write directory; the
  step-8 `seal.py` runs from the clone, where `WORKTREE` is the clone, and its own directory is beside, not
  inside, it; `seal.py verify --real` asks nothing on stdin; the loader inside the sandbox reads the same
  compiled-in paths on decoys and on real data, so the bind set that passes the rehearsal for all ok repos is
  the one the score gets (the score has `docs/`, `.git`, `tools/` only; the reference reads nothing else under
  its root). Test 8 exercises `--real` with a test root under `/tmp` — the other branch of `check_rw`; the
  production branch is reasoned, not run.
- **Report content.** `result_lines` reads `tests[n].bauc.{n,mean,ci}`, `tests[n].holm_level`,
  `tests[n].reading`, `tests.in_degree.{bauc,reading}`, `valid` — the keys `sa3_score.py:424-447` writes; a
  "not fitted" summary has no mean and prints n/a. The Holm level printed is the stored one (98.33%, 97.50%,
  95.00%). `reading.beside` recomputes the coded word and fails if it is not the stored one; `corrected` and
  `applies` follow the note. The exploratory interval is the reference's 95%.
- **Publication.** Every stage result passes `validate_stage`; every public file is built from `REPORT`,
  `STOPPED` or `RUN_LOG` values, except the deviation table and `variants.TABLE` texts (committed) and the
  result itself (by design). Test 2c (markers) passes.

## What I ran

- `tests/test_scoring.py` without tests 6a-6e (they read the blind test's copies, which my rules forbid me to
  open): **29 passed, 5 deselected, 40 min 12 s** (`COMPARE_STUDY_CACHE` reused, a fresh route cache, `-p no:cacheprovider`).
- E1 to E5, E7 (my own file under `~/.claude/jobs/24bf9d40/tmp/scoring_build_review/exp/`, decoy route P):
  - E1 (`--resume` with a wrong receipt on a copy of the completed run P): exit 1, `STOPPED receipt_differs`. The terminal printed "A check before the score failed: the job stopped; nothing has been scored. The ledger has no entry, so a new attempt is still the first scoring." `report.md` was replaced: it now begins `STOPPED at step 1 … receipt_differs` and carries that same sentence; `report.json` holds only the stopped record; no `superseded` copy was kept. The ledger still reads `started, completed`.
  - E2 (the public directory made read-only as the score stage starts): `step 9 score * ok`, then "stopped at step 9 … launcher_error" and "A start is recorded in the ledger and no result was published: a second start needs --rerun REASON.", then `main` itself raised `PermissionError` (no `STOPPED` line). Ledger: `started` only. The result is in the clone, not in the public directory; no receipt was printed. `decide` then answers `rerun` to `--rerun` and `nothing_to_resume` to `--resume`.
  - E3 (the score stage reported `failed` after the reference wrote its file): `step 10 publish * failed score_crashed`, the same "no result was published … --rerun" line on the terminal and in `report.md`, `STOPPED score_crashed`. Ledger: `started, stopped`. The result is in the clone, not published. `decide` answers `rerun`.
  - E4: both launches decided `first`; the score stage was started twice; ledger `started, started`.
  - E5: `--real` with default study path and the test variable: ledger under the test root.
  - E7 (`git update-index --assume-unchanged tools/scoring/texts.py`, then the file changed, on a scratch copy of the route's checkout): `pin_problems` returned no problem; with the bit cleared it returned `checkout_dirty`.
- Step 2's git commands from this worktree (above).

## What I did not check

- Tests 6a-6e (section 6 on the blind copies): not run, for the reason above. Section 6 was checked in code and
  by test 1g only.
- Anything on real data: sizes, times, the real tables, the real seal, run-2's report. The run-time estimate is
  not re-derived.
- The production branch of `check_rw` and the production ledger path, except as strings.
- `tools/compare/` internals beyond the functions the stages call; `tools/owner/placebo_check.py`.
- The deviation table's numbers against `docs/sa3_outcome_marginals.json` (not opened).
- Whether the tests pass alone, in reverse order and with every other test file (section 9's last line).
