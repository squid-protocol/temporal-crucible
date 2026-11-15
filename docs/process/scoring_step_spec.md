# The scoring step — specification (DRAFT; depends on part 2 of the comparison scorer)

**Status: draft, 2026-11-15. Nothing built, nothing run.** It is Amendment 5's step (g): the owner runs `lock`,
then `score`, once — with the comparison scorer, the corrected readings and the sensitivities beside it. It is
written now because most of it does not depend on part 2; the parts that do are marked. It goes to an
independent review once part 2's specification is settled.

## 1. Before the owner's run: three things, in this order

1. **The last documents are entered** by a session and committed: the second erratum (accepted 2026-11-15)
   into `docs/sa3_registration.md`; the consolidated text updated to match. Nothing else in a sealed document
   changes. After this commit, **no sealed file may change until the result is written.**
2. **The owner re-runs the preparation job** (`tools/owner/prepare.py --real --i-am-the-owner`, a new protected
   directory `run-2`). It re-takes the seal over the new registration, re-checks the reference code, and
   reproduces the placebo again. It must print `PASS`. (It takes about seven minutes.)
3. **The scoring job's own code is pinned.** The preparation job's seal covers the reference code, the sealed
   documents and its own code, by a list fixed in sealed code; it cannot be extended. So the scoring job pins
   its code another way: it refuses to run unless the checkout is clean at a named commit, and its report
   records that commit and the SHA-256 of every file under `tools/compare/` and `tools/scoring/`. Those files
   are reviewed before the commit is named.

## 2. The owner's run — one command

```
python3 tools/scoring/score_sa3.py --real --i-am-the-owner \
    --seal <run-2's public directory>/seal.json --protected /srv/…/temporal-crucible-protected/score-1 \
    --out <a new public directory>
```

It prints what it will do and waits for Enter, as the preparation job does. Then, in order, stopping at the
first failure with a reason code:

| step | what | why |
|---|---|---|
| 1 | The checkout is clean; its commit is the named one; `seal.py verify` against run-2's seal passes | the code and inputs are the sealed ones |
| 2 | **A fresh full clone** of the repository at that commit is made inside the protected directory | `lock` needs a real git repository: in this checkout (a linked worktree) git fails inside a sandbox and `lock` writes empty hashes, and then `score` proceeds anyway (`tools/owner/README.md`, "For the scoring step") |
| 3 | The clone's sealed files are checked against the seal | the clone is the sealed tree |
| 4 | In the read-only sandbox, with SA3's real inputs bound read-only and only the clone's `docs/` writable: the reference `python3 tools/sa3_score.py lock`, unchanged | Amendment 5 section 2, item 3 |
| 5 | `seal.py verify --after-lock` on the clone's lock file | the lock holds the nine hashes the seal expects |
| 6 | The same sandbox: the reference `python3 tools/sa3_score.py score`, **once**, unchanged | **this is SA3's confirmatory result** |
| 7 | The label tables are built from the outcome files; the input check's label side runs | comparison scorer, part 1, section 3 |
| 8 | The comparison scorer (part 1) scores from the tables; the cell map compares its result with step 6's, key by key | layer 3 |
| 9 | *(part 2)* The corrected readings; the named-streams variant; the ten sensitivities | Amendment 5 sections 4 and 6 |
| 10 | The report is written | below |

A second run **refuses** a protected directory that is not empty. Nothing is resumed or repeated.

**If step 8 finds a difference,** the confirmatory result is still step 6's, as Amendment 5 says. The report
states the check failed, how many cells of each class differ, and the first R cell by position. It is
investigated afterwards on a decoy, never by re-running on the real data. Whether a failed check changes how
the result may be described is the owner's ruling, made after the report.

## 3. What is published

The result is no longer blind: publishing it is the point of the step. Even so the report is assembled by a
validator, so that nothing beyond the declared outputs leaves the protected directory.

- `sa3_result.json`: the reference's result file, byte for byte as step 6 wrote it.
- `report.md`, first lines: for SA3-B, SA3-C, SA3-D the reading **as coded** and **as corrected**, and "same" or
  "reading depends on a rule corrected after the estimates were partly seen"; SA3-A's exploratory reading; the
  placebo gate's verdict; the check's verdict (cell map all-equal or not).
- The label of Amendment 5 section 8 above every number.
- The cell map's counts per class; the input check's verdicts per item.
- *(part 2)* Each sensitivity's summaries under its name, every one of them, in the neutral vocabulary; beside
  each confirmatory cell, the difference from step 6.
- The deviation table of Amendment 5 section 8: every difference between the registration and the reference
  code, and between the reference code and each correction, with when, who decided it, and whether it can move
  a confirmatory number.
- The provenance: the commit, run-2's seal hash, the lock file, the SHA-256 of every file of the scoring job.

**Not published:** the label tables, per-file values joined to outcomes, lists of positive files. The protected
directory keeps them.

## 4. Before the owner runs it

The job is built and tested on decoy studies (part 1's N and P) in decoy mode, exactly as the real run will go:
a fresh clone, `lock` in it, `verify --after-lock`, `score`, the comparison, the cell map all-equal, the report.
Plus: a test in which `lock` is made to run where git fails, and the job stops at step 5; a run on a decoy
where one sealed file is changed after run-2's seal, and the job stops at step 1; the planted-marker test of
the owner job; every test alone, in reverse order and with every other test file.

Then an independent review of the build, and the owner is given the command, what it prints, and what each
stopping code means.

## 5. Open, to settle in review

- Whether the report's first lines should also give the three confirmatory means and intervals, or only the
  reading words. (They are in `sa3_result.json` either way.)
- Whether to publish the per-repo values in `sa3_result.json` as they are. They are declared outputs of the
  registered scorer; this draft says yes.
