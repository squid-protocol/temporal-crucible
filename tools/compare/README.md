# The comparison scorer, part 1

A second route to the numbers of the reference scorer (`tools/sa3_score.py`), built to
`docs/process/comparison_scorer_spec.md` (Revision 2): tables in, predictors derived by written rules, its own
scoring loop, an input check, a cell-by-cell comparison, decoy studies with a measured coverage list, and the
runner of a blind test. Built and tested on decoys only. Every choice the spec did not make is in
`DECISIONS.md`.

**What a full match shows** (spec, "What it is for"): the reference read the inputs that are recorded, and the
derivation, the missing-value handling, the order of work and the aggregation **as written in the spec** are
what the reference did. Both routes share `sa3_stats.py`, numpy and scipy, and the loop was transcribed from
the reference: a match is agreement between two routes and one description, not evidence that the code does
what the registration says.

## Files

| file | what |
|---|---|
| `tables.py` | `call_degree`, `flux` (predictor side, from a scan database, by the loader's rules) and the five label tables (`outcome_file`, `hp_commit`, `hp_commit_file`, `pool_commit`, `pool_commit_file`); written with `tools/tables/canon.py` (whole-number `position` keys sort as numbers); the sandboxed predictor stage |
| `derive.py` | section 2: the loader-shaped arrays from phase B's `repo`/`file`/`measure` and the tables above |
| `input_check.py` | layer 1: the reference `load()` unchanged in `sandbox_ro` with stub outcome files, the comparison, the validated public output (`tools/owner/report.py`'s `check`, imported by file) |
| `scorer.py` | section 4: the comparison scorer; reads the statistics module, the marginals file and the placebo file from a **sealed copies** directory, never from the tree under test |
| `cellmap.py` | layer 3: exact, key-by-key comparison of two result files, classes W / D / R |
| `decoy_study.py` | section 7: two 12-repo decoy studies, the reference placebo / lock / score on each (in a git checkout), the line-traced score and the coverage list |
| `blind_runner.py` | runs the check on numbered copies of study P's reference side and prints fired / silent per layer, with and without the seal; makes no fault and reads no key |
| `_util.py` | loading by file under unique names, the float encoding, the sealed statistics module's import check |

`indep_stat.py` (section 6) is NOT here: it is written by a second builder who must not see the reference.
`tests/test_compare.py` test 5 is its skipped placeholder against the stated interface.

## Use (decoys)

```
python3 tools/compare/decoy_study.py build --which N --base DIR       # ~6 min; P likewise
python3 tools/compare/decoy_study.py coverage --base DIR
python3 tools/compare/tables.py predictor --decoy D --out OUT          # D: study/, pool/, docs/
python3 tools/compare/input_check.py --decoy D --tables PB --compare-tables CT --sealed SC --ref TREE \
        --scratch S --out O.json
python3 tools/compare/scorer.py --tables PB --compare-tables CT --labels LT --sealed SC --out result.json
python3 tools/compare/blind_runner.py seal --side PRISTINE --out seal.json
python3 tools/compare/blind_runner.py run --copies DIR --tables T --sealed SC --seal seal.json --work W --out O
COMPARE_STUDY_CACHE=~/.claude/jobs/<id>/tmp/cache python3 -m pytest -p no:cacheprovider tests/test_compare.py
```

The real-data entry points (`tables.py predictor --real`, `input_check.py --real`) need
`--i-am-the-reviewer-session`, take every real location as a parameter whose default is the production path,
and touch the study only inside `sandbox_ro`, whose guard reads the mount table first. Neither was run by the
builder. Label tables are built on real data only inside the scoring job (a later specification): the label
CLI refuses `--real`.

## What runs where

- The reference loader, `stage_score`, `placebo`, `lock` and the pipeline run only inside sandboxes
  (`sandbox_ro` for the loader with declared inputs; the harness sandbox for the pipeline and the reference
  stages on a decoy study).
- In-process, the only SA3 module is the sealed copy of `sa3_stats.py`, after an `ast` check that it imports
  nothing but `sys`, `numpy`, `scipy.stats`.
- The comparison scorer and the cell map run in-process on tables and JSON files.

# Part 2: the corrected readings, the named streams, the sensitivities

Built to `docs/process/comparison_scorer_part2_spec.md` (Revision 2), on decoys only; choices in `DECISIONS.md`
(part 2, P1-P19, F10-F12).

| file | what |
|---|---|
| `reading.py` | section 2: `coded` (the reference's Holm block) and `corrected` (with the two changes of the owner's note); the predicate; sections 2.2 and 2.3; the table for the owner (`python3 tools/compare/reading.py table --out docs/process/reading_rule_table.md`) |
| `reading_b.py` | the second build of section 2.1, by a builder of another model (not written here) |
| `streams.py` | section 3: the spawn keys, the generators, `NamedStreams` (part 1's scorer with its one hook overridden) |
| `harvest_variant.py` | the two harvest copies (the owner job's `stage_copy` and `strip_harvest`, imported by file; the late-revert resolution), the reference outcome builder run unchanged in `sandbox_ro` on each |
| `variants.py` | section 4: the variants in the spec's order, their baselines, floors and output |
| `scorer.py` | part 1's scorer, with one hook added: `stream(key, rng)` returns the shared stream |

```
python3 tools/compare/reading.py counts
python3 tools/compare/harvest_variant.py variant --study D/study --pool D/pool --repos a,b --variant late \
        --scratch S --out O.json
python3 tools/compare/variants.py --decoy-study BASE/N --scratch S --out O.txt
COMPARE_STUDY_CACHE=~/.claude/jobs/<id>/tmp/cache python3 -m pytest -p no:cacheprovider tests/test_compare_part2.py
```

`--real` is refused by both command lines: on real data the variants run only inside the scoring job (a later
specification). In-process: `reading.py` (pure), the comparison scorer, tools/owner's code; the reference
`stage_score` (on synthetic readings, test 1f) and the reference outcome builder run only in `sandbox_ro`.
