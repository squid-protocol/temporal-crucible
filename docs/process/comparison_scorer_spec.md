# The comparison scorer — specification (part 1: inputs, the scorer, the cell map, the blind test)

**Status: Revision 2, 2026-11-15, after an independent review. Nothing built, nothing run.** It carries
Amendment 5 section 9, layers 1 and 3, and the blind test (as corrected by the erratum). **No sealed file is
edited** (`docs/sa3_seal_run1.json` lists them): not the reference code, not the six sealed documents, not
`tools/owner/`, `tools/harness/sandbox.py` or `sandbox_ro.py`.

**Revision 2.1, 2026-11-15, after the build** (`reviews/comparison_scorer_build_review.md`): four corrections
found by the builder — duplicate paths, non-finite telemetry values, and that a repo swap moves D summaries.

**What Revision 2 changed** (`reviews/comparison_scorer_spec_review_claude.md`: 1 blocker, 10 major, 7 minor;
"sound to build after changes"). The stream order of the first version was found correct. The rest:

- **The claim is smaller.** A match shows two routes agree with each other and with this document, which was
  written from the code. It does not show the code does what the registration says.
- **Nothing here reads a real label before scoring.** The input check that runs before scoring is
  predictor-side only, with stub outcome files, as phase B's silence count was.
- **One confirmatory predictor could not be rebuilt from the stored tables** (the branch-state value). A new
  predictor-side table holds it by the loader's exact rule.
- **The blind test would have passed with the comparison layers deleted:** every fault sat in a sealed file.
  It is redesigned around the question the layers actually answer, and the faults are written by a session
  other than the builder's.
- **The registration's words do not determine the primary statistic.** The independent statistic is rebuilt
  as a measurement of every reading, not a single guess.
- The cell map uses exact equality and no longer excuses cells "after the first difference"; the decoy studies
  must reach the branches the first design never touched; the owner launcher is not reused.

## What it is for, and what it is not

SA3's confirmatory result will come from the reference scorer, run once, unchanged. Nothing replaces it. The
comparison scorer is a **second route to the same numbers**: tables in, predictors derived by the rules of
section 2, its own scoring loop, and a cell-by-cell comparison with the reference's result.

**What a full match shows:** that the reference read the inputs that are recorded; and that the derivation of
each predictor, the handling of missing values, the order of work and the aggregation, **as written in this
document**, are what the reference did. This document was transcribed from the reference code, and the
comparison scorer uses the reference statistics module, so a match is agreement between two routes and one
description. **It is not evidence that the code does what the registration says**, nor that the statistic is
a good one, nor that the labels mean what they are taken to mean.

**The one place the registration itself is tested** is the primary statistic on the confirmatory cells
(section 6), and what that test found is already a result: the registration's words admit several readings.

**On real data the comparison scorer never scores before the reference `score` has written its result.**

Part 2 (a later document) adds, in the comparison scorer only: the corrected reading rule, the named random
streams and the sensitivities.

## 1. The tables it reads

**Predictor side.** Phase B's `repo`, `snapshot`, `file`, `measure`, already built on real data, plus two new
tables built from the scan database by the rules of section 2:

| table | key | holds |
|---|---|---|
| `call_degree` | repo, path | `in_degree`, `out_degree` |
| `flux` | repo, path | `amplified_cascading_flux` by the loader's rule, and a flag for a record the loader could not have read |

The stored `measure` row for that value reads "missing" in cases where the loader reads 0, so the comparison
scorer takes it from `flux`, not from `measure`.

**Label side — defined by what the reference loader reads.** The loader takes each outcome's positives from
the outcome file's `files` list, and the primary outcome's commits and the control pool as **ordered**
mappings from commit to paths; the matched control draws commits by position.

| table | key | holds |
|---|---|---|
| `outcome_file` | repo, outcome, path | one row per path in each of the six outcomes' `files` lists |
| `hp_commit` | repo, position (a whole number) | the commit's hash, in the outcome file's order |
| `hp_commit_file` | repo, position, path | that commit's paths; a commit with no path has no row here and still has its `hp_commit` row |
| `pool_commit`, `pool_commit_file` | the same | the control pool |

Label tables are built only inside the scoring job (a later specification), under the protected root. Decoys
use them freely.

New tables are written with the canonical writer of `tools/tables/`. Whole-number keys sort as numbers. If
the writer needs a change for that, the change is made in `tools/tables/` **with every phase A and phase B
table hash unchanged**, and a test says so.

**The universe** is the `file` table's rows with `in_universe = 1`. The loader's universe comes from the scan.
If a scanned unit file is not in the snapshot's tree the two differ, and the input check reports it.

## 2. How each predictor is derived from the tables

Transcribed from the reference loader (`tools/sa3_score.py`, `load`) and checked against it value by value by
the review. Where this text and the loader differ, the input check will show it, and that is a finding.

- **A path** in the scan is the stored path with the scan root and one slash removed from its front if it
  starts with them; otherwise with any leading slashes removed. If two scan rows map to one path, each column takes the
  later non-null value, the telemetry value the later record that parses, and both rows count toward the
  call degrees. (Stored tables cannot hold a duplicate path; phase B refuses one.)
- **Order:** universe paths in Python string order. **Size:** the scan's total line count as a real number;
  a universe file without one, or with one not above zero, stops the run.
- **Bands:** the reference `bands` function on size and path, over the files in use.

| predictor | role | count? | rule | missing when |
|---|---|---|---|---|
| `in_degree` | primary (exploratory) | yes | call rows with a resolved target function whose **target** file is this file | never: none means 0 |
| `in_degree_per_loc` | secondary | no | ÷ size | never |
| `out_degree` | secondary | yes | call rows with a resolved target function whose **source** file is this file, whatever the target file | never |
| `pagerank_score`, `betweenness_score` | secondary | no | the scan's value | null |
| `struct_branch` | **primary, confirmatory** | yes | the scan's value | null |
| `struct_branch_per_loc` | secondary | no | ÷ size | the value is missing |
| `state_danger`, `def_safety`, `state_flux` | secondary | yes | the scan's value | null |
| `state_pointers_alloc` | secondary | yes | `state_pointers` + `state_memory_alloc` | either is null |
| `nest_max` | secondary | yes | from the nesting file | no nesting file; the path not in it; a null element |
| `nest_mean` | secondary | no | from the nesting file | the same |
| `risk_safety_score` | **primary, confirmatory** | no | the scan's value | null |
| `risk_tech_debt`, `risk_cognitive_load`, `risk_state_flux`, `risk_concurrency` | secondary | no | the scan's value | null |
| `risk_safety_nonzero` | secondary | no (the yes/no indicator) | 1 if the score is above zero, else 0 | the score is missing |
| `risk_safety_among_nonzero` | secondary | no | the score | the score is missing or not above zero |
| `amplified_cascading_flux` | **primary, confirmatory** | yes | below | below |
| `amplified_cascading_flux_per_loc` | secondary | no | ÷ size | the value is missing |
| `state_heat_triggers` | secondary | yes | the scan's value | null |

The predictors are scored in the order of this table's source list in the reference (`PREDICTORS`), which the
builder copies exactly and a test compares with the reference's.

**`amplified_cascading_flux`, case by case.** The telemetry record is a text field.

| the record | the value |
|---|---|
| null or empty text | 0 |
| a JSON object without the key | 0 |
| the key present with 0, an empty string, null, false, an empty list or an empty object | 0 |
| the key present with a number, or `true` | that number (`true` is 1) |
| the key present with text that reads as a number | that number |
| the key present with other text, or a non-empty list or object | **missing** |
| text that is not valid JSON | **missing** |
| valid JSON that is not an object (a list, a bare number) | **the loader stops with an error**; `flux` flags the row |
| the key present with `Infinity` or a number too large to represent | +∞ |
| the key present with `NaN` or `"nan"` | **missing** |

No flagged row can exist in SA3's data: the loader has already been called on all 46 repos (phase B's silence
count) and did not stop. The predictor-side check reports the number of flagged rows all the same.

**A file with a missing value is dropped for that predictor, and the size bands are recomputed on the files
that remain** — including the choice between 5 and 10 bands, which counts the files in use.

**Silence** (as at `8fb7fe0`): no present value; or fewer than 10% of present values non-zero; or, for a
predictor that is not a count and not the yes/no indicator, fewer than 20 distinct present values.

## 3. The input check (layer 1)

**Before scoring — predictor side only, no label present.** For each repo the reference loader is called
unchanged with **stub outcome files** (every list empty), exactly as phase B's silence stage did, inside the
read-only sandbox with nothing from the label side bound. The comparison route builds the same arrays from
the tables. Compared, each printed as equal or not equal:

the universe's paths and order · size · every file's band and the band count · **every predictor of section
2, element by element, with missing values in the same places** · silence of every predictor.

This is a session-run stage, like phase B. Its public output is, per repo, a fixed list of named items marked
equal or not equal, the count of flagged `flux` rows, and nothing else; a "not equal" names the item — for a
predictor, its name — never a file or a value. It involves no label, so it can say nothing about one.

**At scoring time — label side.** Inside the scoring job, after the label tables are built: every outcome's
positive flags; the primary outcome's commits, their order and their files; the control pool likewise. If the
universes differ, the label comparison is reported as "not comparable: universe differs" and not per outcome,
so that it cannot carry a bit about named files.

## 4. The comparison scorer

**Its code and its public inputs come from the sealed copies.** It loads the reference statistics module, the
marginals file and the placebo file from the locations the seal verifies, never from the tree under test. (A
fault in the tree under test must not be shared by both routes.)

The loop and the aggregation are **written by reading the reference** (`stage_score`, `control_effects`,
`churn_any`, `summarize`); independence is not claimed for them. What must be matched, item by item:

*Order — also the order in which the shared random stream (seed 2982) is consumed.*
1. Repos: the marginals rows with status `ok`, in the file's order.
2. Outcomes in the order HP, HP_allreverts, HP_revert, HP_cve, HP_fixref, KW; an outcome is scored only if
   the marginals row says it clears its floor.
3. Predictors in the reference's declared order; for outcomes other than HP and KW, primaries only.
4. A silent predictor records "instrument silent"; a design under the pair floor records "under pair floor";
   **neither draws**.
5. Otherwise 200 block permutations are drawn, each one call of the reference's `block_permute` on the files
   in use.
6. After a repo's outcomes, if HP clears its floor: the matched control. K is the smaller of the number of
   primary-outcome commits and of pool commits; **under 5 it is skipped and draws nothing**. Otherwise 200
   draws; in each, K pool commits are drawn by position without replacement, **then**, only if there are more
   than K primary-outcome commits, K of those. **The draws are made before the checks:** a draw in which
   either set of flags is empty or covers every file is discarded after the stream has been consumed.
7. For a predictor with missing values the control uses only the files with a value, bands recomputed, and
   discards the draw for that predictor if either set has no positive or only positives there.
8. The any-commit control draws nothing. It is computed only when between 30 and (files − 30) files are
   touched, and only for primaries whose HP cell is "ok" and which have no missing value.

*Per cell:* the primary statistic; files dropped; the permutation spread (sample standard deviation) and
p-value (the share of draws at least as far from the draws' mean as the observed value is); the non-zero
share; the residualised statistic; the three sensitivity statistics; with 600 or more files in use, the tight
variant (caliper 1.25, 20 bands), null if its design is under the pair floor; for primaries on HP, the
bootstrap interval and the difference from the placebo's surrogate mean.

*Aggregation:* `summarize` (fewer than 3 values: "not fitted"; the t-interval; the two-sided p; the reading
word); the Holm step and the readings **as coded**; the exploratory wording for `in_degree`; the side counts;
the random-effects mean (needs at least 3 repos and every spread above zero); the all-reverts reading; the
ten cuts by name, with "fewer than five repos" for the two family cuts; summaries for every statistic on all
drawn repos, and for the other cuts only for the primary statistic on HP.

## 5. The cell map (layer 3)

The reference's result file and the comparison scorer's result are compared key by key. **Equality is exact:**
the same functions on equal 64-bit arrays give identical bits, so no tolerance is needed. A missing number
equals a missing number, a null equals a null, an absent key equals an absent key, and none of them equals the
others.

| class | what | examples |
|---|---|---|
| **W** | words, sets and whole numbers that use no random draw | a cell's status; which cells exist; files; files dropped; repos above and below zero; the readings "supported", "contradicted", "not detected", "not robust", "not fitted" |
| **D** | real numbers that use no random draw | the primary statistic; the residualised statistic; the non-zero share; the sensitivity statistics; the difference from the surrogate; the bootstrap interval (it reseeds itself); every summary of these |
| **R** | anything that uses the shared stream | the permutation spread and p-value; the matched-control difference and its summary; the random-effects mean; the side counts; "defect-specific" against "tracks activity" |

The reference's bookkeeping keys (`sealed`, `engine`, `not_run`, `unavailable`, `valid`) are compared as W.

The map is printed as counts per class and per repo. **Every not-equal cell counts.** For R cells the first
not-equal one in loop order is named by position (repo, outcome, predictor) and later ones are marked "may
follow from the first"; they are still counted and still fail. W and D cells are never excused. A not-equal
cell is investigated on a decoy study, never on the real cells.

## 6. The independent statistic — a measurement of every reading

The registration's words for the primary statistic (`docs/sa3_registration_consolidated.md`, section 6, items
1 to 4, with the names of the reference functions and one sentence about an earlier check left out):

> 1. **Bands:** equal-count on LOC, 10 if the repo has ≥ 300 files, else 5; ties broken by path.
> 2. **Pairs:** a (positive, negative) pair is eligible if both files are in the same band and their LOC ratio
>    is within 1.5.
> 3. **bAUC:** concordance (ties at half) scored separately on pairs where the positive is the larger file and
>    where it is the smaller, the two weighted equally, plus equal-LOC pairs by their share.
>    **effect = bAUC − 0.5.**
> 4. **Pair floor:** ≥ 100 eligible pairs, ≥ 25 on each side.

The review showed these words leave seven choices open, that a plain loop over pairs reproduces the reference
bit for bit under one combination of readings, and that other natural readings differ by more than 0.005 in
14% to 47% of synthetic cases. So a single independent guess would pass by luck or fail without teaching
anything. Instead:

**The second builder** — a different model, given this section and nothing else of the reference — writes the
statistic as a plain loop over pairs **with every reading below as a switch**, and **states in writing, before
any comparison is run, which reading of each choice it judges the plain meaning of the words.**

| choice | readings to implement (in no particular order) |
|---|---|
| a remainder when files do not divide evenly into bands | chunks of ceil(n ÷ k) with a short last band · the first bands take the extra file · cut points at size quantiles, equal sizes sharing a band · band = floor(rank × k ÷ n) · the last bands take the extra file · chunks of floor(n ÷ k) with the last taking the rest |
| "within 1.5" | strictly inside · inclusive |
| "plus equal-LOC pairs by their share" | three parts weighted equally · the mean of the two sides plus share × the equal-size concordance · each equal-size pair counted half on each side · (1 − share) × the mean of the two sides + share × the equal-size concordance · the mean of the two sides plus share × the equal-size concordance centred at one half |
| pooled or per band | the formula inside each band, bands weighted equally · one formula over all eligible pairs · the formula inside each band, bands weighted by pairs |
| "≥ 100 eligible pairs" | equal-size pairs do not count toward the 100 · they do |
| "the repo has ≥ 300 files" | the repo's ranked files · the files in use for this predictor |
| "ties broken by path" | natural order (digits as numbers) · Python string order |

Interface: the statistic receives the files in use — after files with a missing value are dropped — each with
size, path, value and label, and returns the effect or "no value".

**The second builder must not open** `tools/sa3_stats.py`, `tools/sa3_score.py`, or
`docs/process/reviews/comparison_scorer_spec_review_claude.md` (it marks which reading the reference takes).

**The report:** per reading and per combination, equal to the reference or not, on synthetic cases and on the
decoy studies; and the builder's own prior choice beside the one that matches. **The test of the test:** on
2,000 synthetic cases built to make every choice bite (remainders, equal sizes, pairs exactly at the ratio,
missing values near 300 files, paths with digits), exactly one combination must equal the reference on every
case and every other reading must differ on at least one; if two readings both always agree, the cases are
too weak and the test fails.

Whatever the builder's prior choice turns out to be, **the registration's wording gets an erratum naming the
reading the code takes** (defect log 64). It is entered with the scoring step's documents, when the seal is
next taken.

## 7. Decoy studies

One control repository gives one repo, and with one repo every study summary reads "not fitted". The tests
use **decoy studies**: control repositories run through the unmodified pipeline by the harness and laid out
as one study directory with one marginals file. Two studies, **N** (no effect) and **P** (`branches` planted),
each of 12 repos, built so that the reference's branches are reached:

- 10 marked drawn and 2 not; at least 5 in the C family and 5 not, so both family cuts are fitted;
- repos carrying the names the cuts use (`django`, `circuitpython`, `mediawiki`, `freebsd-src`, `go`, and two
  of the "new language" names), as labels on control repositories;
- at least two under `merge_workflow`; one with a window under 730 days;
- one with 600 or more files in use (the tight variant); one whose pool has fewer than 5 commits; one with
  more primary-outcome commits than pool commits (the control's second draw);
- one predictor silent in one repo, one cell under the pair floor, one repo failing an outcome's floor.

The reference `lock` and `score` run on each study unchanged, inside the harness sandbox, from a copy that is
a git checkout, so that `lock` writes real hashes.

**Coverage is measured, not assumed:** the reference's `stage_score`, `control_effects`, `churn_any` and
`summarize` are run under the standard library's line tracer on both studies, and the report lists every line
not executed. The target is every line except the two "LOCKED" refusals; any other unexecuted line is named
with the reason no decoy reaches it. Reading words that the generator cannot produce (it plants one of the
three confirmatory predictors) are listed as not reached; the corrected reading rule of part 2 is a pure
function and gets its own full truth table.

## 8. Tests

1. **The input check passes** on both studies, every item, every repo; and **fails, naming the item**, when in
   a copy of the tables: one measure value is changed; one is made missing; one `flux` value is changed; one
   call row is removed; and, label side, one positive is moved, two pool commits are swapped in order, and a
   commit with no path is dropped.
2. **Derivation, rule by rule:** every row of section 2's tables, with planted cases for each "missing when"
   and each row of the `flux` table, gives the stated value; bands and the 5-or-10 choice are recomputed on
   the files in use.
3. **The cell map is all-equal** on both studies, every class.
4. **The stream:** each of these changes to the comparison scorer's loop makes R cells not equal while every
   W and D cell stays equal, and the first difference is named correctly: two repos swapped; two outcomes
   swapped; a silent predictor made to draw; the control's second draw made unconditional; the control's
   checks moved before its draws. **And a local fault is not hidden:** one D value changed in a late repo is
   reported although an earlier R cell already differs.
5. **The independent statistic** (section 6), written by the first builder as a skipped test against the
   stated interface; filled by the second builder.
6. **The blind test** (below).
7. **No way out for label-side text:** planted markers in a decoy's outcome files appear in no public output.
8. Every test passes alone, in reverse order, and in one process with every existing test file.

### The blind test of the check

**What it can and cannot show.** The seal certifies that files are the ones recorded; it catches any change to
a sealed file, and it says nothing about whether the two routes agree. Layers 1 and 3 answer a different
question: do the reference route and the table route see the same inputs and reach the same numbers. So the
test is scored **twice per copy: with the seal, and with the seal's verdict withheld.** The second is the one
that tests the comparison layers.

**Who does what.** The builder builds the check and the runner. **The faults, the clean copies, the shuffle
and the key are made afterwards by a different session**, which the builder never sees; the key is a file the
runner does not read. The runner prints, per numbered copy and per layer (seal · placebo · input check ·
cell map W/D · cell map R), "fired" or "silent". Only then is the key opened.

**The copies:** 8 faulty and 8 clean, of study P's reference side (the tree under test and its inputs). The
table route's tables are built once, from the pristine study, before any fault is made. Faults, one per copy,
with the layers expected to fire **written by the fault-writer before the run**:

| fault | where | expected, seal withheld |
|---|---|---|
| the caliper changed in the statistics module of the tree under test | reference code | cell map D |
| the silent rule put back to its `edc5c53` form | reference code | cell map W (cells appear or vanish) and R |
| the control's draws and checks reordered in the reference scorer | reference code | cell map R only |
| one scan value of a confirmatory count predictor changed | an input | input check; cell map D; placebo |
| one scan value of the risk score changed | an input | input check; cell map D (the placebo cannot see it) |
| one path removed from the primary outcome's file list | an input | input check, label side; cell map D |
| two pool commits swapped in order | an input | input check, label side; cell map R only |
| two repos swapped in the marginals file of the tree under test | a document | cell map R, and D summaries (floating-point sums follow repo order) unless the two are the first two |

**Pass:** with the seal withheld, every faulty copy is flagged by at least the expected layers and no clean
copy is flagged by any layer; with the seal, every faulty copy is flagged by the seal as well. The report
gives the full table. Eight faults show that these eight kinds are caught; they do not give a detection rate.

## 9. Deliverables

```
tools/compare/tables.py         call_degree, flux; the five label tables
tools/compare/derive.py         section 2: predictors from tables
tools/compare/input_check.py    section 3, both sides; the predictor-side stage and its validated public output
tools/compare/scorer.py         section 4
tools/compare/cellmap.py        section 5
tools/compare/decoy_study.py    section 7, with the coverage report
tools/compare/blind_runner.py   the runner of the blind test (not the faults, not the key)
tools/compare/README.md, DECISIONS.md
tests/test_compare.py
```

`tools/compare/indep_stat.py` is built afterwards by the second builder. The blind test's copies and key are
made afterwards by another session.

The predictor-side stage needs a launcher that binds declared inputs read-only and validates its public
output. The owner job's launcher is sealed and is not edited or extended: the new stage has its own, in
`tools/compare/`, using `sandbox_ro` and the `check` function of `tools/owner/report.py` by import, and
**its no-free-text property is tested again from scratch** (test 7).

## 10. Rules for the builder

- Decoys only. Never the real study directory, the corpus, the pool, the tables root, the protected root, the
  owner's report directory or `~/.blind`. Every call into SA3 code inside a sandbox.
- Write only the deliverables, and `tools/tables/` only as section 1 allows. No edit to any sealed file, to
  any SA3 tool, or to `tools/control_repo/`, `tools/blind/`, `tools/harness/`, `tools/owner/`.
- Modules are loaded by file path under unique names.
- Run the new tests alone, in reverse order, and together with every existing test file before reporting.
- Report: what was built; test results in all three modes; for each decoy study the cell map's counts and the
  coverage list; every place where section 2 or 4 differs from the reference, as a finding; anything here
  that is wrong, ambiguous, unsafe or impossible.

## Review record

| point | disposition |
|---|---|
| B1 the blind test was decided by a hash; expectations wrong | adopted: scored with the seal withheld; faults by another session; the comparison route reads sealed copies; expectations corrected |
| M1 the claim | adopted: what a match shows is restated |
| M2 the words do not determine the statistic | adopted: every reading as a switch, a prior choice stated first; defect log 64; an erratum is owed |
| M3 the branch-state value cannot come from `measure` | adopted: the `flux` table; the case table |
| M4 section 4 could not be built from its text | adopted: the list of what must be matched; independence not claimed for the loop |
| M5 the cell map | adopted: exact equality; classes for missing, null and absent; nothing excused |
| M6 unexercised branches | adopted: study design and a measured coverage list |
| M7 the owner launcher | adopted: not reused |
| M8 layer 1 and labels | adopted: predictor side before scoring, label side inside the scoring job |
| M9 the canonical writer | adopted: whole-number keys; a commit with no path |
| M10 the universe and `call_degree` | adopted |
| Not adopted | none |
