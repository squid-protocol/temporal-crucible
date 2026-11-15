# The comparison scorer, part 2 — the corrected readings, the named streams and the sensitivities (specification)

**Status: Revision 2, 2026-11-15, after an independent review and two owner rulings. Nothing built, nothing
run.** It carries Amendment 5 sections 4 and 6. Everything here runs **in the comparison scorer only**
(`tools/compare/`), never in the reference, and on real data only inside the scoring job, after the reference
`score` has written its result, as words and numbers printed beside it. **No sealed file is edited.**

**What Revision 2 changed** (`reviews/comparison_scorer_part2_spec_review.md`: 3 blockers, 10 major, 9 minor):

- **The corrected reading rule is now exactly the coded rule with the two corrections Amendment 5 names** and
  nothing else. The first version reworded tests the corrections do not touch and introduced a reading,
  "contradicted, not robust", that no registered text names; under it even a plain null would have been
  flagged "reading depends on a corrected rule".
- **A variant is compared with the right baseline.** On the shared random stream, any change to one repo's
  labels shifts the draws of every later repo, so a variant that changes labels or the universe is scored on
  named streams and compared with `PU_named_streams`, not with the frozen run.
- The variants print no Holm level and no confirmatory word; two sensitivities are redefined; one is reported
  "not run" for the right reason; the five already known to equal the frozen run are reported from the counts.

## 1. Owner rulings, 2026-11-15

1. **Defect 43, read literally:** "not robust to the statistic" whenever the primary and the residualised
   statistic read differently, whatever the primary reads.
2. **The reading rule is checked twice:** a second, different-model build compared on every input, **and** the
   full coded-against-corrected table published for the owner to read.

These close choices the registration left open, after the estimates were partly seen. They are entered as a
dated note to Amendment 5 together with the second erratum at the scoring step (the registration is sealed
until then): `docs/sa3_amendment5_note_reading_draft.md`.

## 2. The corrected readings (Amendment 5 section 4)

### 2.1 The rule: the coded rule with two changes

The coded rule (`tools/sa3_score.py`, the Holm block of `stage_score`): order the three confirmatory tests by
the primary statistic's two-sided p (ties keep the order B, C, D); read each at its Holm level; then

```
still = True
for each test in that order:
    reading = primary's reading            # "supported" | "contradicted" | "not detected" | "not fitted"
    if reading == "supported" and not still:
        reading = "not detected (Holm: an earlier test in the family failed)"
    if primary's reading != "supported":            # ← change 1 alters this line
        still = False
    if reading == "supported" and residualised's reading != "supported":   # ← change 2 alters this line
        reading = "not robust to the statistic"
    elif reading == "supported":
        reading = "supported, defect-specific" if control reads "supported" else
                  "supported, but tracks activity, not defects"
    if the placebo gate failed:
        reading = "NO FINDING: the placebo gate failed"
```

**Change 1 (defect 42).** The step-down stops at the first test whose primary reads neither "supported" nor
"contradicted":

```
    if primary's reading not in ("supported", "contradicted"):
        still = False
```

**Change 2 (defect 43, owner ruling 1).** "Not robust" whenever the two statistics read differently, except for
a test already reworded by the Holm step:

```
    if reading is not the Holm sentence and primary's reading != residualised's reading:
        reading = "not robust to the statistic"
    elif reading == "supported":
        (as coded)
```

**Nothing else changes.** Every word the corrected rule can print is a word the coded rule can print. Where
neither change applies, the two give the same words, letter for letter.

**Counted beforehand** (the author's enumeration, the reviewer's equal; the space of Amendment 5: each of three
tests gets one of three readings for the primary and three for the residualised, 729 combinations):

| | readings differ | the corrected rule gives more "supported" |
|---|---|---|
| change 1 alone | 135 | 51 |
| change 2 alone | 604 | 0 |
| both | 631 | 51 |
| all three tests "not detected" on both statistics (the plain null) | same | — |

Change 2 never creates a "supported": it can only turn a reading into "not robust". The large count is a
property of the enumeration, which pairs every primary reading with every residualised one; in data the two
statistics usually agree, and then change 2 does nothing.

### 2.1a The interface (both builds)

```
coded(tests, gate_valid)     -> {name: words}
corrected(tests, gate_valid) -> {name: words}
```

`tests` is a list of three mappings, one per confirmatory test, in the order B, C, D, each with `name` (str),
`p` (float, the primary statistic's two-sided p at 95%), `primary`, `residualised` (each one of "supported",
"contradicted", "not detected", "not fitted") and `control` ("supported" or anything else). `gate_valid` is a
bool. The result maps each name to the words of section 2.1. Holm order is ascending `p`, ties kept in the
order given. Pure: no input, no output, no randomness.

### 2.2 Printed beside the coded reading

For each confirmatory test: the coded reading (part 1's, equal to the reference), the corrected reading, and
**"same"** or **"reading depends on a rule corrected after the estimates were partly seen"**. A test whose two
readings differ is not called confirmatory in any summary.

### 2.3 The other two corrections

- **Defect 47:** outside the three confirmatory tests nothing prints "supported" or "contradicted". The
  exploratory test reads "positive", "negative" or "not detected"; every other summary reads "above zero",
  "below zero" or "not detected", with its level.
- **Defect 48:** the "tracks reverted changes, not fixes" reading compares HP and HP_allreverts on **the same
  repos** — the drawn repos where both clear their floor. It prints, per confirmatory test, the HP_allreverts
  summary at the test's Holm level on that repo set, the number of repos, and "tracks reverted changes, not
  fixes" exactly when that summary reads "above zero" and the corrected reading does not begin with
  "supported".

### 2.4 Checks

- **Two builds.** The first builder writes `tools/compare/reading.py` from section 2.1. A second builder — a
  different model, given section 2.1 and the interface, and not the first builder's file, part 1's scorer or
  the reference scorer — writes `tools/compare/reading_b.py`. They are compared on every input: three tests;
  primary and residualised each "supported", "contradicted", "not detected" or "not fitted"; control
  "supported" or not; every order of the three p-values, ties included; the gate passed or failed.
- **Against the coded rule.** A predicate "a correction applies" is computed for each input: change 1 applies
  when some test reading "contradicted" comes before a test reading "supported" in Holm order; change 2 applies
  when a test's two statistics read differently. On every input where neither applies, the corrected words
  equal the coded words; the test enumerates this and must find no exception.
- **The table for the owner** (`docs/process/reading_rule_table.md`, generated): every distinct combination of
  the three tests' readings in Holm order (with the control and the gate), the coded words and the corrected
  words side by side, the rows where they differ marked. It is regenerated by a test and must equal the
  committed file.
- **Named cases** written by hand: defect 42's (the first test contradicted, the next two supported); defect
  43's (primary supported, residualised not detected; and primary not detected, residualised supported); the
  plain null; the gate failed; all three "not fitted".

## 3. The named random streams (`PU_named_streams`)

Each use of randomness gets its own generator:

```
numpy.random.Generator(numpy.random.PCG64(numpy.random.SeedSequence(2982, spawn_key=KEY)))
```

- permutation draws for a cell: `KEY = (r, 0, o, p)`;
- the matched control for a repo: `KEY = (r, 1)`;

where `r` is the first 8 bytes of SHA-256 of the repo's name, read as an unsigned big-endian integer; `o` is the
outcome's index in (HP, HP_allreverts, HP_revert, HP_cve, HP_fixref, KW); `p` is the predictor's index in the
reference's `PREDICTORS` order. The bootstrap interval reseeds itself and uses no stream. `DECISIONS.md` gives
test vectors (the first three draws for two keys).

Part 1's scorer gains **one hook**: a function returning the generator for a given key, which in part 1 returns
the shared stream every time. That edit to `tools/compare/scorer.py` is allowed, provided every part 1 test
still passes and part 1's cell maps on both studies stay all-equal.

**Tests.** Under named streams: reversing the repo order leaves every **per-repo cell** identical bit for bit,
and every study summary equal within 1e-12 relative (a sum's value depends on the order of its terms); dropping
one predictor from the scored set leaves every other per-repo cell identical, **except the matched-control
cells of that repo**, which draw for all predictors together. Under the shared stream both tests change R cells.

## 4. The sensitivities (Amendment 5 section 6)

**The baseline.** A variant that changes a repo's labels or universe is scored **on named streams** and its
difference is taken **from `PU_named_streams`**, not from the frozen run: on the shared stream, one commit fewer
in one repo changes how many draws the control consumes and so moves every later repo's random cells.

**Commit order.** A rebuilt outcome file lists commits in an order that depends on the interpreter's hash seed,
and the matched control draws commits by position. In a variant's label tables, commits that are also in the
frozen file keep the frozen file's order; commits new to the variant follow, in hash order.

**Floors.** A variant whose outcome file is rebuilt takes each outcome's floor verdict from the rebuilt file;
every other variant uses the frozen marginals file's.

**Output.** Every variant prints, for each primary on each outcome, the mean and its 95% interval over the drawn
repos, the number of repos, and "above zero", "below zero" or "not detected" — **no Holm level and no
confirmatory word** (Amendment 5 section 6). Beside each, the difference from its baseline. Every variant is
printed whatever it shows, in the order of the table below.

| name | what changes | how | known before scoring |
|---|---|---|---|
| `PU_named_streams` | section 3 | part 1 with named streams | — |
| `PU_tracker_keys_case_sensitive` | a tracker key with a lower-case letter is not a fix reference | the reference outcome builder run unchanged on a copy of the link harvest without the rows of kind `issue_fix` whose value has a hyphen and a lower-case letter (the owner job's second run) | 2 commits in the study, 1 in a repo scored on the primary outcome (bun) |
| `PU_late_revert_ticket_dropped` | a revert whose target was made after the cut does not qualify through a fix reference its message carries | the reference outcome builder run unchanged on a copy of the harvest without the `issue_fix` rows of each commit that has a revert link **whose target resolves to a commit after the cut**. Resolution follows Amendment 5 section 5: a unique match of the stored prefix among reachable commits in the history; for a commit brought in by a merge, the merge's time. Unresolved reverts and commits that only quote a `Revert "` line keep their rows. Trailers and CVE ids are separate link kinds and are not touched | counted by this variant; checked on decoys against the reference's own split between the primary and the all-reverts outcomes |
| `PU_reachable_universe` | files the history walk cannot touch are removed | — | **0 such files in every repo** (`docs/sa3_prescoring_counts.md`): equals the frozen run; not scored |
| `PU_unreachable_made_reachable` | those files can be positive | — | **0 such files**: equals the frozen run; not scored |
| `PU_new_completeness` | repos under 90% measured against the tree are dropped | — | **the same six repos as the registered measure**: equals the frozen run; not scored |
| `PU_nesting_floor` | repos with nesting coverage under 95% lose their nesting cells | — | **coverage is 100% wherever a nesting file exists**; repos without one already have silent nesting cells: equals the frozen run; not scored |
| `PU_window_assertion` | repos whose window ends before it starts are dropped | — | **no repo**: equals the frozen run; not scored |
| `PU_generic_dirs_restored` | first-party files under `cache/`, `dist/`, `extern/`, `env/` are ranked again | — | **not run.** The universe could be changed (a `.gitattributes` line in a copy of the scan sidecar), but the stored history records no touch for those paths, so they could never be positive; their labels would need a new extraction from the clones. Size: 65 scanned files across seven repos scored on the primary outcome |
| S8 | rename following | — | **not run**, as Amendment 4 reported; building it is a new rule, not a variant |

**On "every one is run".** Amendment 5 section 6 says every sensitivity is run and reported whatever it shows.
Five are reported as equal to the frozen run from counts published before scoring, and two as not run, with the
reasons above. That is a deviation from the sentence's letter, stated here and in the result's deviation table.

## 5. Tests, on the decoy studies of part 1

1. Section 2.4, all of it.
2. Section 3's tests.
3. **The two harvest variants**, each on a decoy edited so that it should change something — a lower-case
   tracker key in a qualifying commit; a late revert carrying a ticket; and, as controls, an early revert
   carrying a ticket, an unresolved revert carrying one, and a commit that only quotes a `Revert "` line — with
   the commits that should leave or stay **written into the test beforehand**. The rebuilt outcome file must
   differ from the frozen one in exactly those commits. On an unedited decoy, the rebuilt file equals the
   frozen one.
4. The harvest copy differs from the original only in the deleted rows and keeps its `meta` rows; the reference
   outcome builder reproduces the stored outcome file from an **unmodified** copy.
5. Commit order: a rebuilt outcome file with one commit removed keeps the frozen order for every other commit,
   and the variant's matched control, on named streams, changes only in the repo concerned.
6. No variant's output contains "supported", "contradicted" or a Holm level.
7. Every test passes alone, in reverse order, and with every existing test file in one process.

## 6. Deliverables

```
tools/compare/reading.py          section 2.1 (the first build)
tools/compare/streams.py          section 3
tools/compare/variants.py         section 4
tools/compare/harvest_variant.py  the two harvest copies, the late-revert resolution, the outcome builder runs
docs/process/reading_rule_table.md   generated, section 2.4
tests/test_compare_part2.py
```

and the one hook in `tools/compare/scorer.py`. `tools/compare/reading_b.py` is written afterwards by the second
builder.

## 7. Rules for the builder

As part 1: decoys only; none of the forbidden paths; every call into SA3 code in a sandbox; no edit to a sealed
file, to `tools/owner/`, `tools/harness/`, `tools/control_repo/`, `tools/blind/` or `tools/tables/`; modules
loaded by path under unique names. Report: what was built; test results in all three modes; the generated
table's row count and its differing rows; each variant's changed cells on each decoy; anything here that is
wrong, ambiguous, unsafe or impossible.
