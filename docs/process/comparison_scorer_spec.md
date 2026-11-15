# The comparison scorer — specification (part 1: inputs, the scorer, the cell map, the blind test)

**Status: specification, 2026-11-15. Nothing built, nothing run.** It carries Amendment 5 section 9, layers 1
and 3, and the blind seeded-fault test (as corrected by the erratum). Built by one session from this document;
reviewed by a different model. **No sealed file is edited** (`docs/sa3_seal_run1.json` lists them): not the
reference code, not the six sealed documents, not `tools/owner/`, `tools/harness/sandbox.py` or
`sandbox_ro.py`.

## What it is for, and what it is not

SA3's confirmatory result will come from the reference scorer, run once, unchanged. Nothing replaces it. The
comparison scorer is a **second route to the same numbers**: it reads its inputs from tables, derives the
predictors by rules written out here, runs its own scoring loop and aggregation, and its result is compared
with the reference's, cell by cell.

What a match is evidence of: that the inputs the reference read are the ones recorded; that the derivation of
every predictor, the handling of missing values, the order of work and the aggregation are what the
registration says; and, for the three confirmatory cells, that the statistic itself is what the registration
says. What it is **not** evidence of: that the registered statistic is a good one, or that the labels mean
what they are taken to mean.

**How independent it is, stated.** It uses the reference statistics module (`tools/sa3_stats.py`) unchanged
for every statistic and for the block permutation, because the random-dependent cells can only match if the
shared random stream is consumed in exactly the reference's way. On top of that, **one statistic — the primary
one, on the confirmatory cells — is also computed by an independent implementation written from the
registration's words** (section 6 below). Everything else in the statistics module has had no independent
check, and the report says so.

**On real data the comparison scorer never runs before the reference scorer.** Its inputs are built and
compared beforehand (layer 1). Its scoring stage runs only after the reference `score` has written its result,
in the same owner-run job. The order is fixed by the scoring step's specification, which follows this one.

Part 2 (a later document) adds, in the comparison scorer only: the corrected reading rule, the named random
streams and the sensitivities of Amendment 5 section 6.

## 1. The tables it reads

The predictor side is phase B's output (`repo`, `snapshot`, `file`, `measure`), already built on real data.
The rest is new. Every table has a canonical hash as in `tables_spec.md`.

**Label-side tables — defined by what the reference loader reads, nothing more.** The loader takes each
outcome's positives from the outcome file's `files` list, and the primary outcome's commits and the control
pool as ordered mappings from commit to paths; the matched control draws commits **by position** in those
mappings. So:

| table | key | holds | built from |
|---|---|---|---|
| `outcome_file` | repo, outcome, path | one row per path in the `files` list of each of the six outcomes | the outcome file |
| `hp_commit` | repo, position, path | the primary outcome's commits **in the outcome file's order**, with each commit's hash and paths | the outcome file |
| `pool_commit` | repo, position, path | the control pool's commits in the outcome file's order | the outcome file |

They are protected: written under the protected root by an owner-run stage, never in a public directory.
They add nothing to what the outcome files hold.

**One more predictor-side table.** The loader counts call rows per file; phase A left that out.

| table | key | holds | built from |
|---|---|---|---|
| `call_degree` | repo, path | `in_degree`, `out_degree` | the scan database's call table, by the rule of section 2 |

## 2. How each predictor is derived from the tables

These are the reference loader's rules (`tools/sa3_score.py`, `load`), written out. The comparison scorer
implements **this text**. Where the text and the loader differ, that is a finding, and layer 1 will show it.

- **The universe and its order:** the `file` rows with `in_universe = 1`, paths in sorted order. Size is the
  scan's total line count; a universe file without one stops the run.
- **Bands:** `sa3_stats.bands` on size and path, over the files in use.
- **A path** in the scan is the stored path with the scan root removed from its front.

| predictor | rule | missing when |
|---|---|---|
| `in_degree` | the number of call rows with a resolved target function whose target file is this file | never: no rows means 0 |
| `out_degree` | the number of such rows whose source file is this file | never |
| `pagerank_score`, `betweenness_score`, `struct_branch`, `state_danger`, `def_safety`, `state_flux`, `state_heat_triggers`, the five `risk_` scores | the scan's value | the scan's value is null |
| `state_pointers_alloc` | `state_pointers` + `state_memory_alloc` | either is null |
| `in_degree_per_loc`, `struct_branch_per_loc`, `amplified_cascading_flux_per_loc` | the value ÷ size | the value is missing |
| `risk_safety_nonzero` | 1 if `risk_safety_score` > 0, else 0 | the score is missing |
| `risk_safety_among_nonzero` | `risk_safety_score` | the score is missing **or not above zero** |
| `amplified_cascading_flux` | the value of that key in the file's telemetry record; **0 when the record is empty, the key is absent, or the value is empty or zero** | the record cannot be parsed, or the value cannot be read as a number |
| `nest_max`, `nest_mean` | from the nesting file | the repo has no nesting file, or the file is not in it |

**A file with a missing value is dropped for that predictor, and the size bands are recomputed on the files
that remain.** This changes which files are compared with which; it is part of the rule.

**Silence** (as at `8fb7fe0`): a predictor is silent in a repo when fewer than 10% of its present values are
non-zero, or it has no present value; or, for a continuous score only (not a count, not the yes/no indicator),
when it has fewer than 20 distinct values.

## 3. Layer 1 — the inputs are the same (it can fail)

For each repo, the reference loader is called unchanged, and the comparison scorer builds the same things from
the tables. Compared, each printed as equal or not equal:

the universe's paths and their order · size · the band of every file and the band count · **every predictor,
element by element, missing values in the same places** · every outcome's positive flags · the primary
outcome's commits, their order and their files · the control pool likewise.

On real data this reads labels and predictors in one process, so it is an **owner-run stage**, with the
launcher and validator of `tools/owner/` (imported, not edited): its public output is, per repo, a fixed list
of named items each marked equal or not equal, and nothing else. A "not equal" names the item — for a
predictor, its name — never a file, a commit or a value.

## 4. The comparison scorer

**The scoring loop, in the reference's order** — which is also the order in which the shared random stream
(seed 2982) is consumed:

1. Repos: the rows of the committed marginals file with status `ok`, in the file's order.
2. For each repo, the six outcomes in the order HP, HP_allreverts, HP_revert, HP_cve, HP_fixref, KW; an
   outcome is scored only if the marginals row says it clears its floor.
3. For each outcome, the predictors in the reference's declared order; for outcomes other than HP and KW,
   primaries only.
4. A silent predictor, or a design under the pair floor, records its status and **draws nothing**.
5. Otherwise the cell's statistics are computed and **200 block permutations are drawn**, each one call of the
   reference's `block_permute` on the files in use.
6. After a repo's outcomes, if HP clears its floor: the matched control, 200 draws; in each, K control commits
   are drawn without replacement **by position**, then, only if the primary outcome has more than K commits, K
   of those; K is the smaller of the two counts, and under 5 the control is skipped and draws nothing.
7. Then the any-commit control for the primaries, which draws nothing.

**Aggregation**, as the reference does it: the per-cell statistics; the study summaries with their t-intervals;
the Holm step and the readings **as coded**; the side counts; the random-effects mean; the all-reverts reading;
the cuts. (The corrected readings are part 2.)

It reads `docs/sa3_placebo.json` for the gate's verdict and the surrogate means, as the reference does.

## 5. Layer 3 — the cell map

The reference's result file and the comparison scorer's result are compared cell by cell.

| kind of cell | examples | rule |
|---|---|---|
| words and sets | a cell's status, a reading, the repos in a summary, which cells exist | exactly equal |
| whole numbers | files, dropped files, counts of repos above and below zero | exactly equal |
| real numbers that use no random draw (**D**) | the primary statistic, the residualised statistic, the non-zero share, the three sensitivity statistics, the difference from the surrogate, the bootstrap interval (it reseeds itself) | within 1e-12 |
| real numbers that use the shared stream (**R**) | the permutation p-value and spread, the matched-control difference, and everything built on them: the random-effects mean, the side counts, "defect-specific" | within 1e-12 — which requires the stream to have been consumed identically up to that cell |

The map is printed as counts per kind and per repo: equal, not equal. **The first not-equal R cell in loop
order is named by its position** (repo, outcome, predictor); R cells after it are expected to differ and are
reported as "after the first difference", so that one slip is not read as hundreds.

A not-equal cell is investigated on a decoy study, never on the real cells.

## 6. The independent statistic

For the three confirmatory predictors on the primary outcome, in every scored repo, the primary statistic is
also computed by an implementation that **does not import the reference statistics module**, written from
these words of the registration:

> 1. **Bands:** equal-count on LOC, 10 if the repo has ≥ 300 files, else 5; ties broken by path.
> 2. **Pairs:** a (positive, negative) pair is eligible if both files are in the same band and their LOC ratio
>    is within 1.5.
> 3. **bAUC:** concordance (ties at half) scored separately on pairs where the positive is the larger file and
>    where it is the smaller, the two weighted equally, plus equal-LOC pairs by their share.
>    **effect = bAUC − 0.5.**
> 4. **Pair floor:** ≥ 100 eligible pairs, ≥ 25 on each side.

(`docs/sa3_registration_consolidated.md`, section 6, items 1 to 4, quoted exactly.)

It is written as a plain loop over pairs. Compared with the reference's value within 1e-9. **Where the words
above leave a choice open** (how "equal-count" treats a remainder; how "by their share" combines the three
parts), the builder does not look at the reference to decide: it records each reading, implements the one it
judges the plain meaning, and the comparison shows whether the reference agrees. A disagreement that traces to
such a choice is a finding about the registration's wording, reported as that.

This is the part to give to the **second, independent builder** (`research_codebase_spec.md` section 9): a
different model, from this section alone, without sight of the first build.

## 7. Decoy studies

One control repository gives one repo, and with one repo every study summary reads "not fitted". So the tests
need **decoy studies**: several control repositories run through the unmodified pipeline by the harness and
laid out as one study directory with one marginals file, as phase B's rehearsal did.

- **Study N** (no effect) and **study P** (`branches=0.5` planted): 8 repos each, 6 marked drawn, default size,
  ten-year span, Python and C mixed, at least two under `merge_workflow`.
- The reference `lock` and `score` are run on each decoy study unchanged, inside the harness sandbox, from a
  copy that is a git checkout, so that `lock` writes real hashes.

## 8. Tests

1. **Layer 1 passes** on both decoy studies, every item, every repo; and **fails, naming the item**, when in a
   copy of the tables: one measure value is changed; one value is made missing; one positive is moved; two
   commits of the pool are swapped in order; one call row is removed.
2. **Derivation, rule by rule:** for each row of section 2's table, a decoy scan with planted cases (a null, a
   zero, an empty telemetry record, a record that does not parse, a non-positive score, a file absent from the
   nesting file) gives the stated value or the stated "missing", and the bands are recomputed.
3. **Layer 3 passes:** on both decoy studies every cell of every kind is equal.
4. **The stream:** changing the comparison scorer's loop in each of these ways makes R cells not equal while
   every D cell stays equal, and the first difference is named correctly: two repos swapped; two outcomes
   swapped; a silent predictor made to draw; the control's second draw made unconditional.
5. **The independent statistic** equals the reference's on every confirmatory cell of both studies; and on
   2,000 small random cases, including ties in size, ties in value, and bands with a remainder.
6. **The blind test of the check as a whole** (Amendment 5 section 9 and its erratum). Ten copies of study P's
   reference side: five clean, five each carrying one fault. **Before the test is run, the layer expected to
   catch each fault is written down:**

   | fault | expected to be caught by |
   |---|---|
   | one line of the reference scorer changed (the caliper) | the seal (code hash) and layer 3, D cells |
   | the silent rule put back to its `edc5c53` form | the seal and layer 3 |
   | one scan value of a primary predictor changed | the seal (input hash), layer 1, and the placebo reproduction |
   | one path removed from an outcome file's primary list | the seal and layer 1 |
   | two repos swapped in the marginals file | the seal (document hash) and layer 3, R cells only |

   The copies are shuffled and labelled by number. The check — seal verification, the placebo reproduction,
   layer 1, layer 3 — is run on each and prints "flagged" or "not flagged" with the layers that fired. Only
   then is the key opened. **Pass:** all five faulty copies flagged, by at least the expected layers; none of
   the five clean copies flagged.
7. **No way out for label-side text,** as for the owner job: planted markers in a decoy's outcome files appear
   in no public output of layer 1 or of the cell map.
8. Every test passes when run alone, in reverse order, and in one process with every existing test file.

## 9. Deliverables

```
tools/compare/label_tables.py   outcome_file, hp_commit, pool_commit (an owner-run stage on real data)
tools/compare/call_degree.py    the call-degree table
tools/compare/derive.py         section 2: predictors from tables
tools/compare/layer1.py         section 3
tools/compare/scorer.py         section 4
tools/compare/cellmap.py        section 5
tools/compare/decoy_study.py    section 7
tools/compare/blind_test.py     test 6
tools/compare/README.md, DECISIONS.md
tests/test_compare.py
```

`tools/compare/indep_stat.py` (section 6) is **not** built by this builder. It is built afterwards by the
second builder; test 5 is written by the first builder against a stated interface and left skipped until the
file exists.

## 10. Rules for the builder

- Decoys only. Never the real study directory, the corpus, the pool, the tables root, the protected root or
  `~/.blind`. Every call into SA3 code inside a sandbox.
- Write only the deliverables. No edit to any sealed file (section header), to any SA3 tool, or to
  `tools/tables/`, `tools/control_repo/`, `tools/blind/`. If a sealed file would need a change, report it.
- Modules are loaded by file path under unique names, never by a bare name that another tool directory also
  uses.
- Run the new tests alone, in reverse order, and together with every existing test file before reporting.
- Report: what was built; test results in all three modes; for each decoy study the cell map's counts; the
  blind test's outcome with the key; every place where section 2 or section 4 turned out to differ from the
  reference, as a finding; anything here that is wrong, ambiguous, unsafe or impossible.
