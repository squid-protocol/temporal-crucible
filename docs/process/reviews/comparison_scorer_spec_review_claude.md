# Review — the comparison scorer, specification part 1

**Reviewer:** Claude (Fable 5.2), an independent session, 2026-11-15. I did not write the specification.
**Reviewed:** `docs/process/comparison_scorer_spec.md` at `3db7d7b`.
**Read:** `tools/sa3_score.py`, `tools/sa3_stats.py`, `tools/sa3_outcomes.py` (all of each); `tools/tables/`
(`schema.py`, `build.py`, `canon.py`, `invariants.py`, `DECISIONS.md`); `tables_spec.md`,
`tables_phase_b_spec.md`, `owner_job_spec.md`; `tools/owner/README.md`, `DECISIONS.md`, and the parts of
`prepare.py` and `report.py` that run and validate a stage; Amendment 5 sections 2, 3, 4, 6 to 10 and the
erratum; the consolidated registration, section 6; `research_codebase_spec.md` sections 5, 7, 9; defect log
25, 26, 42 to 48, 63; the leakage table of `reviews/owner_job_spec_review_claude.md`; the head of
`harness_report.md`.
**Experiments:** `/home/joe/.claude/jobs/24bf9d40/tmp/compare_review/` (`exp_a.py` to `exp_f.py`, `exp_c2.py`,
`exp_c.out`). Synthetic arrays only. `tools/sa3_stats.py` was imported after I confirmed from its source that
it imports only `sys`, numpy and scipy and opens nothing. `tools/sa3_score.py` was never imported; where I
needed two of its pure functions I transcribed them. No SA3 tool, harness or job was run. No real study path
was opened.

Marks: **[code]** verified in code · **[run]** run on synthetic data · **[reasoned]** reasoned, not run.

## Verdict

**Sound to build after changes; not sound to build as written.** The core idea holds: a table route, the
reference loader called unchanged beside it, and a cell-by-cell comparison is a check that can fail. The
stream order in section 4 is right as far as it goes, and I found no consumption of the shared generator
that it omits. Four things stop the build as written. The blind test cannot do what it says: every seeded
fault sits in a sealed file, so a hash decides the result, and three of the five "expected layer" entries
are wrong or undefined. The words quoted for the independent statistic do not fix the number: of six natural
readings of "equal-count" only one reproduces the reference. The table route cannot reproduce the branch-state
predictor in three value cases, because the stored `measure` table lost the information. And the spec claims
a match shows the run is "what the registration says"; it would show that two routes agree with each other
and with this document, which was transcribed from the code.

Counts: **1 blocker, 10 major, 7 minor.**

## Findings

### Blocker

**B1. The blind test (test 6) is not blind, is decided by a hash, and three of its five expectations are
wrong or undefined. [code] [run] [reasoned]**

- *Every fault is in a sealed file.* Code, a scan database, an outcome file, the marginals file: the external
  seal hashes all of them. So "flagged" is settled by `seal.py verify` for all five before any layer of this
  specification runs. The test would pass with layers 1 and 3 deleted. Only the clause "by at least the
  expected layers" tests the new work, and that clause is where the errors are.
- *Fault 5, two repos swapped in the marginals file, "layer 3, R cells only".* The comparison scorer reads the
  same marginals file, "in the file's order" (spec section 4, step 1). If it reads the copy's file, both
  routes take the swapped order and every cell is equal: layer 3 does not fire. It fires only if the
  comparison side reads a pristine file, and the spec does not say which. [code: `sa3_score.py:76-77`, `354`]
- *Fault 1, "one line of the reference scorer changed (the caliper)".* The caliper is `CALIPER = 1.5` in
  `sa3_stats.py:28`, which the comparison scorer imports. Changed there, both routes get the same wrong
  number and layer 3 is silent; only the independent statistic sees it, and that file is not built by this
  builder (test 5 is "left skipped"). Changed at `sa3_score.py:394` (the 1.25 of S7), nothing sees it: the
  decoys have about 306 files and that branch needs 600 (M6). Only a change to the default at
  `sa3_score.py:173` is caught as the table says.
- *Fault 3, "one scan value of a primary predictor changed … and the placebo reproduction".* For
  `risk_safety_score` the placebo stage is blind to it. The surrogate for a score is a monotone map of
  uniform draws through the quantiles of the non-zero values, and the statistic uses only order. I
  transcribed `fit_size_model` and `draw_surrogate` and ran them: moving one non-zero value, a little or a
  lot, left all 200 surrogate effects bit-identical in 12 of 12 runs. A count predictor's surrogates changed
  in 12 of 12. `in_degree` has no scan value at all (it comes from the call table). So the expectation holds
  for two of the four primaries. [run: `exp_e.py`]
- *Not blind.* One session writes the faults, the expectations, the check and the shuffle, and knows the
  five fault types while writing the check. `research_codebase_spec.md` section 9 asks for more: detection
  rate and false-alarm rate recorded, beside what a review of the same copies finds.
- *Five and five say little.* All five caught bounds the detection rate below only at 55% (95%, one-sided:
  0.05^(1/5)). No false alarm in five bounds the false-alarm rate above only at 45%. Defect log 25 and 63
  say: simulate a gate before using it. This gate's false-alarm rate is not estimated anywhere.
- *False alarms are possible.* `mod1_lift.ro` opens scan databases with `mode=ro` (`mod1_lift.py:45-46`). A
  database in write-ahead mode can gain side files on an ordinary read; the seal hashes the `-wal`. Whether a
  clean copy is flagged then depends on whether the seal is verified before or after the reference runs on
  that copy. The spec does not say. [reasoned; owner-job review M3 measured the same effect]

*Changes.* (1) Report each layer's verdict on its own, with the seal switched off, as well as the whole
check's. The pass rule is on the layers. (2) State which files each side reads in a faulty copy: the
comparison side reads the pristine tables, the pristine marginals file and the sealed `sa3_stats.py`, never
the copy's. (3) Correct the table: fault 1 names the line; fault 3 names a count predictor and a universe
file, or drops the placebo from its row; fault 5 depends on (2). (4) Add faults the seal cannot see, which
is what layers 1 and 3 exist for: a stale table (one `measure` row from an older build), a call-degree table
built with the unresolved rows left in, a label table with two pool positions exchanged, a comparison run
under a different thread count. (5) Someone other than the check's author picks the faults: the reviewer
model or the second builder, from a list the first builder has not seen. A script draws the shuffle from
the system's random source and writes the key to a file the check's process cannot read; the expectation
table's SHA-256 and the check's full output are written down before the key is opened. (6) Give the numbers
their bounds in the report, or run 20 and 20.

*How to test the changes.* (1) and (2): the corrected test must fail when layer 3 is replaced by a stub that
always prints "equal", and when layer 1 is. Today's version would still pass. (3): run each fault alone on
study P and record which layers fire before fixing the table. (5): the test's log shows the key file's
creation time after the output's hash. (6): simulate the pass rule under assumed detection rates, as
section 7 of `research_codebase_spec.md` did for the control suite.

### Major

**M1. The spec overclaims what a match shows. [code] [reasoned]**
"What a match is evidence of: … that the derivation of every predictor, the handling of missing values, the
order of work and the aggregation are what the registration says" (spec lines 16-20). That is not right.

- Section 2 says of itself: "These are the reference loader's rules …, written out." Section 4 is "the
  reference's order". Both were written by reading `sa3_score.py`. A match shows the comparison scorer
  reproduces this document, and this document reproduces the code. The registration is not on either side.
- The two routes share `sa3_stats.py` (every statistic, the permutation, the bootstrap), numpy and scipy,
  the marginals file, the placebo file, and a loop written from the reference loop. A fault in any of them
  is common to both and invisible. Defects 42 and 43 are reproduced "as coded" by design.
- Only section 6 is written from the registration's words, and M2 shows those words do not fix the number.

*An all-equal cell map would license:* the reference result is a function of the recorded inputs alone; the
stored tables hold what the reference loader read, for every predictor and label, element by element; no
unrecorded state, input or ordering entered the run; the written rules of sections 2 and 4 are a complete
description of what the code did; so part 2's corrections, computed from the tables, start from the same
numbers. *It would not license:* that the code follows the registration; that any statistic is computed
correctly; that the Holm step, the readings or the cuts are right; that the labels or the universe are
right.

*Change.* Replace the paragraph with the two lists above. Add "transcribed from the code, not derived from
the registration" to sections 2 and 4. *Test:* none needed; it is wording. The deviation table of Amendment 5
section 8 is where registration-against-code belongs.

**M2. The quoted words do not determine the independent statistic. [run]**
See "The independent-statistic experiment" below for the numbers. In short: the words leave seven choices
open. On 2,983 synthetic cases, exactly one combination reproduced the reference (bit for bit, every case).
For the band remainder alone I tried six readings; the one I would most readily have written
(`numpy.array_split`: the first bands get the extra file) agrees with the reference in 42% of the cases that
have a remainder, with a mean absolute difference of 0.006 and differences above 0.005 in 14% of cases. An
independent builder lands on the reference by luck or by looking.

The spec foresees a disagreement and calls it "a finding about the registration's wording". That is honest,
but it leaves the check with two outcomes, neither of them useful: it passes because the builder guessed
right, or it fails and can only be resolved by reading the reference, which ends the independence. The
spec's own parenthesis also names two of the open choices to the second builder, and
`tools/sa3_stats.py`'s docstring sits in the same repository.

*Change.* Decide beforehand, in writing, what the open choices are and what each reading is (the list
below). The second builder implements **every** listed reading as a switch, and states which one it judges
the plain meaning **before** any comparison. The report then gives, per reading, equal or not, on the
synthetic cases and on the decoys. That turns luck into a measurement, and the registration's wording gets
an erratum naming the reading the code takes. Also fix the interface: the statistic receives the files in
use (after missing values are dropped), with size, path, value and label; and say that the 300-file rule
counts the files in use (`sa3_score.py:177-179`), which the words do not say.
*Test.* On the 2,000 cases of test 5, exactly one listed combination must equal the reference within 1e-9 on
every case, and each of the others must differ on at least one case. If two readings both always agree, the
cases are too weak (no remainder, no equal sizes) and the test fails.

**M3. The table route cannot reproduce `amplified_cascading_flux` in three value cases, and the stored table
cannot hold two more. [code] [run]**
The reference: `float((json.loads(rec) if rec else {}).get(key, 0) or 0)` inside
`except (ValueError, TypeError)` (`sa3_score.py:102-105`). The stored `measure` row was built by different
code: `.get(key)`, then `None if v is None else float(v)`, with `AttributeError` also caught
(`tools/tables/build.py:206-213`). I ran both on 35 synthetic records (`exp_a.py`):

| telemetry record | reference `load()` | from the `measure` row |
|---|---|---|
| key present, value `""` | 0 | missing |
| key present, value `[]` or `{}` | 0 | missing |
| value `NaN`, `"nan"`, `Infinity`, `1e400` | missing, missing, inf, inf | the table build stops: `canon.py:69-70` refuses a non-finite real |
| record is JSON but not an object (`[]`, `3`, `0`, `null`, `"x"`) | **the loader crashes**: `AttributeError` is not caught | missing |
| every other case tried (NULL, `''`, `{}`, key absent, `0`, `null`, `false`, `true` → 1, `"3.5"` → 3.5, `" "` → missing, `"abc"` → missing, `[1]` → missing, not JSON → missing) | — | agree |

The spec's row says "0 when … the value is empty or zero". That is what the loader does. But a builder
working from `measure` gets "missing" for an empty string, list or object, and nothing in the table can
tell those from a value that does not parse. The spec's own rule cannot be implemented from the tables it
names. Whether any real record has such a value I do not know and did not look.
*Change.* Do not derive this predictor from `measure`. Put it in the new predictor-side table, built from
the scan database by the rule as written, next to the call degrees. State the full rule: Python truthiness
of the value, then `float()`; `true` is 1; a non-finite result is stored as missing with a flag; a record
that is valid JSON but not an object is reported as "the reference loader would stop here" and counted.
*Test.* Test 2's planted cases must include `""`, `[]`, `{}`, `true`, `"3.5"`, `" "`, and layer 1 must pass
on that planted scan (see m4: test 2 as written checks the derivation against the spec, not against the
loader). A planted non-object record must make the reference loader stop and the table builder report it.

**M4. Section 4 cannot be built from its text; two builders would write different loops. [code]**
The stream order is correct (see "Section 4 against the code"). What a cell holds is not stated. Missing
from the text, all needed for cells to match:

- The 23 predictors, their order, role and count flag (`sa3_score.py:52-66`). "The reference's declared
  order" is not a list. The silence rule needs the count flag (`183-190`).
- The matched control runs over **all 23** predictors, silent or not, under the pair floor or not, with
  **no** pair floor of its own (`406`, `297-332`). A predictor with no missing value uses the whole-universe
  bands; one with missing values gets bands recomputed on its own files (`320-329`). A draw in which either
  label vector is empty or covers every file is dropped for every predictor, **after** the generator has
  been used (`316-317`); a predictor is dropped from a draw on the same test within its own files (`326`);
  a not-a-number difference is dropped (`330`); a predictor with no surviving draw has no entry (`332`).
- S7: only with 600 or more files in use; caliper 1.25, 20 bands; `null` when under the pair floor
  (`393-395`). The bootstrap interval and "minus surrogate" only for primaries on HP; the surrogate mean
  defaults to 0.0 when the repo or predictor is absent from the placebo file (`396-400`).
- The permutation p-value's form: two-sided about the null mean, `>=` (`389`); the spread with `ddof=1`.
- The any-commit control's three conditions (`410`, `414`), and that its values appear only in the
  summaries.
- Aggregation: "as the reference does it" is the whole rule.

A builder will open `sa3_score.py` to fill these. That is acceptable for a transcription check, but the
spec says "the comparison scorer implements **this text**".
*Change.* Either write the items above into section 4, or say plainly that the loop is transcribed from
`stage_score` and `control_effects` and that the text is a summary. *Test.* Give section 4 alone to the
second builder and count the questions it has to ask; each is a gap.

**M5. The cell map's classes have holes, and "after the first difference" hides faults. [code] [run]**

- *Masking.* "R cells after it are expected to differ and are reported as 'after the first difference'."
  That is true only for a stream slip. A wrong value in one cell leaves the stream in step:
  `block_permute`'s use of the generator depends on the number of files, not on the values, and a block of
  one file draws nothing, so 400 and 401 files leave the same state (`exp_b.py`). After such a fault every
  later R cell is still equal. Folding them into "after the first difference" hides which case it is, and
  hides a second, independent fault behind the first.
  *Change:* compare and count every R cell. Report the first not-equal one, and separately "R cells equal
  after it: n of m". All equal after it means a local fault; none equal means a slip.
- *Cells with no position.* A cell has two R numbers (`perm_p`, `null_sd`). The matched control is per repo,
  after its outcomes, and is not "an outcome". `random_effects`, `side_counts`, three of the summaries and
  the readings are study-level. "(repo, outcome, predictor)" does not name any of these. Define the order:
  per repo, the outcome cells in loop order, then that repo's control; then the study-level cells in a
  fixed order.
- *Words and whole numbers that depend on R.* `side_counts.above/below/across` are whole numbers built on
  `perm_p < 0.05`. `tests[p].reading` and `allreverts_reading` are words built on the control. The spec
  puts "side counts" and "defect-specific" under "within 1e-12", which has no meaning for a word or a
  count. They need their own class: exact, and reported apart because they follow the stream.
- *Not-a-number, null, absent.* `S9_logistic_z` is not-a-number when the values in use are constant
  (`sa3_stats.py:139`; `exp_d.py`), and the reference writes it as the bare token `NaN`. Read back,
  `abs(nan - nan) <= 1e-12` is false: a spurious "not equal". `S7_tight` and `ci95` can be `null`
  (`sa3_score.py:395`, `sa3_stats.py:193-194`). `S7_tight`, `ci95`, `minus_surrogate`, `specificity`,
  `allreverts_reading` and `random_effects[p]` can be absent. State: not-a-number equals not-a-number; null
  equals null; a key present on one side only is "not equal" under "which cells exist".
- *Top-level keys the comparison cannot produce independently.* `sealed` is the lock file's content;
  `engine` is one string from the first repo's sidecar; `valid` is copied from the placebo file; `not_run`
  and `unavailable` are constants. Say for each whether it is compared, and from where the comparison side
  gets it. A copied constant is not a check.
- *The tolerance.* Calling the same functions on equal arrays gives bit-identical results; I found no
  difference from building the arrays another way (fill-and-assign against a list, `float.hex` round trip),
  from integer, boolean or 32-bit-integer dtypes, from a non-contiguous view, or from 1, 2 or 8 threads in
  a second process (`exp_d.py`, `exp_f.py`). The one exception: a 32-bit float `x` moved `S9_logistic_z` by
  4e-7. So 1e-12 is not needed, and a difference between 0 and 1e-12 is itself information.
  *Change:* report three counts per class: bit-equal, within 1e-12, beyond. Require the comparison side to
  use 64-bit floats. Record the runtime fingerprint of both runs and require them equal.

*Test for all of M5:* a comparison scorer with one wrong value in one predictor of the second repo must be
reported as "1 not equal, all later R cells equal"; one with a slip as "all later R cells not equal"; a
decoy cell with a constant predictor must compare equal.

**M6. The two decoy studies leave much of `stage_score` unexercised. [code] [reasoned]**
Default control repositories have about 306 unit files (`harness_report.md`), 8 repos, 6 drawn. I did not
run them; the list below is from the code's conditions.

| branch | line | reached on the decoys as specified? |
|---|---|---|
| S7, 600 or more files in use | `393-395` | **no** |
| control skipped, K under 5 | `302-303` | **no**: HP's floor needs 20 commits, and the pool is large |
| the second draw, pool smaller than HP's commits | `314` | **not stated**; default pools are larger. The comparison scorer could omit this draw and pass |
| a repo with status `ok` whose HP does not clear the floor | `366`, `405` | not stated |
| cuts by repo name (`PU_…`, S1, `go_django_removed`) | `483-488` | **no**: decoy names match none, so each cut equals `all_drawn` and a wrong name list cannot show |
| `C_family` and `managed` with five or more repos | `493-494` | at most one of the two, and only with a 5 to 1 split |
| S3, a window under 730 days | `487` | no: ten-year span |
| "not detected (Holm: an earlier test …)" | `433-434` | unlikely |
| "contradicted"; "NO FINDING" (gate failed) | `170`, `442-443` | no |
| `allreverts_reading` | `480-481` | unlikely |
| any-commit control skipped for a primary with a missing value | `414` | unlikely |
| a control draw dropped | `316-317`, `326-327` | first: practically never; second: perhaps |
| bootstrap returns `[null, null]` | `sa3_stats.py:193-194` | no |
| 10 bands against 5 | `sa3_stats.py:34` | by luck: 306 files, and one missing value in seven puts a predictor under 300 |

A comparison scorer can be wrong in any "no" row, pass every test, and then differ on real data. The spec
says a difference is then "investigated on a decoy", but no decoy reaches the branch.
*Change.* Measure it: run the reference `score` on the decoy studies under a line tracer inside the sandbox
and list the lines of `load`, `control_effects`, `churn_any`, `stage_score` and `summarize` never executed.
Add decoys until the list is empty or each remaining line is named and accepted: one repo of 650 files; one
with a pool smaller than HP's commit count; one with a pool under five; one `ok` repo under the HP floor;
decoys named `django`, `go`, `bun`, `mediawiki`; five C repos among the drawn; one short window; a third
study with the placebo gate failed; a study with a negative planted effect (defect 42's own case).
*Test.* The unexecuted-line list is a test output; the test fails if it grows.

**M7. The owner launcher cannot run a new stage unedited. [code]**
Section 3: "an owner-run stage, with the launcher and validator of `tools/owner/` (imported, not edited)".

- `Job.run` builds the command `…/tools/owner/prepare.py stage <name>` (`prepare.py:494`); the stage
  entry accepts only the names in `STAGE_FUNCS` (`279-281`, `290`); `validate_result` looks the name up in a
  closed dictionary of shapes (`306-325`, `509`); `record` writes the run log, whose stage names are
  validated against `report.STAGES` (`report.py:29-30`, `182-186`).
- `write_public` writes exactly three kinds of file (`report.py:294-311`). There is no way to hand it a
  layer 1 report.
- `leaf` has no kind for an item name or a predictor name; `word:` kinds resolve through the fixed `WORDS`
  dictionary (`report.py:127-138`).

All of `tools/owner/` is sealed. What can be imported as it is: `sandbox_ro` (`Spec`, `run`,
`assert_inside_ro`, `check_rw`), `report.check` with a **new** schema made of fixed-key dictionaries and
`yesno` leaves (item names as dictionary keys need no new kind), `ReportError`, `Vocab`, `prepare.code_of`,
`check_places`, `new_or_empty`, `read_marginals`. What must be new code: the launcher's stage runner, the
stage entry point, the result shapes, the public writer, the run log. That new code carries the
"no free text leaves" property, so it needs the owner job's test 4 (planted markers, a stage that raises,
a stage that prints) run against **it**, not inherited. The seal's `job_code` list also does not cover
`tools/compare/`, so the code that reads real labels in this stage is not in any seal.
*Change.* Say exactly what is imported and what is new; add the new files' hashes to the scoring job's
record; forbid changing `report.WORDS` or `report.STAGES` in memory. *Test.* The marker tests on the new
launcher; a test that the sealed files' hashes equal `docs/sa3_seal_run1.json` after the build.

**M8. Layer 1 can leak one bit about named files, and most of it needs no label at all. [code] [reasoned]**

- *Free text:* none, if the output is a fixed-key dictionary of yes/no per repo. Good. A failed stage shows
  an exception type (`key_error` against `assertion`), as the owner job already does.
- *Predictor against outcome:* no item compares a predictor with a label.
- *The leak.* The outcome items are indexed by the universe. If the table universe differs from the
  loader's (M10 gives one way), then "positive flags equal" compared as sets of paths is true exactly when
  none of the differing files is positive. Those files can be worked out from public tables. That is one
  bit per outcome about identified files, before scoring. Compared as vectors it is always "not equal" and
  leaks nothing. The spec does not say which.
  *Change:* when the universe item is not equal, every item indexed by the universe (bands, predictors,
  outcome flags, commit files) is reported "not compared". *Test:* two decoys whose `file` table lacks one
  universe file, positive in one and not in the other, must give byte-identical public output.
- *The channel.* About 35 yes/no values for each of up to 46 repos is up to some 1,600 bits. Honest code puts nothing in
  them. The owner job's standard accepted yes/no values; this is the same class, larger.
- *Smaller.* The predictor-side items (universe, size, bands, 23 predictors) need no label. Phase B already
  calls `load(repo, True)` with stub outcome files and no label bound (`tools/tables/silence.py:43-48`,
  `125`). The same route gives layer 1's predictor side inside the read-only sandbox, run by a session, with
  nothing owner-run. The label-side items compare a re-encoding of the outcome file with the outcome file;
  they can only show an encoder fault (the erratum says as much), and nothing is lost by running them
  inside the scoring job, after the reference `score` has written its result.
  So **nothing in this specification needs to read a real label before scoring.**
  *Test:* on decoys, the predictor-side items computed with stubs equal those computed with the real
  outcome files (phase B's test 5 shows this for silence; extend it to the arrays).

**M9. The label tables as specified cannot be written with the existing canonical writer, and their key
loses the order they exist to keep. [code]**

- `canon.row_bytes` and `table_bytes` look the table up in `schema.TABLES` (`canon.py:79-87`). New tables are
  not there. Section 10 forbids editing `tools/tables/`. So "a canonical hash as in `tables_spec.md`" needs
  an edit the rules forbid, an in-memory change to `schema.TABLES`, or a second writer. Also `canon.py`
  does `import schema` by bare name, against section 10's own module rule.
- The schema requires every key column to be a string (`schema.py:85`), and rows are stored sorted by key
  bytes (`canon.py:93-101`). A `position` key therefore sorts as text: "10" before "2". A reader that takes
  the file's row order gets the commits in the wrong order from the eleventh on. The spec must say: fixed
  width with leading zeros, or the reader sorts by the number.
- A table with one row per (position, path) cannot hold a commit with no path. The loader counts such a
  commit in K and in the positions drawn (`sa3_score.py:120-121`, `300-301`). `sa3_outcomes.build` as it
  stands never writes one (`168-174`, `250-252`, `292`, `309`), and never repeats a path or a hash; but the
  stored files are data, not code. Add a commit-level table (repo, position, hash, number of paths) and an
  invariant that fails the build on an empty commit, a repeated path or a repeated hash.
- Say that tables are built from the **parsed** outcome file, as the loader parses it (a repeated key in
  JSON keeps its first position and its last value).

*Test.* Layer 1 on a decoy with twelve or more pool commits fails if the reader
uses text order; a planted empty commit fails the table build by name of invariant, not of commit.

**M10. The universe and the call-degree table are under-defined. [code]**

- *Universe.* The loader's universe is `universe()`'s set, taken from the scan (`sa3_score.py:83-85`). The
  `file` table has rows only for paths of the snapshot's **tree** (`build.py:185-193`); a scanned unit file
  that is not in the tree gets no row and is only counted (`repo.scanned_not_in_tree`, DECISIONS 7). Where
  that count is not zero, "the `file` rows with `in_universe = 1`" is a smaller universe than the loader's.
  Layer 1 would show it, with M8's leak on the way. *Check before building:* read that column in phase B's
  public output for all repos. I did not; that directory was out of bounds for this review.
- *Call degrees.* The loader maps a call row to a file through `file_data.id` and the path mapping, and
  counts a row for any id whose path is a universe path (`98`, `125-130`). The spec gives the counting rule
  but not: which sandbox builds the table on real data and with which declared inputs; that the path
  mapping is restated (remove `src_root` + "/" from the front, else strip leading slashes, `94`); that it
  holds rows for universe files only or for all; what happens with two `file_data` rows for one path
  (`read_scan` refuses, `build.py:146-147`, so phase B having passed means there are none; say so and
  refuse likewise).
- *Which repos.* Layer 1 "for each repo": say "the rows with status `ok`", which is what `stage_score`
  loads (`354`, `362-363`). The placebo stage only ever loaded the repos that clear the HP floor, so for
  the others this would be the loader's first run with real labels.

*Test.* A decoy with one scanned unit file removed from the tree's table must make layer 1 say "universe:
not equal" and everything indexed by it "not compared"; a planted call from a universe file to a file
outside it, and one with an unresolved target, give the stated degrees.

### Minor

**m1. `out_degree`: "the number of such rows" can be read two ways. [code]** The code counts rows with a
resolved target **function** whose source file is this file, whatever the target file (`126-130`). "Such
rows" could be read as also requiring the target file to be in the universe. Write it out. A call from a
file to itself counts once in each degree. *Test:* M10's planted call.

**m2. Three loader behaviours the table does not mention. [run]** (a) Two `file_data` rows mapping to one
path: the last **non-null** value wins per column, and an unparsable later record leaves the earlier value
(`exp_a.py`); moot while `read_scan` refuses duplicates. (b) A text cell in a numeric column stops the
loader (`float("abc")`, line `101`, no `try`). (c) A nesting entry `[1, null]` reads as (1, missing) in the
loader and stops the table build; `[]` stops the loader and reads as missing in the table. None is likely.
State them as "the reference would stop".

**m3. The reference's pair counts are 32-bit sums. [run]** `Design.effect` adds 32-bit masks
(`sa3_stats.py:61`, `82`). The concordance sum is 64-bit (line `78` promotes), but the pair **count** per
band and side is not exact above 2^24 = 16.7 million: I measured an error of 99 in 45 million (2e-6
relative). A plain loop would then differ from the reference by more than 1e-9, and the loop would be the
one that is right. Below 16.7 million eligible pairs in one band and side the two agree exactly. *Change:*
the independent statistic also prints the largest per-band, per-side pair count; above 2^24 a difference is
attributed to this, as a finding about the reference.

**m4. Test 2 checks the derivation against the spec, not the spec against the loader. [reasoned]** "Gives
the stated value" passes if `derive.py` and section 2 share a mistake. Run the reference `load()` on the
same planted scan and require layer 1 to pass on it.

**m5. Some planted changes in tests 1 and 4 can be no-ops. [code] [run]** Test 1: a changed `coding_loc`
(stored, used by no predictor), a value of a file outside the universe, a removed call row with no resolved
target, each leaves every array unchanged and layer 1 rightly silent. Name a measure in use, a universe
file, a resolved row. Test 4: "two outcomes swapped" changes nothing unless both clear the floor in that
repo; "a silent predictor made to draw" changes nothing if it is silent because it has no value, or one
value (a block of one draws nothing, `exp_b.py`). Test 4 also needs fault switches inside the scorer; keep
them in the test, by subclass or patch, not in `scorer.py`.

**m6. Sort order and file order. [reasoned]** "Paths in sorted order" should say Python's string order
(code points). It equals the byte order of the stored tables for valid UTF-8, so both readings agree; say
it once. The tie-break "by path" in the bands is the same order: on cases with many equal sizes, breaking
ties in natural order (`f2` before `f10`) agreed with the reference in 0 of 300 (`exp_c2.py`).

**m7. Label-side layer 1 is a test of the encoder only. [reasoned]** The label tables are built from the
outcome file and compared with the loader reading the same file. State that in section 3, as the erratum
does, so that "equal" on those items is not read as more.

## Section 2 against `load()`, predictor by predictor

"Agree" means the spec's words give the loader's array for every value I tried (`exp_a.py`).

| predictor | spec's rule | what the code does | agree? |
|---|---|---|---|
| universe, order | `file` rows in universe, sorted | `sorted(universe())` from the scan (`83-84`) | **only if** no scanned unit file lies outside the tree (M10) |
| size | scan's total lines; none stops the run | `total_loc` as float; asserts no missing and all > 0 (`106-107`) | yes |
| bands | `bands` on size and path, files in use | whole universe at `109`; recomputed on files in use at `177-179` | yes |
| path | scan root removed from the front | root + "/" removed if present, else leading slashes stripped (`94`) | **incomplete**: the second half is missing |
| `in_degree` | call rows with a resolved target function whose target file is this file; never missing | the same (`126-128`) | yes |
| `out_degree` | "such rows" whose source file is this file | resolved target function; source is this file; any target file (`129-130`) | yes on one reading; ambiguous (m1) |
| `in_degree_per_loc` | value ÷ size | `indeg / loc` | yes; never missing |
| `pagerank_score` | scan's value; missing if null | `float(v)`, null stays missing (`99-101`) | yes |
| `betweenness_score` | same | same | yes |
| `struct_branch` | same | same | yes |
| `struct_branch_per_loc` | value ÷ size; missing if the value is | division carries missing | yes |
| `state_danger` | scan's value | same | yes |
| `state_pointers_alloc` | sum; missing if either is null | float sum carries missing (`135`) | yes |
| `def_safety` | scan's value | same | yes |
| `state_flux` | scan's value | same | yes |
| `state_heat_triggers` | scan's value | same | yes |
| `risk_safety_score` | scan's value | same | yes |
| `risk_tech_debt`, `risk_cognitive_load`, `risk_state_flux`, `risk_concurrency` | scan's value | same | yes (four rows, one rule) |
| `risk_safety_nonzero` | 1 if score > 0 else 0; missing if the score is | `where(isnan, nan, (r > 0) * 1.0)` (`140`): negative → 0, −0.0 → 0, +inf → 1 | yes |
| `risk_safety_among_nonzero` | the score; missing if missing or not above zero | `where(r > 0, r, nan)` (`141`): negative, zero → missing | yes |
| `amplified_cascading_flux` | key's value; 0 if record empty, key absent, value empty or zero; missing if unparsable or not a number | see M3 | the words match the loader, **except**: `true` → 1 and a non-object record stops the loader (not stated). **The tables cannot supply it** for `""`, `[]`, `{}`, non-finite |
| `amplified_cascading_flux_per_loc` | value ÷ size | `acf / loc` | follows the row above |
| `nest_max`, `nest_mean` | from the nesting file; missing if no file or not in it | `nm[i], nn[i] = a, b` for paths in the universe (`144-150`); a null element reads as missing | yes for well-formed entries (m2) |
| silence | under 10% non-zero among present, or none present; continuous only: under 20 distinct | the same (`186-190`); "continuous" = not a count and not the indicator | yes, but the count flags are not listed (M4) |

## Section 4 against the code

- **Repos, outcomes, predictors:** stated correctly (`354`, `362-372`). One generator, made once before the
  repo loop (`361`), shared by every repo.
- **What draws.** `bands`, `Design`, `Design.effect`, `residual_effect`, the three sensitivity statistics
  and `design_for` take no generator. `boot_ci` makes its own from seed 2982 each call
  (`sa3_stats.py:181`) and leaves the shared one untouched; two calls give the same interval. Confirmed by
  comparing the generator's state before and after (`exp_b.py`). Only `block_permute` (200 per scored cell)
  and the two `rng.choice` calls in the control draw.
- **How much.** `block_permute` calls `rng.permutation` once per block of four files in size order; its use
  of the stream depends on the number of files in use and not on values or sizes; a last block of one file
  draws nothing. `rng.choice(n, K, replace=False)` draws even when K equals n.
- **The control.** K, the conditional second draw and "under 5 draws nothing" are right (`301-303`, `311`,
  `314`). The draws at `311` and `314` happen before the tests at `316` and `326`, so a dropped draw has
  still used the stream; the comparison scorer must draw first and test after. The spec does not say so
  (M4), though a builder who gets it wrong is caught by test 3.
- **S7 and the any-commit control** draw nothing. Correct.
- **Nothing omitted** from the stream that I could find.
- **Order of commits.** `list(d["hp_commits"])` is the outcome file's object order, which is the order a
  set of hashes happened to iterate in when the file was built (`sa3_outcomes.py:226`, `292`, `309`). It is
  fixed only by the file's bytes. The position column is the right answer; M9 gives what it still needs.
- **A match with a fault elsewhere.** The any-commit control's per-repo values are not in any per-repo
  cell; they reach the result only through the summaries, and with fewer than three repos a summary is
  "not fitted". On the decoys that is six repos, so it is compared, if the three conditions hold there.

## Section 1: are the label tables enough?

For `d["y"]` (six outcomes), `d["hp_commits"]` and `d["pool"]`: yes, with M9's additions (text order of
`position`, empty commits, the parsed file). Paths outside the universe: the loader asserts on `files`
(`113-115`) and raises `KeyError` on a commit's path (`120-121`); the table route should refuse the same
way, by count, never by name. Everything else `stage_score` reads about a repo comes from the public
marginals file, not from the outcome file: `status`, `repo`, each outcome's `clears_floor`, `drawn`,
`merge_units`, `window_days`, `family` (`76-77`, `366`, `405`, `482-490`). The spec has the scorer read that
file directly, which is right. Nothing is missing from the tables on that account. `engine` comes from the
first repo's sidecar (`357`); the `repo` table holds it.

## The result's keys and their class

D = real number, no shared draw. R = real number from the shared stream. "R-exact" = a word or whole number
that follows the stream (the class the spec lacks).

| key | class | note |
|---|---|---|
| `valid` | word (yes/no) | copied from the placebo file by both routes |
| `unavailable`, `not_run` | words | constants; a match is not a check |
| `sealed` | words | the lock file's nine hashes; the comparison has no lock. Exclude or say how |
| `engine` | word | first repo's sidecar; from the `repo` table |
| `repos` (key set and order) | set | order follows the marginals file |
| `repos[r].n` | whole number | |
| `…outcomes` (which outcomes, which predictors) | set | from the floors and the role rule |
| `…[p].status` | word | "ok", "instrument silent", "under pair floor" |
| `…[p].bauc` | D | |
| `…[p].dropped_null` | whole number | |
| `…[p].null_sd` | R | |
| `…[p].nonzero_share` | D | |
| `…[p].residual` | D | least squares inside; bit-equal in my runs |
| `…[p].perm_p` | R | |
| `…[p].S4_replaces`, `S6_sauc_minus` | D | |
| `…[p].S9_logistic_z` | D | can be not-a-number; up to 40 Newton steps, stop at 1e-7; bit-equal on equal 64-bit arrays |
| `…[p].S7_tight` | D, or null, or absent | absent under 600 files |
| `…[p].ci95` | D pair, or `[null, null]`, or absent | the spec is right: it reseeds itself |
| `…[p].minus_surrogate` | D, or absent | |
| `repos[r].specificity[p]` | R | absent key = no HP floor; `{}` = K under 5; a predictor absent = no surviving draw |
| `tests[p].holm_level` | D | follows the order of the p-values |
| `tests[p].bauc`, `.residual`, `.allreverts` | summary of D | `n`, `positive`, `negative` whole; `mean`, `se`, `ci`, `p`, `level` D; `reading` word |
| `tests[p].minus_control` | summary of R | its `reading` is R-exact |
| `tests[p].reading` | R-exact word | "defect-specific" against "tracks activity" follows the control |
| `tests[p].allreverts_reading` | R-exact word, optional | follows `reading` |
| `tests.in_degree.*` | D and words | `exploratory` is a constant |
| `side_counts[p].above`, `.below`, `.across` | R-exact whole numbers | the spec lists them under "within 1e-12" |
| `side_counts[p].sign_test_p` | D, or null | the spec's "side counts … R" is wrong for this one |
| `random_effects[p].mean`, `.se`, `.tau` | R | the key exists only with three or more repos and every spread above zero |
| `summaries["…|bauc|…"]`, `residual`, `minus_surrogate`, `S4`, `S6`, `S7`, `S9`, `minus_churn_any` | summary of D | the only place the any-commit control appears; summation order follows repo order |
| `summaries["…|minus_control|all_drawn"]` | summary of R | |
| `summaries` key set | set | follows which statistics exist anywhere |

The reference writes with `default=float` (`500`). Every count in it is already a Python integer, so no
whole number is written as a real. A numpy integer would be (`exp_d.py`); the comparison side should not
rely on that argument.

## The independent-statistic experiment

**A disclosure first.** The task was to write the statistic from the quoted words before reading
`Design.effect`. I had already read all of `sa3_stats.py`, as the same brief required, when I wrote it. So I
cannot report which reading I would have chosen blind. What I did instead: listed every choice the words
leave open, wrote each reading as a switch in a plain double loop over pairs (`exp_c.py`), and measured
which combination equals `sa3_stats.Design(...).effect`. Where I say which reading seems plainest to me,
that judgement is contaminated.

**Cases.** 3,000 synthetic repos, 23 to 650 files (sizes chosen around 300), four kinds: heavy ties in size,
few ties, mid, and a continuous value; ties in value throughout; labels related to size. 17 gave no value
in the reference (one side empty); 2,983 compared; 2,265 of them have a band remainder.

**The choices the words leave open, and what each reading does.**

| choice | reading | equal to the reference within 1e-9 | largest difference | mean | over 0.005 |
|---|---|---|---|---|---|
| remainder | band = floor(rank × k ÷ n) — **the reference** | 2,983 of 2,983, all bit-equal | 0 | 0 | 0 |
| remainder | first bands get the extra file (`array_split`) | 1,659; with a remainder 941 of 2,265 | 0.33 | 0.006 | 416 |
| remainder | last bands get the extra | 724; with a remainder 6 | 0.38 | 0.013 | 827 |
| remainder | chunks of ceil(n ÷ k), last band short | 1,179; with a remainder 461 | 0.37 | 0.011 | 839 |
| remainder | chunks of floor(n ÷ k), last band takes the rest | 723; with a remainder 5 | 0.42 | 0.014 | 993 |
| remainder | cut points at size quantiles (equal sizes share a band) | 110 | 0.34 | 0.014 | 1,401 |
| "within 1.5" | inclusive — **the reference** | all | 0 | | |
| "within 1.5" | strictly inside | 789 | 0.095 | 0.002 | 256 |
| "by their share" | (1 − share) × mean of the two sides + share × equal-size concordance, pooled over bands — **the reference** | all | 0 | | |
| "by their share" | mean of the two sides, **plus** share × equal-size concordance (nothing taken off) | 209 | 0.51 | 0.086 | 2,692 |
| "by their share" | the same with the equal-size part centred at 0.5 | 218 | 0.21 | 0.009 | 882 |
| "by their share" | three parts weighted equally | 216 | 0.21 | 0.020 | 1,956 |
| "by their share" | each equal-size pair counted half on each side | 242 | 0.13 | 0.001 | 130 |
| pooled or per band | the formula inside each band, bands weighted by pairs | 15 (19 with no value) | 0.46 | 0.020 | 1,538 |
| pooled or per band | the same, bands weighted equally | 12 | 0.46 | 0.030 | 2,398 |
| "≥ 100 eligible pairs" | equal-size pairs count toward the 100 — **the reference** | all verdicts equal | | | |
| "≥ 100 eligible pairs" | they do not | verdict differs in 33 | | | |
| "the repo has ≥ 300 files" | the files in use after dropping missing values — **the reference** | all | | | |
| "the repo has ≥ 300 files" | the repo's universe (305 files, ten without a value) | 0 of 300 | 0.029 | 0.008 | (`exp_c2.py`) |
| "ties broken by path" | Python string order — **the reference** | all | | | |
| "ties broken by path" | natural order | 0 of 300 on heavy ties | | | (`exp_c2.py`) |

One choice was varied at a time, and every band rule was crossed with both caliper readings. A reading
"agrees" on the cases where the choice does not bite (no remainder, no equal-size pair, no pair exactly at
1.5), which is why none scores zero.

**What it shows.**

1. The reference is reproduced exactly by one combination: floor(rank × k ÷ n); inclusive; the convex
   combination pooled over all bands; equal-size pairs inside the 100; k from the files in use; code-point
   order. With that combination the plain loop was bit-identical to the reference in all 2,983 cases. So
   the reference computes what that reading says, which supports the third review's check of 400 cases.
2. The words do not select that combination. "Equal-count" with a remainder has at least five defensible
   readings, and two of them (floor of rank × k ÷ n, and extras to the first bands) both give band sizes
   that differ by at most one. "Plus equal-LOC pairs by their share" does not say that the two sides are
   scaled down by one minus the share; the word "plus" suggests they are not. "Scored separately" does not
   say pooled over bands. "The repo has ≥ 300 files" reads more naturally as the repo than as the files in
   use for one predictor.
3. The differences are not small. A wrong remainder rule moves the statistic by more than 0.005 in 14% to
   47% of cases, against confirmatory effects of a few hundredths. So a mismatch will be loud; the problem
   is not detection, it is that a mismatch is the likely outcome for an honest independent builder, and
   then the check has nothing left to say.
4. So: the quoted words are **not** enough to land on the reference's number without luck. M2 gives the
   change: pre-list the readings, build all, state the preferred one first, report each.

## What the comparison is evidence of

Stated under M1. In one line: all-equal means **the reference run did what this document says, on the
inputs the tables hold, with nothing else entering**. It does not mean the run did what the registration
says. For the three confirmatory cells the independent statistic adds: the reference's number equals a
plain loop under one named reading of the registration's words; whether that reading is the registration's
meaning is a question of wording, to be settled by an erratum, not by the comparison.

## Is the job larger than it needs to be before scoring?

Yes, on real data. Amendment 5's order needs, before the seal and the run, that "the checks of section 9
pass on control repositories". That is decoy work. On real data before scoring this spec adds an owner-run
stage that holds labels and predictors in one process and publishes up to about 1,600 yes/no values. M8 shows it
can be split: the predictor side needs no label and no owner (stub outcomes, the phase B sandbox); the label
side is an encoder check that can run after the reference `score`. The trade-off to put to the owner: run
before scoring, the comparison's inputs are fixed before anyone sees a result; run after, a layer 1 failure
is repaired with the result known. The predictor side before, by stub, keeps most of the first without the
cost.

## Reviewer's proposals and how each could be tested

| proposal | test |
|---|---|
| B1: per-layer verdicts with the seal off; faults the seal cannot see; faults chosen by another party; key sealed | the test fails when a layer is replaced by an always-equal stub; the log orders output hash before key |
| M2: pre-listed readings, all built, preference stated first | exactly one combination equals the reference on every synthetic case; each other differs somewhere |
| M3: branch-state value from the scan database by the written rule | planted `""`, `[]`, `{}`, `true`, `"3.5"`, `" "`; layer 1 passes on the planted scan |
| M5: compare every R cell; three counts per class | a one-value fault reads "later R cells equal"; a slip reads "none equal"; a constant predictor compares equal |
| M6: line coverage of the reference under the decoys | the unexecuted-line list is printed and may not grow |
| M7: new launcher code named and tested | the owner job's marker tests run against it; sealed hashes unchanged |
| M8: "not compared" under a universe difference; predictor side by stub | two decoys differing only in one positive give identical public bytes; stub equals real on decoys |
| M9: commit-level table, padded positions | twelve-commit decoy; planted empty commit |
| M10: universe difference | decoy with a scanned file outside the tree |

Each of these is my proposal and has not been built or run. The coverage proposal in particular assumes a
tracer can run inside the harness sandbox around the unmodified `score`; I did not try it.

## What I did not check

- Anything on real data. I did not open the study directory, the pool, the tables root, the protected root,
  the owner report's run directory or `~/.blind`. I did not read the numbers of `docs/sa3_placebo.json` or
  `docs/sa3_outcome_marginals.json`. So I do not know whether any real telemetry record has an empty,
  list or non-finite value (M3), whether any repo has scanned unit files outside its tree (M10), whether
  any real pool is smaller than its HP commit count or any repo has 600 files (M6), or whether any band
  holds more than 16.7 million eligible pairs on one side (m3).
- I ran no SA3 tool, no harness run, no decoy study and none of the existing tests. Every statement about
  what the decoys reach (M6) is from the code's conditions and the 306-file figure in `harness_report.md`.
- I did not import `sa3_score.py`. Section 2 was checked by reading `load()` and running transcriptions of
  its expressions; a transcription can be wrong. `fit_size_model` and `draw_surrogate` in `exp_e.py` are
  transcriptions too.
- The independent statistic was not written blind (stated above).
- Bit-equality across thread counts was tried on this machine only; its numpy links a system BLAS whose
  configuration it reports as unknown. Another library could behave differently.
- The write-ahead side-file false alarm in B1 is reasoned from the owner-job review, not run here.
- I read `tools/owner/prepare.py` and `report.py` in the parts that run and validate a stage, not line by
  line; `seal.py`, `placebo_check.py`, `tracker_keys.py`, `sandbox_ro.py` and `tools/tables/phase_b.py` only
  by outline. I did not check that `seal.py verify` has a decoy mode suited to ten copies.
- `harness_report.md` beyond its head and the lines on sizes; the defect log beyond the entries named;
  Amendment 5 sections 1 and 5; `research_codebase_spec.md` beyond sections 5, 7 and 9.
- Part 2 does not exist yet; nothing here speaks to it.
