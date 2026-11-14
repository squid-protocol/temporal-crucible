# Control repository, phase 1 — review

**Reviewer:** Claude Fable 5.2, 2026-11-14. **Built by:** Claude Opus, from `docs/process/control_repo_spec.md`
alone (a first builder session was interrupted; a second finished from its four partial files).
**Reviewed:** `tools/control_repo/` (generate, codegen, history, mutations, manifest, README, DECISIONS) and
`tests/test_control_repo.py`, uncommitted in the working tree at `c60336e`.

**Verdict: accept with changes.** The generator's core is sound: hashes are deterministic, every planted count
equals the file text, the negative control is null in the truth, planted effects are recovered, and the twelve
mutations leave the planted truth alone. Four findings concern the **expected labels and one mutation**; they
should be fixed before phase 2 scores a pipeline against this manifest. One finding is a fault in **SA3's own
consolidated text**, which the control repository exposed.

Every finding below was reproduced by running something. Nothing was taken from the builder's report. The
reviewer's checks share no code with the build: `check_counts.py`, `check_git.py`, `check_null.py` (kept in the
session's scratch directory; the method of each is stated here so it can be rewritten).

## What was checked, and the result

| check | how | result |
|---|---|---|
| The builder's tests | re-run of `python3 -m pytest tests/test_control_repo.py` | 37 passed, 0 skipped, 100 s |
| Tests are honest | read the file; no `xfail`; two conditional skips (no C compiler, no tree-sitter), neither fired | pass, with one deviation (finding 6) |
| Determinism | regenerated seed 11 from another directory with a different `TZ`, locale, `PYTHONHASHSEED` and an inherited `GIT_AUTHOR_NAME` | manifest byte-identical, same HEAD hash |
| Repository validity | `git fsck --strict`; every commit's paths, parents, author, time and message read from git and compared with the manifest, baseline and all 12 mutations and one five-way composition | 0 mismatches in 13 baseline-or-mutated repos (3,000 to 4,407 commits each) |
| Planted counts = text, Python | my own `ast` reader for lines, branches, nesting (else-if flat), cross-file calls out and in, state writes inside an `if`; every code file at the snapshot **and** the prior point | 771 file-points, 0 mismatches; calls-in 611 unit file-points, 0 mismatches |
| Planted counts = text, C | regex readers for lines, branch keywords, calls, allocation calls; `gcc -std=c11 -fsyntax-only -Wall` on 150 files | 771 file-points, 0 mismatches; 0 files fail to compile |
| `sa3_nesting.py` agrees | the tool itself (pack 1.20.0) on every code file, both languages, both points | 0 mismatches, 0 parse errors |
| Negative control is null | fresh seeds (Python 100–159, C 300–339), default profile, my own statistic: Spearman of density against true fix count inside size deciles | Python: every property within 1.4 standard errors of zero, largest −0.010. C: see finding 5 |
| Nothing leaks through busyness | Spearman of each density against the latent busyness, same seeds | none beyond 3 standard errors |
| Positive controls | `branches=0.5`, `d_branches=0.5` (Python), `pointer_ops=0.5` (C), 12–20 fresh seeds | +0.228, +0.194, +0.213; other properties stay near zero |
| Mutations change only what they say | each mutation's manifest against the baseline's: planted properties at both points, busyness, true fixes, fix weights | unchanged for every pre-existing file in all 12 |
| Mutations do what they say, in git | merge counts, bot authorship of merges, squash commit counts, a 500-commit merge, 40% other-language share, 295 imported files, 61 rename commits, no references left on fixes | all as stated, except finding 3 |
| Expected labels | an independent reading of the message text from git (ticket, Jira key, `Fixes:`, CVE, revert whose target is an ancestor of the snapshot, tree-wide rule) for every non-merge commit after the snapshot | agree except findings 1 and 2 |
| Rules for the builder | `git status`: only `tools/control_repo/` and the test file are new; nothing committed; `--out` inside the repository is refused | pass |

A reviewer's error, for the record: my first C reader counted the declaration `long *cursor = data;` as a
pointer write and reported 604 mismatches. The manifest counts dereference writes only and is right (finding 8).

## Findings

Severity: **medium** = a pipeline scored against this manifest would be marked wrongly. **low** = worth fixing.
**note** = phase 2 must know it.

### 1. Expected positive files are not confined to the snapshot's unit files — medium

`manifest.expected_labels` gives `positive_unit_files` as paths **at the time of the commit**, for any unit
file, including files created after the snapshot. SA3 ranks only the snapshot's unit files and identifies them
by their snapshot path.

- Baseline, seed 11: 2 positive paths are not unit paths at the snapshot.
- `renames_after_snapshot`: 7. `squash_merges`: 14. `tickets_for_everything`: 18.

A pipeline that follows renames correctly would be marked wrong, and one that drops them would be marked right
— the opposite of what the mutation is for (defect log 39). The tree-wide test in the labels has the same
flaw: it counts every unit file a commit touches, against a denominator of snapshot units.

**Change:** give positives as file ids with their snapshot path; list separately the touched unit files that
are not in the snapshot's set; apply the tree-wide rule to snapshot units only.

### 2. A revert of new code that quotes a ticket is counted, not listed as ambiguous — medium

A revert's message quotes its target's subject. When the target is a ticket feature, the revert carries
"Fixed #N" in its own subject. The manifest counts such a revert under HP through that reference even when its
target was written after the snapshot — the case log entry 16 is about.

- Baseline: 1 such commit. `tickets_for_everything`: 4. `squash_merges`: 3.
- Under `reverts_of_new_code` one revert is still counted this way, which contradicts that mutation's own truth
  sentence ("reverts after the snapshot target post-snapshot commits, which HP does not count").

The written rule can be read either way (it carries a fix reference; it is a revert that does not qualify).
The spec says not to decide such cases. **Change:** list them under `ambiguous` with both readings.

### 3. In Python, a rename rewrites every caller; `renames_after_snapshot` edits half the repository — medium

Python files import each other by path, so a rename commit also rewrites the import line of every file that
calls the renamed one (`history.Simulator._move`). Measured on 20 seeds:

- with `renames_after_snapshot`, **53%** of unit files are touched by a rename commit after the snapshot (the
  mutation says 20% are renamed);
- non-fix activity after the snapshot becomes related to **calls-out density: +0.143** inside size deciles
  (standard error 0.013). Without the mutation there is no detectable relation.

So the mutation plants a structure-to-activity association that its description and its `truth` sentence do
not mention, and it would move SA3's matched control for a call-graph measure. The builder's test 7 passes
because it compares planted properties and fix counts, not which files other commits touch. C is unaffected.

**Change:** the inserted post-snapshot renames should not rewrite callers (snapshot truth is measured before
them, so nothing planted depends on it); say in the manifest that imports of a moved file go stale. For the 24
ordinary renames and 18 deletes of the base history, keep the behaviour and record in each commit which files
were edited only as callers.

### 4. Merge labels: one reading is missing, and it is the one SA3's code implements — medium

The builder is right that section 4 of `docs/sa3_registration_consolidated.md` contradicts itself: a merge
"inherits the fix reference … of a commit it brings in", and a merge "bringing in a linked or fix-worded
commit" is tainted and "in no outcome". The builder listed every inheriting merge as ambiguous (83 in the
default repository), with three readings.

`tools/sa3_outcomes.py` (lines 221–310) does something none of the three says: a merge that brings in a linked
commit **is counted as a positive** when it shares a file with that commit, **and** is put in the tainted set;
the tainted set is then used only to keep merges out of the keyword outcome and the control pool.

- Add this as a fourth reading, "taint governs the control pool only".
- 6 merges in the default repository bring in both a linked commit and a fix-worded one. The manifest marks
  them not counted under every reading; under the code's reading they are counted. They belong under
  `ambiguous`.
- Until the text is settled, `merge_workflow` and `bot_merges` have **no decided positive label at all**
  (`counted: true` on 0 of 285 first-parent commits after the snapshot).

This is also a fault in SA3 itself: see "For the defect log".

### 5. Density is related to size inside size bands — low, and a note for phase 2

Counts are whole numbers, so `count / loc` is mechanically related to `loc`. Inside size deciles, density
against size reads −0.04 to −0.10 in Python and −0.07 to −0.12 in C (all beyond 3 standard errors;
`max_nesting` reads +0.04 to +0.07 because it is a depth, not a rate).

Fix probability rises with size, so a band-based statistic inherits a little of this. In Python nothing is
visible (largest −0.010 over 60 seeds). In C two properties read **−0.024** (branches) and **−0.020**
(calls-in), each about 2.3 standard errors from zero over 40 seeds: suggestive, not established.

The generating formula is null; a real instrument measuring these files will see a small size relation that is
not an effect. **For phase 2:** score a pipeline against the manifest's truth pushed through the same
statistic, not against exactly zero.

### 6. Test 5 does not run at `--profile small`, and has a built-in false-failure rate — low (spec)

The spec asks for the null test at `--profile small` with a tolerance of ±0.03. The builder showed this cannot
be resolved at 60 files (standard error of a 20-seed mean about 0.05) and ran it at `--files 800`. I agree
with the change and with reporting it. The tolerance is still only 2.4 to 5 standard errors wide across 14
property checks, so a correct generator fails some fixed seed set about one time in twenty by the builder's own
estimate. **Change the spec:** state the file count, and test each mean against three of its own standard
errors with a ceiling of 0.03.

### 7. The change effect rests on few files — low

Only **11.8%** of unit files (Python) and **9.9%** (C) change their branch density in the year before the
snapshot, and whether a file changed at all is related to busyness (+0.057). The planted change effect is
recovered (+0.194), but a study of change would be working with about 35 files per repository. The spec gave
no number. **Change the spec:** at least 40% of unit files change in that year.

### 8. Notes for phase 2

- **The outcome window is short.** `--years 4` leaves about 270 days after the snapshot; SA3's window is 730.
  A sensitivity cut removes such repositories. Phase 2 should generate with a span long enough for a full
  window, or the spec should add a way to set it.
- **`--profile small` is below SA3's floors** (40 unit files, 12 fixes): usable for tests of the generator,
  not for running the pipeline.
- **The snapshot is not where SA3 would put it.** The manifest's snapshot is commit `ceil(0.8n) − 1` of all
  commits; SA3 takes `int(0.8n)` of the non-bot commits and then the nearest scanned snapshot. Either pass the
  snapshot to the pipeline or treat the pipeline's own choice as one of the things being tested — and say
  which.
- **Pointer operations.** The manifest counts dereference writes (`*cursor = …`). Each C function also
  declares `long *cursor = data;` (500 declarations in one repository), which a keyword-family instrument will
  count. The manifest should give both counts or the stated mapping.
- **Imported code never changes.** The files added by `vendored_half` and `mixed_language` receive no commits
  after the initial import, so in a pipeline that ranks them they are all negatives.

## The builder's objections to the spec

| objection | reviewer |
|---|---|
| Test 5 cannot be met at `--profile small` | Agree (finding 6) |
| Section 4 contradicts itself on merges | Agree, and the code settles what was meant (finding 4) |
| `reverts_of_new_code` cannot apply to every revert | Agree; the spec's "every revert" should read "every revert in the outcome window, where a post-snapshot target exists" |
| The change effect is thin | Agree (finding 7) |

## For the defect log

**New entry (SA3, spec vs code).** The consolidated text says tainted merges are "in no outcome and no
control". The code counts a merge that inherits a fix reference as a positive and uses the tainted set only
for the keyword outcome and the control pool. The text was written after three reviews. Found by: the control
repository's builder (the contradiction) and its reviewer (what the code does). Earliest catch: a generated
repository with merges and a known answer — which is what found it.

## What this review did not do

- It did not run the engine or any SA3 tool on a generated repository; that is phase 2.
- It did not check the engine's branch-keyword mapping, only that the manifest states one.
- It read `codegen.py` for structure but verified it by counting its output, not line by line.
- Hash stability across Python versions or C libraries was not tested (the builder's decision 1 says so).

## Re-review after the builder's fixes (same day)

The builder made all nine changes (generator 1.1.0, manifest schema 2) and disputed none. Re-checked with the
same independent scripts on freshly generated repositories; nothing taken from the builder's report.

| check | result |
|---|---|
| Tests | 39 passed, 0 skipped, 144 s |
| Determinism | byte-identical manifest under a different directory, `TZ` and hash seed |
| Planted counts = text, both languages, both points | 0 mismatches (771 file-points each); `sa3_nesting.py` agrees on all |
| Git matches the manifest, baseline and 7 mutations | 0 mismatches; `fsck` clean |
| Finding 1 | 0 expected positives outside the snapshot's unit files in the baseline and in `renames_after_snapshot`, `squash_merges`, `tickets_for_everything`, `reverts_of_new_code`; later files are listed apart |
| Finding 2 | late reverts quoting a ticket are `counted: null` and listed under `ambiguous` with two readings (baseline 1, `tickets_for_everything` 4). In `squash_merges`, two such reverts share a squash commit with another link and are counted through that link — correct |
| Finding 3 | the 61 inserted renames touch 61 of 306 snapshot unit files and nothing else; every commit shared with the baseline touches the same files. Non-fix activity against calls-out density, 16 fresh seeds: +0.031 (standard error 0.010), down from +0.143; the builder's 20 seeds read +0.008. What remains comes from the base history's own renames and deletes, whose caller edits are now marked per commit |
| Finding 4 | four readings; `merge_workflow` has 89 ambiguous merges, 88 of them counted under "taint governs the control pool only" |
| Finding 7 | branch density changes in the prior year for 66% of unit files (Python) and 56% (C), 30 fresh seeds each. Change-effect null: +0.017 in both languages, 1.3 and 1.8 standard errors from zero; the builder's 40 seeds read +0.002 and −0.007 |
| Null on fresh seeds (700–729), all other properties | Python and C: every property within 1.9 standard errors of zero |

**Accepted.** Open for phase 2, unchanged: merge-workflow repositories have no decided positive label until
defect-log entry 54 is ruled on; density is related to size inside size bands, so a pipeline is scored against
the truth pushed through the same statistic.
