# Stored tables, phase B — SA3's real data, public counts only (specification)

**Status: specification, 2026-11-14. Nothing built, nothing run.** Step 3, phase B, of
`research_codebase_spec.md`. **This is the first step that reads SA3's real study data.** It needs an
independent review of this document, and the owner's go-ahead, before the job is run.

**Purpose.** Build the stored tables of `tables_spec.md` from SA3's existing scans, histories, harvests and
outcome files, and publish the counts that Amendment 5 section 7 promises before scoring. No predictor is ever
set against an outcome.

## What may leave the job

Only these, written to one new output directory:

1. The **public tables** per repo: `repo`, `snapshot`, `file`, `measure`, `touch`, `marginal`, and `index.json`.
2. The **protected tables** per repo (`link`, `event`, `pool`), in a `protected/` subdirectory with mode 700.
   They hold what the existing outcome files already hold in plain text; nothing new is revealed. No session
   opens them. Only their hashes are read afterwards.
3. The **data card** per repo and one **study card**, holding the counts below and nothing else.

**Nothing in a data card or the study card is computed from a predictor and an outcome together.** A test
enforces it: the card builder is given the public tables, the marginals, and from the protected tables only
row counts and hashes.

## The counts (Amendment 5, section 7), per repo unless said

| # | count | from |
|---|---|---|
| 1 | The cells whose silence changed in `8fb7fe0`: for every (repo, outcome, measure) the scorer would score, whether the measure is silent under the rule as at `edc5c53` and as at `8fb7fe0`; the cells where the two differ, marking the confirmatory ones | `measure` only. The two versions of the rule are read from the two commits' `silent()` and **called**, each in its own process, not rewritten |
| 2 | For the 15 drawn repos: window start, cut, whether they are equal | `snapshot` |
| 3 | Window start, window end, usable commits | `snapshot`, `repo` |
| 4 | Completeness on the registered measure, and against the tree with reasons | `file` |
| 5 | Files excluded by each of the four patterns of `PU_generic_dirs_restored`, and how many have scan rows | `file` |
| 6 | Universe files the history cannot touch, **by cause**: `.gitattributes` re-inclusion; path spelled differently in the archive listing and the history; symbolic link or submodule entry; reachable only off the first-parent chain in a repo walked first-parent | `file`, the history |
| 7 | Qualifying commits that qualify only through a lower-case tracker key: the count of commits whose only fix link is a tracker key that is not all capitals | `link` and the harvested messages. **A count per repo, never a list.** It reads which commits qualify, not which files, and no predictor |
| 8 | The share of universe files with a nesting value | `measure` |
| 9 | The stored `.gitattributes` text: its length, and whether it reaches the 200,000-character cut | the scan sidecar |
| 10 | How each prebuilt input was made: SHA-256 of GitHub's two lists; the history walk's unit rule and C-family flag; the harvest's flags; engine id; hash seed if recorded; grammar pack version | sidecars, database `meta` tables |

Count 7 is the only one that reads the link table. It is included because Amendment 5 promises it and it is a
property of commit messages. If the reviewer of this document judges that it tells a session something about
the outcome that the existing public marginals do not, it moves to the owner-run job.

## How it runs: the real data is read-only by construction

A variant of the harness sandbox (`tools/harness/sandbox.py`), **added as new code, leaving the existing
sandbox and its tests untouched**:

- root read-only; home, `/tmp`, the corpus root and the projects root hidden, as now;
- the real study directory bound **read-only** at its own path;
- the corpus clones the tools must read (for `git ls-tree` and `git archive` of each snapshot) bound
  **read-only**, one repo at a time, with `GIT_NO_LAZY_FETCH=1`, `gc.auto=0`, and no command that writes to a
  repository. A partial clone that cannot serve a tree without fetching is recorded as "tree unavailable: a
  fetch would be needed" and its `file` table is built from the scan and the archive listing the scan sidecar
  already holds;
- the engine export read-only; it is not run. **No scan is made in phase B**;
- one new output directory, outside the study directory, bound read-write;
- the network unshared.

The existing tools write as they go: the outcome builder rewrites the harvest database, and `universe()` runs
`git archive`. **Phase B never calls the outcome builder.** It calls `universe()`, `frame()` and the
Excluder, which only read; the read-only bind turns any write this specification failed to foresee into an
error instead of a change.

**Sandbox tests, run first, on a decoy** (a temporary directory standing in for the study directory, with a
control repository's outputs in it): a write to the study path fails; a write to a clone fails; `git gc` and a
fetch fail; the output directory is the only writable place; a deliberately misbehaving stage that tries each
of those leaves the decoy's file hashes and modification times unchanged.

## Before the real run

1. **Rehearsal on control repositories:** the phase B job, unchanged, is pointed at a decoy study directory
   built by the harness from 10 control repositories (the base pair and the mutations). Its tables must equal
   the phase A tables for the same repositories, hash for hash, and its counts must equal the values known
   from the manifests: count 5 under `generic_dir_names`; count 6 is zero in the base repository and equals
   the planted number in a repository given a `.gitattributes` line that switches vendoring off (a small
   addition to the generator, specified with the rehearsal); count 7 on commits planted with lower-case keys.
2. **The four items the second design review asked for before phase B** (`research_codebase_spec.md` section
   12): count 6 by cause and count 10 are in the table above; the missing-value rule of each derived predictor
   is written beside its formula in `tools/tables/schema.py` and tested, band recomputation included, **but
   derived predictors are still not stored in phase B**; the false-failure rate of each control-suite bound is
   simulated and written into `research_codebase_spec.md` section 7.
3. **Hashes before and after:** the job records the SHA-256 and modification time of every file it is allowed
   to read under the study directory before it starts and after it ends, from inside the sandbox, and stops
   with an error if any differs. The list of hashes is part of the output.
4. The owner says go.

## The run, and after it

- One repo at a time, in the frozen list's order; a repo that fails an invariant gets `build_failed.json` and
  the run continues.
- Afterwards a session reads only: the study card, the data cards, `index.json` files, and the public tables.
- **A failed invariant on real data is not investigated on real data.** It is reproduced on a control
  repository, or reported to the owner with the invariant's name and the row count.

## Deliverables

```
tools/tables/phase_b.py        the job: python tools/tables/phase_b.py --out DIR [--decoy DIR]
tools/tables/study_card.py     the ten counts
tools/harness/sandbox_ro.py    the read-only variant (new file; sandbox.py is not edited)
tests/test_tables_phase_b.py   sandbox tests on a decoy; the rehearsal; the "no predictor with outcome" test
```

## Rules for the builder

- **The builder never runs the job on the real study directory.** It builds and tests on decoys only. The
  real run is started by the reviewer's session after the review, the rehearsal and the owner's go-ahead, and
  only through `sandbox_ro.py`.
- Until then: never open, list or stat the real study directory, the corpus or `~/.blind`, by any route.
- Write only the four deliverables. No commits. No edit to any SA3 tool, to `tools/harness/sandbox.py`, or to
  the phase A modules beyond adding the derived-predictor rules to `schema.py` and counts to the data card.
- Report: what was built; the sandbox test results; the rehearsal's table-hash comparison and each count
  against its known value; anything in this document that is wrong, ambiguous, unsafe or impossible.
