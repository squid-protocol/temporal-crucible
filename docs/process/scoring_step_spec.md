# The scoring step — specification

**Status: Revision 2, 2026-11-15, after an independent review and two owner rulings. Nothing built, nothing
run.** It is Amendment 5's step (g): the owner runs `lock`, then `score`, once — with the comparison scorer,
the corrected readings and the sensitivities beside it.

**What Revision 2 changed** (`reviews/scoring_step_spec_review.md`: 2 blockers, 11 major, 9 minor; the
fresh-clone design itself was tested and found sound):

- **The job is split at the score.** Everything before it stops on failure with nothing scored; the result is
  published the moment it exists; nothing after it can strand it.
- **"Once" is defined, enforced and recorded** by a ledger (owner ruling 2 below).
- **How a failed check is described is fixed now**, before the result is seen (owner ruling 1).
- The pin is a commit given to the owner out of band and pushed with a tag; the reading note is entered with
  the second erratum; the scan databases are read through checked copies; the loader is rehearsed on all 40
  repos before scoring; the predictor-side check on real data is scheduled; the bind layout and the run time
  are written down.

## 1. Owner rulings, 2026-11-15

1. **The failure table of section 6 is accepted as written**, before any build or result.
2. **"Once" is defined as in section 5.**

## 2. The order, with the commit at each step

| # | who | what | commit |
|---|---|---|---|
| 1 | session | build `tools/scoring/` on decoys; independent review of the build; fix; accept | build commit |
| 2 | session | **the predictor-side check on real data** (comparison scorer part 1, section 3; session-run, no label bound): build `call_degree` and `flux` from the real scans, run the reference loader with stub outcomes against the table route. Public verdicts and table hashes committed. A "not equal" stops the route here, and is investigated freely: no label is involved | verdict commit |
| 3 | session | enter the **second erratum** and the **reading note** into `docs/sa3_registration.md`; update the consolidated text; write the **deviation table** (section 7) and commit it. This is **commit C**. Annotated tag `sa3-score-C`; push the branch and the tag | **C** |
| 4 | session | give the owner, in the hand-over message: C's full hash, the tag, the tree hash of `tools/` at C (`git rev-parse C:tools`) that the build review read, the command, and the run-time estimate | — |
| 5 | owner | the preparation job again, at C, into `run-2`. It must print `PASS` | — |
| 6 | session | compare run-2's seal with run-1's: exactly the entries for the two changed documents and the run's own times may differ; anything else stops the route | — |
| 7 | owner | the scoring job, at C (section 3) | — |
| 8 | session | one commit of the public outputs | result commit |

**Nothing is committed, and nothing on the machine is updated, between step 5 and step 7.**

## 3. The scoring job

```
tmux new -s sa3
cd /srv/storage_16tb/projects/temporal-crucible-wt-seat
python3 tools/scoring/score_sa3.py --real --i-am-the-owner --commit <C, 40 hex> \
    --seal <run-2's public directory>/seal.json \
    --protected /srv/storage_16tb/projects/temporal-crucible-protected/score-1 --out ~/sa3-score-1
```

It prints its plan and waits for Enter. The launcher runs on the host from the checkout; **every stage runs
from code taken from a fresh clone at C**, inside the read-only sandbox.

### Before the score — any failure stops the job; nothing has been scored; the ledger has no entry

| step | what |
|---|---|
| 1 | The ledger (section 5) has no entry. `git rev-parse HEAD` equals `--commit`; `git status --porcelain --ignored` shows nothing but the known ignored `__pycache__`; the tag points at C. `seal.py verify` against run-2's seal passes |
| 2 | A fresh clone: `git clone --no-hardlinks --no-checkout` of the main repository, then `checkout --detach C`, inside the protected directory. `.git` is a directory; HEAD is C; status is clean |
| 3 | Every sealed file in the clone has the seal's SHA-256 |
| 4 | The inputs are copied by the owner job's `copy` stage (each original hashed first and compared with the seal; each database copy checkpointed and set to rollback mode). Every input `score` reads — for **all** repos with status `ok`: history copy, scan copy, sidecar, nesting file, outcome file, the clone of the repo, GitHub's two lists — must match the seal |
| 5 | The predictor-side tables of step 2 of section 2 match their committed hashes |
| 6 | **The loader rehearsal:** the reference `load(repo, True)`, unchanged, for every `ok` repo, with its real outcome file bound. It scores nothing. Only ok or a code leaves, per repo; the arrays stay in the protected directory |
| 7 | The reference `lock`, unchanged, in the sandbox, with the clone's `docs/` the only writable directory and the clone's `.git` and `tools/` bound read-only as inputs |
| 8 | `seal.py verify --after-lock` on the clone's lock file (its own empty verify directory). Then, on the host, `git -C <clone> status --porcelain` shows exactly `docs/sa3_lock.json` |

### The score — once

| step | what |
|---|---|
| 9 | The ledger entry `started` is written and flushed: time, C, run-2's seal SHA-256. **The reference `score`, unchanged, once**, in the same sandbox, with a time-out of one day. **This is SA3's confirmatory result.** |
| 10 | The ledger entry `completed`: the result's SHA-256. The result is checked by shape, **published byte for byte** to the public directory, and a **receipt** line printed for the owner to keep off the machine: the result's SHA-256, C, the seal's SHA-256 |

### After the score — no step can stop the report

| step | what |
|---|---|
| 11 | Label tables built in a sandbox stage with the outcome files bound read-only; the input check's label side (comparison part 1, section 3) |
| 12 | The comparison scorer (part 1) on the tables, reading its sealed copies from the clone; the cell map against the published result |
| 13 | Part 2: the corrected readings; `PU_named_streams`; the two harvest variants. Steps 12 and 13 may run side by side |
| 14 | The report (section 4) — always written. Each of steps 11 to 13 ends as done or as `failed` with a code |

**Resume.** `score_sa3.py --resume` re-runs steps 11 to 14 from the published result. It checks the result's
SHA-256 against the receipt and **cannot start the reference `score`**. Each resume is recorded in the ledger.
If code changed since the first attempt, the parts it produced are labelled "run later, on <date>".

**The real-data doors of `tools/compare/`.** Its command lines refuse real paths. `tools/scoring/` holds the
real-mode stage launchers and calls `tools/compare/` functions as a library inside sandbox stages. If a
`tools/compare/` function itself must change, the change lands in step 1 of section 2, parts 1 and 2 pass
again in all three test modes, both decoy cell maps stay all-equal, and the build review covers the diff.

## 4. What is published

Through a validator of fixed shapes, as for the owner job:

- `sa3_result.json`: the reference's result, byte for byte (step 10).
- `report.md`. **First lines:** the label of Amendment 5 section 8; then, for SA3-B, SA3-C, SA3-D, the mean
  and its interval at the Holm level, the reading **as coded** and **as corrected**, and "same" or "reading
  depends on a rule corrected after the estimates were partly seen"; SA3-A's exploratory reading; the placebo
  gate's verdict (it is the sealed placebo file's, fixed since 2026-11-14); the check's verdict; any sentence
  of section 6 that applies; every attempt and resume.
- The cell map's counts per class; the input check's verdicts per item.
- Part 2: each variant as specified there, in its order, whatever it shows; the five reported equal from the
  pre-scoring counts and the two not run, with their reasons.
- The deviation table (section 7), with its last column filled from this run.
- Provenance: C, the tag, run-2's seal SHA-256, the lock file, the receipt, the ledger, the SHA-256 of every
  loaded module of every stage.

Not published: the label tables, per-file values joined to outcomes, lists of positive files.

## 5. "Once" (owner ruling 2)

- **"Once" means the reference `score` process is started at most once on the real inputs.**
- The ledger is a file at a fixed path outside any run directory
  (`/srv/storage_16tb/projects/temporal-crucible-protected/sa3_score_ledger.jsonl`), appended and flushed by
  the launcher on the host; a copy goes to the public directory.
- If the ledger has **any** entry, the job refuses, whatever directory is named — except `--resume`.
- A failure in steps 1 to 8 writes no entry; a new attempt is still the first scoring, and every attempt is
  listed in the report.
- A `started` with no `completed` (a crash, a time-out, a power cut): the reference prints no estimate before it
  has written its file, so nothing was seen. A second start needs `--rerun REASON`, which is recorded and
  printed in the report's first lines.
- After a `completed`: no second start, ever. Only `--resume`.

## 6. If a check fails (owner ruling 1)

The reference result always stands (Amendment 5 sections 2 and 9). Fixed now:

| event | when | what happens |
|---|---|---|
| run-2's placebo is not `bytes_equal` | before scoring | the route stops; nothing scored |
| steps 1 to 8 fail | before scoring | the job stops; nothing scored |
| the loader rehearsal fails | before scoring | the job stops; nothing scored |
| the placebo gate | fixed | it is the `valid` field of the sealed placebo file and cannot newly fail; the report prints it |
| the label-side input check reads "not equal" or "not comparable" | after scoring | the result stands; the report says "the inputs the two routes read were not shown equal"; the cell map is still printed |
| the cell map: R cells differ, W and D all equal | after scoring | the result stands; the report names the R class; "defect-specific" against "tracks activity" is marked unverified |
| the cell map: any W or D cell differs | after scoring | the result stands as the registered output; the label gains "the check did not confirm this run"; **no hypothesis is called confirmatory** until a decoy investigation, written up and dated, places the cause |
| a corrected reading or a variant fails to run | after scoring | reported "failed: code"; a later run is dated and labelled later; it never blocks the report |

These sentences are constants in `tools/scoring/`, reviewed before C.

## 7. The deviation table

Written in step 3 of section 2, committed in C, every row known today: each difference between the
registration and the reference code, and between the reference code and each correction — what, when, who
decided it, and whether it can move a confirmatory number. Sources: Amendments 4 and 5, the two errata, the
reading note, the defect log entries 42 to 64, the five sensitivities reported from counts and the two not run.
Only its last column — whether the reading differs in this run — comes from the job.

## 8. Run time

Not measured. The review's estimate from the public run log of run-1 and a count of evaluations: one scoring
loop 25 to 75 minutes; the job runs three to five loops (the reference, the comparison, named streams, the two
harvest variants) plus about 15 minutes of checks — **one to six hours**. The build times one loop on a decoy
study and scales it; the hand-over gives the measured estimate. The owner runs the job inside `tmux`, because
the sandbox dies with its terminal.

## 9. Before the owner runs it — tests on decoy studies

- The whole job in decoy mode, exactly as section 3 runs it, on parts 1's studies N and P: fresh clone, lock,
  verify, score, comparison, report; the cell map all-equal.
- Split and resume: each of steps 11, 12 and 13 made to fail in turn; each time the published result equals
  the clone's byte for byte, the report exists and names the failure, `--resume` completes it, and the ledger
  shows one start.
- Once: a second run after a completed one refuses with a different directory; a run killed during the score
  leaves `started`; `--rerun` records its reason; a failure at step 3 leaves no entry.
- The pin: a wrong `--commit` refuses; an untracked file under `tools/` refuses; each stage's loaded modules
  equal `git ls-tree` of the clone.
- `lock` where git fails stops at step 8; a sealed file changed after run-2's seal stops at step 1; a scan
  database changed between the seal and the copy stops at step 4; an outcome path outside the universe stops
  the loader rehearsal with no ledger entry.
- Each sentence of section 6, on the blind test's faulty copies: each kind of failure prints its sentence and no
  other.
- Planted markers in a decoy's outcome files appear in no public output.
- Every test alone, in reverse order, and with every other test file.

Then an independent review of the build. The owner gets the command, what it prints, the run-time estimate, and
what each stopping code means.

## 10. Rules for the builder

Decoys only; never `--real`; none of the forbidden paths; every call into SA3 code in a sandbox; no edit to a
sealed file, to `tools/owner/`, `tools/harness/`, `tools/tables/`, `tools/control_repo/` or `tools/blind/`;
`tools/compare/` only as section 3 allows; modules loaded by path under unique names. Report: what was built;
test results in all three modes; the timed decoy loop and the scaled estimate; anything here that is wrong,
ambiguous, unsafe or impossible.
