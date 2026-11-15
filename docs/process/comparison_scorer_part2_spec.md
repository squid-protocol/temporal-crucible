# The comparison scorer, part 2 — the corrected readings, the named streams and the sensitivities (specification)

**Status: specification, 2026-11-15. Nothing built, nothing run.** It carries Amendment 5 sections 4 and 6:
the four corrections printed beside the coded reading, and the closed list of sensitivities. Everything here
runs **in the comparison scorer only** (`tools/compare/`), never in the reference. **No sealed file is edited**
(`docs/sa3_seal_run1.json`).

On real data all of it runs inside the scoring job, after the reference `score` has written its result, and
only as numbers and words printed beside it. The scoring job is a later specification.

## 1. What is new, and what is reused

Part 1 built a second route that reproduces the reference bit for bit. Part 2 adds **variants** of that route.
Each variant is the part 1 scorer with one named thing changed. Because part 1 equals the reference exactly,
**the difference between a variant and the reference is the effect of that one change and nothing else**.
Every variant is tested on the decoy studies in exactly that form.

## 2. The corrected readings (Amendment 5 section 4)

### 2.1 The rule, in words

For each of the three confirmatory tests (B, C, D) on the primary outcome over the drawn repos, inputs are:
the primary statistic's summary at its Holm level, the residualised statistic's summary at the same level,
the matched-control difference's summary at 95%, and whether the placebo gate passed. Each summary reads one
of **"above"** (interval wholly above zero), **"below"** (wholly below), **"across"** (contains zero), or
**"not fitted"** (fewer than 3 repos).

1. **Holm order and levels**, as coded: the three tests are ordered by the primary statistic's two-sided p at
   95% (ties in the order B, C, D); the first is read at 1 − 0.05/3, the second at 1 − 0.05/2, the third at
   0.95.
2. **The step-down stops** at the first test, in that order, whose primary statistic reads "across" or "not
   fitted". A test that reads "below" **does not stop it** (this is the correction of defect 42: a two-sided
   interval wholly below zero rejects the null as surely as one above it). Every test after a stop reads
   **"not detected (Holm: an earlier test was not significant)"**.
3. **For a test not stopped:**
   - primary "below" and residualised "below" → **"contradicted"**;
   - primary "across" or "not fitted" → **"not detected"** (it is the test that stopped the step-down);
   - primary "above" and residualised **not** "above" → **"not robust to the statistic"** (the correction of
     defect 43: whenever the two differ — here, whenever the residualised statistic does not also read above);
   - primary "below" and residualised not "below" → **"contradicted, not robust to the statistic"**;
   - primary "above", residualised "above", control "above" → **"supported, defect-specific"**;
   - primary "above", residualised "above", control not "above" → **"supported, but tracks activity, not
     defects"**.
4. **The gate:** if the placebo gate failed, every test reads **"NO FINDING: the placebo gate failed"**,
   whatever else holds.

**The exploratory test (`in_degree`)** reads "positive", "negative" or "not detected" at 95%, never
"supported" (correction of defect 47). **No other summary anywhere** in the comparison scorer's output prints
"supported" or "contradicted"; secondary predictors, other outcomes and every sensitivity use "above zero",
"below zero", "not detected" with the level stated (defect 47).

**The all-reverts comparison** (correction of defect 48): the "tracks reverted changes, not fixes" reading
compares HP and HP_allreverts **on the same repos** — the drawn repos where both outcomes clear their floor —
at the confirmatory test's Holm level.

### 2.2 Coded beside corrected

For each confirmatory test the output gives the coded reading (part 1's, which equals the reference), the
corrected reading, and **"same"** or **"reading depends on a rule corrected after the estimates were partly
seen"**. A test whose two readings differ is not called confirmatory in any summary.

### 2.3 Built twice

The reading rule is in the second, different-model build's scope (owner, 2026-11-14). It is a pure function of
the inputs above. So:

- the first builder writes `tools/compare/reading.py` from section 2.1;
- a second builder — a different model, given section 2.1 and the function's interface only, and not the
  first builder's file, part 1's scorer or the reference scorer — writes `tools/compare/reading_b.py`;
- the two are compared on **every combination of inputs**: three tests, each with primary and residualised
  in four states and control in four states, in every order of p-values (all six), with ties, and the gate
  passed or failed. A disagreement is resolved by the words of 2.1; where the words do not decide it, it is a
  finding about this specification, and the text is fixed before either file.
- **Named cases** written by hand into the test from section 2.1, each with the expected six words: defect 42's
  case (the smallest p contradicted, the other two above), defect 43's (primary above, residualised across),
  all three above with the control above, the gate failed, and three tests all "not fitted".

### 2.4 Against the reference

On every input combination where the correction does not apply (no "below" ahead of an "above"; primary and
residualised agree), the corrected reading must equal the coded one. A test enumerates this.

## 3. The named random streams (`PU_named_streams`)

The reference uses one stream from seed 2982 across everything, so a result depends on repo order and on which
cells are scored before. The named variant gives each use its own stream:

```
numpy.random.Generator(numpy.random.PCG64(numpy.random.SeedSequence(2982, spawn_key=(r, u, p))))
```

where `r` is the repo's integer key — the first 8 bytes of SHA-256 of the repo's name, as an unsigned
big-endian integer; `u` is 0 for the permutation draws, 1 for the matched control; `p` is the predictor's index
in the reference's `PREDICTORS` order for the permutation draws, and 0 for the control. The outcome's index
is added as a fourth key element for the permutation draws. Exact construction and its test vectors are in
`DECISIONS.md`.

**Tests:** under named streams, reversing the repo order, and dropping one predictor from the scored set,
change no other cell at all; under the registered stream (part 1) both change R cells. On both decoy studies
the named variant's D and W cells equal part 1's.

## 4. The sensitivities (Amendment 5 section 6)

**The closed list.** Amendment 4's — S1, S2, S3, S4, S6, S7, S9, the go and django cut, the earlier eight, the
two family cuts, `PU_django_circuitpython_removed`, `PU_mediawiki_freebsd_removed` — are already computed by the
reference and reproduced by part 1; part 2 adds nothing for them. The ten of Amendment 5, and how each is made:

| name | what changes | how it is made, with no sealed file edited | what the pre-scoring counts already say |
|---|---|---|---|
| `PU_reachable_universe` | universe files that the history walk's own unit rule excludes are removed | from phase B's `file` table (`history_can_touch`) | **0 such files in every repo**: equals the frozen run |
| `PU_unreachable_made_reachable` | those files stay ranked and can be positive | — | **0 such files**: equals the frozen run |
| `PU_generic_dirs_restored` | files excluded only by `(^|/)cache/`, `(^|/)dist/`, `(^|/)[Ee]xtern(als?)?/`, `(^|/)env/`, and scanned, are ranked again | below | at most 19 such files in a scored repo (go); 3 of them scanned |
| `PU_tracker_keys_case_sensitive` | a tracker key with a lower-case letter is not a fix reference | the reference outcome builder run unchanged on a copy of the link harvest without those rows — exactly the owner job's second run | 2 commits in the study, 1 in a scored repo (bun) |
| `PU_named_streams` | section 3 | the part 1 scorer with named streams | — |
| `PU_late_revert_ticket_dropped` | a revert whose target is after the cut does not qualify through a ticket its message quotes | the reference outcome builder run unchanged on a copy of the harvest **without the fix-reference rows of every commit that also has a revert link**; for the primary outcome this is exactly the definition, because a revert whose target is before the cut qualifies through the revert anyway. The exclusive tiers can change; that is reported | not counted yet; counted by this variant |
| `PU_new_completeness` | repos under 90% completeness measured against the tree are dropped | phase B's counts | **drops the same six repos** as the registered measure: equals the frozen run |
| `PU_nesting_floor` | a repo whose nesting file covers under 95% of its files has its nesting cells dropped | phase B's counts | **equals the frozen run**: coverage is 100% wherever a nesting file exists; racket has none and its nesting cells are already silent |
| `PU_window_assertion` | a repo whose window ends before it starts, or with no usable commits, is dropped | phase B's counts | **no repo fails**: equals the frozen run |
| S8 | rename following | — | **not run**, as Amendment 4 already reports. Building it is a new rule, not a variant, and is out of this specification |

**The five that equal the frozen run** are still computed as variants, so that "equals" is a measured result
(every cell equal to part 1's), not an assertion.

**`PU_generic_dirs_restored`, how.** The universe comes from the reference `universe()`, which reads GitHub's
lists through `laws_units` and checks their SHA-256, so the lists cannot be swapped. The variant therefore
builds its universe as the part 1 universe **plus** the files whose only exclusion reason in phase B's `file`
table is one of the four patterns and that have scan rows. Their labels need the outcome builder to see them as
unit files, which it does not. So the variant's outcome flags for the restored files are taken from a run of
the reference outcome builder with the variant universe supplied the way the harness supplies inputs — **if
that can be done without editing a sealed file**. If it cannot, the variant is reported as "not run: the
restored files' labels cannot be obtained without changing the outcome builder", with the count of files it
would have restored. The builder finds out which, and does not work around it.

**Each variant's output** is the full set of summaries the reference produces, under the variant's name, with
the vocabulary of section 2.1 for non-confirmatory text. Beside each, the difference from the frozen run in
each confirmatory cell.

## 5. Tests, on the decoy studies of part 1

1. The corrected reading rule: section 2.3's exhaustive comparison of the two builds, the named cases, and
   section 2.4.
2. The named streams: section 3's tests.
3. For each sensitivity: on a decoy study where it **should** change something (made so by editing the decoy —
   a lower-case tracker key in a qualifying commit's message and harvest, a late revert quoting a ticket, files
   under `cache/` that the engine scanned, a repo with a window that ends before it starts, a nesting file
   covering 80% of files), the variant changes exactly the cells it should; on a decoy where it should change
   nothing, every cell equals part 1's.
4. **The harvest copies** of the two outcome-builder variants: the copy differs from the original only in the
   deleted rows, keeps its `meta` rows, and the reference outcome builder reproduces the stored outcome file
   exactly from the **unmodified** copy (the owner job's check).
5. No variant's output prints "supported" or "contradicted" outside section 2's confirmatory readings.
6. Every test passes alone, in reverse order, and with every existing test file in one process.

## 6. Deliverables

```
tools/compare/reading.py          section 2 (the first build)
tools/compare/streams.py          section 3
tools/compare/variants.py         section 4: the variant scorers and their output
tools/compare/harvest_variant.py  the two harvest copies and the outcome builder runs
tests/test_compare_part2.py
```

`tools/compare/reading_b.py` is written afterwards by the second builder.

## 7. Rules for the builder

As part 1: decoys only; none of the forbidden paths; every call into SA3 code in a sandbox; no edit to a sealed
file, to `tools/owner/`, `tools/harness/`, `tools/control_repo/`, `tools/blind/` or `tools/tables/`; modules
loaded by path under unique names; part 1's files under `tools/compare/` are extended only by import (a
subclass or a hook), with every part 1 test still passing and part 1's cell maps on both studies still
all-equal. Report: what was built; test results in all three modes; for each variant, on each decoy study,
the cells it changed; whether `PU_generic_dirs_restored` could be made; anything here that is wrong, ambiguous,
unsafe or impossible.
