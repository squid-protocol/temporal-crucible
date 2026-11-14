# Research codebase specification — design review

**Reviewer:** Claude Fable 5.2, 2026-11-14, independent session. **Reviewed:**
`docs/process/research_codebase_spec.md` (draft of 2026-11-14) against the SA3 code in `tools/`, the SA3
consolidated registration, the defect log, the blinding and control-repository specifications and the first
control-repository review. No study data, scan, label or corpus clone was opened. No study tool was run.
Scratch scripts are in `/home/joe/.claude/jobs/24bf9d40/tmp/arch_review/` (`closure.py`, `lits.py`,
`scramble.py`); each method is stated below so it can be rewritten.

Every finding is marked **[code]** verified in code, **[reasoned]** reasoned, not run, or **[synthetic]** run
on synthetic data.

## Verdict

**Ready after changes. Do not hand it to a builder as written.** Section 1's picture of the code is right:
of 22 claims, 15 are confirmed, 5 are overstated in a count or a word, 2 are wrong in a small way, and none
changes the argument. The direction is right too: stored tables, a generated seal, named random streams and
the control repository on every change would have caught or blunted about half of the logged faults I walked.
But the document has five blockers. It says the spine keeps what SA3's registered code does, and then
specifies at least six things that change SA3's numbers without listing them. Three of its table invariants
will fail on correct real data. The `label` table cannot hold a merge-inherited positive. The scrambled-label
step leaks a large part of the true labels and of the true effect if "directory" means the full directory.
And the first exit test (equality with the old code) cannot be run safely, because the old tools are wired to
the real study directory and delete one of their inputs. All five are fixed by editing the specification, not
by redesign. Separately, the spine is larger than SA3 needs; a smaller version is in finding 16.

Counts: **5 blockers, 9 major, 6 minor.**

## Blockers

### B1. The spine changes SA3's numbers in at least six unlisted ways — [code]

Section 5 says the default is what the registered code does and lists eight disagreements. I compared each
table and rule with the code. These are not on the list:

| # | the spec says | the registered code does | where |
|---|---|---|---|
| a | `touch.unit_path` is the path at the snapshot, **resolved through renames** | matches a later commit to a snapshot file by **equal path only**. Rename following is sensitivity S8, registered and not run | `sa3_outcomes.py:168-171`; `sa3_score.py:358` |
| b | a missing measure is a row with a reason, **never zero** | the D primary reads a missing key, an empty blob or a null as **0**; `in_degree` starts at 0 for every file; the surrogate fit turns missing into 0 | `sa3_score.py:103`, `:125`, `:252` |
| c | one named random stream per study, repo, purpose | registered text: "200 draws, seed 2982". The gate result of 2026-11-14 is sealed and came from the old streams | registration §4, §8; `sa3_score.py:247`, `:361` |
| d | `snapshot` is built by `defs.cut` on `commit` | the snapshot is a **given**: the commit MOD-1 scanned. For the earlier eight it is the scanned commit nearest the cut. The window end is cut + 730 days, the start is max(cut, snapshot time) | `sa3_scan.py:50`; `mod1_lift.py:86-96`; `sa3_outcomes.py:164-169` |
| e | the history's rule is "looser" than the universe | it is **different**, not looser. A `.gitattributes` line that switches vendoring or generation **off** puts a file in the SA3 universe that the history never records a touch for. Such a file is ranked and can never be positive | `laws_units.py:141-142`, `:147`; `laws_history.py:118`, `:151` |
| f | `marginal` is generated from `label` | the list of scored repos is a frozen, registered file. If a regenerated marginal moves a repo across a floor, the confirmatory pool changes | `sa3_score.py:77`; registration §4 |

Item (a) changes the primary outcome. Item (b) changes a confirmatory primary. Item (e) I could not size:
it needs the scans' stored `.gitattributes`, which are study data.

There is also a registration sentence the spec does not mention: "The confirmatory tests run exactly as
frozen at commit `edc5c53`" (consolidated text, line 9). Scoring SA3 through a new spine ends that. It needs
an amendment, written before the build, that says so and lists every item above with its ruling.

**Change.** Add (a)–(f) to section 5 with a default each. My defaults: (a) no rename following, path
equality, S8 stays "not run"; (b) per measure, state "absent means zero" or "absent means missing", copying
the code; (c) new streams, reported as a deviation, gate re-run; (d) snapshot hash is an input taken from the
scan, the cut is computed beside it; (e) owner ruling after a count; (f) the frozen list governs, differences
are reported.

**How to test the change.** Require a three-way table from step A, per rule and per control-repository case:
spine = old code = manifest; spine = old ≠ manifest (an inherited fault, listed); spine = manifest ≠ old (a
deviation, listed, ruled). An empty or missing row fails the step. Seed one rule difference into a copy of
`defs` and check that the table reports it.

### B2. Three stated invariants will fail on correct real data — [code] for the first, [reasoned] for the rest

- **"The snapshot is on the first-parent chain."** In a repo that is not merge-workflow the history is every
  non-merge commit reachable from the head, in commit-time order, and the cut commit is the last of those at
  or before the cut time (`laws_history.py:84`, `mod1_run.py:92-93`). That commit can sit on a side branch.
  The invariant holds only for first-parent repos.
- **"Times on the first-parent chain increase."** Committer times in git are not monotonic: rebases, imports
  and clock skew break it. The existing code knows this: it sorts the walk by commit time, not position
  (`laws_history.py:121`), and every window is a time comparison. I checked only this repository's own
  history (181 first-parent commits, none out of order); I did not open a corpus clone.
- **"`in_universe = 1` implies `loc > 0`", with `file` built from `git ls-tree`.** LOC comes from the scan,
  and the scan reads a `git archive`, which drops `export-ignore` paths and whatever the engine skips. So
  `file` depends on `measure`, which the table says depends on `file`. Up to 10% of unit files in the tree
  may be absent from a scan that still passes (`MIN_COMPLETE`, `mod1_lift.py:40`). Those need a reason in the
  closed list; the list is not given.

The related fact with no home: the cut time, the snapshot commit, the window start and the window end are
four different things. The `snapshot` table has one hash per role.

**Change.** Drop the two chain invariants or scope them to first-parent repos and make "times increase" a
reported count, not a failure. Give `snapshot` the columns `cut_ct`, `sha`, `ct`, `window_start`,
`window_end`. State the build order `scan → file`. Write out the closed list of exclusion reasons, including
"not in the archive", "not scanned by the engine" and "zero LOC".

**How to test.** Generate a control repository with a side branch holding the cut commit and two commits with
equal and with reversed times; the build must succeed and report them.

### B3. The `label` table cannot hold SA3's outcome — [code]

`label` is one row per (commit, outcome). The invariant talks of "every positive file", but there is no path
column, so positive files must come from a join with `touch`. For a merge that inherits a link that is wrong:
its positive files are the merge's first-parent diff **intersected with the linking commit's files**
(`sa3_outcomes.py:246-253`), per linking commit. Other facts the outcome needs and the tables do not hold:

- the link harvest itself (kind and value per commit: issue, CVE, revert target, trailers). `commit` has no
  message and there is no `link` table. `labels.links(message)` needs an input;
- strict and loose kinds per event (HP versus HP_allreverts), the exclusive tier per commit, own versus
  inherited (`:206-217`, `:274-279`);
- the tainted set and the over-cap merges (`:221-272`);
- the **control pool**: commit to files, for the matched control (`:309-312`). It is defined by the absence
  of a label, so a public pool gives the labelled commits by subtraction from the public `touch` table;
- the revert-target resolution, which depends on every commit reachable from the tip at the time of the
  build (`:189-198`): a longer history can make a 7-character prefix ambiguous.

**Change.** Replace `label` with an event table keyed (repo, unit commit, linking commit, path) carrying
kinds, tier and how; add `link` and `pool` tables; say which of them are protected (all three).

**How to test.** The control repository's `merge_workflow` mutation: the table must reproduce the manifest's
positives for a merge whose diff shares only some files with the linked commit.

### B4. Scrambled labels leak the true labels and the true effect — [synthetic]

Section 6 and step F rest on `blinding_spec.md`: labels permuted within LOC band × directory, 20 copies.
With ten bands, a directory of a few files puts most files alone in their cell, and a file alone in its cell
keeps its label. I simulated this (`scramble.py`: heavy-tailed directory sizes, ten equal-count bands, a
planted effect of +0.16 independent of directory; 30 repos per row). The directory size distribution is my
assumption.

| files | mean files per directory | files alone in a cell | true positives recoverable from 20 copies | share of the true effect that survives |
|---|---|---|---|---|
| 800 | 4 | 52% | 61% | 76% |
| 800 | 10 | 26% | 34% | 47% |
| 800 | 30 | 8% | 14% | 25% |
| 3000 | 10 | 26% | 35% | 48% |
| 3000 | 10, cells = band × 8 top-level directories | 0% | 0% | 3% |

"Recoverable" means positive in all 20 copies. So with full directories: a session holding the scrambles
holds a third or more of the true labels; "any effect on scrambled labels is false by construction" is not
true; and step F's exit test ("every structural effect is null") fails for a correct pipeline exactly when
SA3 has a real effect. Its failure would then be a statement about the confirmatory result. That is defect 26
again.

Step F's test is also not specified: null against what, for how many of 23 predictors × 6 outcomes × 20
repos, with what allowance for chance. A gate nobody has simulated is defect 25.

**Change.** Fix the cell definition in the spec (band × top-level directory, or coarser). Add a label-free
check: from the `file` table alone, the share of universe files in cells of one or two files must be under a
stated limit per repo, else the cells are coarsened. State step F's statistic and simulate it under no effect
and under an effect before it is used.

**How to test.** The check is computable without labels. On the control repository with a planted effect,
the scrambled effect must be under a stated fraction of the true one; the full-directory variant must fail
that test.

### B5. Step A's exit test cannot be run safely as written — [code]

"Every `defs` function equals the SA3 function it replaces on control repositories." The old rules are not
functions that take inputs:

- `universe()` reads a scan database and a sidecar from the study directory and runs `git archive` on a pool
  clone (`sa3_outcomes.py:63-89`). `frame()` reads a history database from a hard-coded study path
  (`mod1_lift.py:37`, `:51`). `build()` is one 180-line function that does all of it.
- Run on a control repository, `sa3_outcomes.py` writes into the real study directory (`OUT`, `:43`, `:348`)
  and may delete a harvest there (`:58`). `sa3_scan.py` reads a MOD-1 file by a path relative to the working
  directory (`:50`). `STUDY` is a constant, not an environment setting; only the pool has one (`_engine.py:32`).
- Phase 2 of the control repository (the harness that runs the old pipeline on a generated repository) does
  not exist; `tools/control_repo/` holds the generator only.

So step A needs a harness that redirects every path, runs the engine, the history walk and the body harvest
on generated repositories, and never touches the study directory. That harness is step A's largest part and
it is not in the plan. A builder who takes the short route runs old tools against the real study directory.

The test is also unsound as the only test. The old code has known faults (entries 31, 42–48, 54, and B1 a, b,
e above). "Equal to old" and "equal to the manifest" (steps B and E) contradict each other on those cases.

**Change.** Make the harness an explicit step zero with its own exit test: the old pipeline runs on a
generated repository with every path under a temporary directory, and a test proves no file under the study
directory was opened for writing. Replace "equals the old function" with the three-way table of B1.

**How to test.** Run the harness under a wrapper that fails on any write outside the temporary directory.

## Major

### 6. Text or code: the spec uses both rules without saying which governs — [code]

Section 5: the code governs, because SA3 is registered. Section 13: for tainted merges keep the code and fix
the text. Step D: fix findings 42, 43 and 47, where the **text** governs and the code is wrong
(`sa3_score.py:432-443`). The registration says the registration governs. A builder needs one stated rule and
a per-item ruling, in the amendment of B1. Test: the rule-to-code table gains a column "governed by" and no
row may be empty.

### 7. The reading-rule truth table omits the dimension where defect 42 lived — [code]

Section 7 lists four inputs: interval side, co-statistic agreement, gate, control. The Holm step makes the
reading of one test depend on the others (`sa3_score.py:425-436`), and what counts as "an earlier test
failed" was the blocker in entry 42. The all-reverts reading (`:477-481`) is a fifth input. A table without
them is tested cell by cell and still wrong. Change: the table is over the family of three, or the Holm step
is a separate tested function with "failed" defined. Test: entry 42's case (first primary contradicted, two
later intervals above zero) is a named row.

### 8. Storage is specified twice, differently; the hash is not canonical — [reasoned]

Section 4: one SQLite database per study and repo. Section 8: each output is a new file named by its content
hash, never written over. A table inside a shared database is not a file, and a SQLite file's bytes are not
stable. Two builders will build two layouts. The row hash is also open: integer 1 against real 1.0 in a
dynamically typed column, float text, nulls, non-UTF-8 paths, sort collation. Change: one file per table
build; state the serialisation (column types fixed, floats as IEEE hex, UTF-8 bytes with a stated escape,
byte-order sort). Test: build the same table twice, once inserted in reverse order and once with integers
written as reals; the hashes must be equal.

### 9. Provenance by import tracing misses most of what moved results here — [code] and [reasoned]

Traced imports cover Python modules loaded in the process. Not covered:

- code run as a subprocess: the engine (`sa3_scan.py:64`), `hist_meta.py` (`sa3_outcomes.py:59`), git, tar;
- data read by path: the linguist lists in `~/.cache` (hash-checked in code, `laws_units.py:69`, so safe only
  if that check is carried over), the nesting files, the MOD-1 snapshot file;
- library versions: numpy and scipy (ranks, t quantiles), `tree_sitter_language_pack`, SQLite, Python;
- `PYTHONHASHSEED`: `sa3_scan.py:39` exists because the engine's output depends on it; SA3's scans were made
  without it. A scan can be hashed but not reproduced;
- the corpus clone's state: the tip (a fetched clone has a new tip and new reachable commits), `.mailmap`
  (the bot flag reads mapped names), partial-clone status. With lazy fetch off, `git log -M` and
  `git archive` fail on a blobless clone; the spec has no "unusable, because" path for that outside the
  mutation tests;
- a module edited during a long run (hash at import, or at ledger time?).

Change: the ledger records interpreter and package versions, the git version, each clone's head hash, and the
hash of every file opened (wrap `open` and `sqlite3.connect` in the runner, not only imports). Test: a stage
that reads a file by path without declaring it must fail.

### 10. What blinding buys in this design, stated honestly — [reasoned]

`touch`, `commit` and `brought` are public, commit messages are in the clones, and `defs.labels` is
importable. True labels are a ten-line join for any session. The lint stops opening a label file and
importing the decryption code; it cannot stop recomputation. The spec's section 12 says so. What the design
does buy: no accidental join, scrambles to develop on, an audit trail. What it does not buy for SA3: anything.
SA3's plaintext labels exist next to the scans the builder will read, and its estimates were partly seen.
For SA3, steps C and F are a rehearsal of the machinery. That is a fair use, but it should be costed as such
(finding 16). One addition worth having: the lint also fails on any call of `defs.labels` outside
`spine/labels/`. It is still evadable; it makes the act visible in a diff.

### 11. The literal lint will raise false alarms at about one in two — [code]

I listed numeric literals in four SA3 files that equal a value named in section 5 (0.80, 730, 30, 20, 0.25,
0.10, 1.5, 10): 24 hits. Eleven are a parameter (one of them the S7 band count). Eleven are not: the ±30 clip
in three logistic fits (6 hits), four `[:10]` and `[:20]` slices, `edges * 10`. Two, on one line, are a real
find (an unnamed copy of the floor, `sa3_score.py:410`). Against all registered values (5, 3, 100, 200, 25, 50 …) the same files give 71 hits.
A lint like that gets a blanket exemption within a week. Change: lint by **name**, not value: `defs` and
`stats` functions take every parameter as a required argument with no default, and no module in `spine/`
outside the configuration loader may assign a module-level numeric constant. Test: run both lints on the
moved `sa3_stats.py`; the count of alarms that are not parameters must be zero.

### 12. The rule-to-code table proves a mapping, not behaviour — [reasoned]

A script can check that each clause names a function and each function a clause. Entry 8 (a rule that was a
no-op) and entry 31 (a rule that silenced two measures) would pass it: the function exists and has a test.
"A second implementation is a build failure" is not enforceable either; the lint catches a reused name, not
an inline copy of a rule. Say so, and put the weight where it belongs: each `defs` test must include a case
taken from the control repository's manifest where the rule changes the answer.

### 13. The control suite has no tolerances, seed counts or cost — [reasoned]

Section 10's rows say "within tolerance" and "recovered". The first review measured what that takes: 800
files and 20 seeds to resolve ±0.03. A quick set of one negative and one positive repository at one seed is
either powerless or flaky. Every run needs an engine scan of a generated repository; the suite as listed is
dozens of scans, and its run time is unknown. Which truth is "the manifest's truth pushed through the same
statistic": the true fixes or the expected labels? The two differ by design (silent fixes). Also out of scope
for an SA3-only spine: the change-effect row, the `prior` role and `cut.prior` (they are SA3-CH). Change:
give each row its file count, seed count and pass rule, simulated for its false-failure rate; measure one
scan's time before fixing the suite's size; drop the SA3-CH rows.

### 14. SA3 facts with no home in the tables or the configuration — [code]

- a repo's status and reason: scan incomplete (six repos), no harvest (`sa3_outcomes.py:148-153`);
- the cohort: drawn or earlier eight. It decides the confirmatory pool (`sa3_score.py:422`);
- derived predictors: ratios to LOC, a sum of two columns, "non-zero yes/no", "the score among non-zero
  files" (missing by design) (`:132-143`). The configuration lists "measure names"; these become plug-ins;
- the count-or-score flag, used by the silent rule, the surrogate and S9 (`:52`, `:189`, `:252`);
- the instrument-silent rule and the pair floor (`:183-190`; `sa3_stats.py:65`). Neither is in section 5's
  function list. The silent rule's 10% and 20 are different parameters from tree-wide's 10% and 20;
- band count by repo size and the tie-break by path (`sa3_stats.py:34-35`);
- the scan's path mapping (`src_root`, `sa3_outcomes.py:72-75`) and the engine id per scan.

### 15. Ambiguities a builder would have to guess — [code] where cited

1. `merges.inherit(...)`: the signature is literally an ellipsis. This is the rule of entry 17.
2. "The earliest merge that reaches it": earliest by chain position or by time? The code walks the chain in
   commit-time order (`laws_history.py:121`, `sa3_outcomes.py:159`).
3. `cut.snapshot(commits, q)`: index `int(n·q)` (code) or `ceil(n·q) − 1` (control repository); ties in
   commit time. `mod1_run.py:93` picks arbitrarily among equal times.
4. `cut.window(snapshot, days)`: the code's end is cut + days, not snapshot + days.
5. `touch`: rename detection settings, copies, a path deleted and re-created, renames in a non-linear
   history. `git ls-tree` without `-z` quotes odd paths; submodule and symlink entries.
6. `commits.tree_wide(n_touched_units, …)`: touched files counted in the snapshot universe, or all unit files
   at the time of the commit (the first review's finding 1).
7. `commits.is_bot(author, committer)`: mapped names or raw.
8. The scramble: directory depth; whether the control pool is permuted with the same permutation as HP.
9. The closed list of exclusion reasons; the order in which reasons are tried (`laws_units.py:140-153` has an
   order and it matters to the reason reported).
10. "Per-repo override … who": which rules may be overridden, and what stops an override added after a
    result.
11. What "the stage's inputs are in the ledger" means for the first stage, whose input is a clone.

### 16. It is over-built for one study; a smaller version prevents the faults that happened — [reasoned]

The spine is a store, a definitions package, an encrypted label store, a runner, a lint, a configuration
language and a plug-in mechanism, written before one study has gone through any of it, by rewriting about
1,500 lines of registered code after its estimates were partly seen. Every rewritten rule is a new chance
for entries 22 and 39. The generality (truth tables as data, plug-ins, selection rules) serves the second
study, which does not exist.

The smallest version that covers the faults in the log:

1. The path-redirecting harness of B5, and the control repository run through the **existing** SA3 code.
2. Three stored tables built by the existing functions, moved not rewritten: `file`, `touch` (snapshot paths
   only), label events; each with a hash. Later stages read them and never call git.
3. A generated seal: hash every file the scorer opens and every module it loads (entry 44).
4. Named random streams, with the repo-order test (entry 45).
5. The reading rule as one tested function, with entry 42's and 43's cases (entries 42, 43, 47, 48).
6. The amendment of B1.

That is steps A-harness, B, half of D and E. I would cut from the SA3 route: the encrypted store and step F
(build and test them on the control repository, as their own project), `study.toml` beyond a flat parameter
file, the plug-in mechanism, the rule-to-code generator, rename following, `prior` and the change effect.
Test of this proposal: the same control suite must pass, and the three-way table must be no longer than the
full spine's.

## Minor

17. **Counts in section 1 are slightly off** (table below): 225 Python files under `tools/`, not 220; 56 with
    an absolute path by my pattern, not 51; the study directory in 14 to 16, not 12; 13 unsealed code files in
    SA3's import closure, not 11; three `ro`, not two. [code]
18. **"No test for any SA3 tool"** is no longer exact: `tests/test_control_repo.py:360-395` tests
    `sa3_nesting.py`, and `sa3_stats.py` has a self-test. No test covers the outcome builder or the scorer. [code]
19. **The `commit` table holds every reachable commit and `touch` every changed path.** For the largest repos
    that is tens of millions of rows and a rename-detecting log over the whole history. Feasible; cost it. The
    code today holds the whole log in memory (`laws_history.py:85`). [reasoned]
20. **Record the clone's tip in `commit`** and refuse a build if it differs from the tip the scans and the
    history were made at (`laws_history.py:170` stores `head`). [code]
21. **"Each step is built by Opus from this document"**: the document is not enough for steps A to C without
    the SA3 code open beside it, and the builder will then be reading the plaintext-label paths. Say what the
    builder may open. [reasoned]
22. **Section 9's duplicate-name lint** cites ten `auc`; those are in `tools/`, which the lint does not scan
    and the spine does not import. The example does not support the rule. [code]

## Claim verification

Section 1 and "Where today's copies disagree". Method: read each cited tool; grep across `tools/`; an AST
walk for the import closure and the path counts.

| claim | verdict | evidence |
|---|---|---|
| Universe rule written 5 ways | confirmed (5 distinct forms) | `Excluder()` with no attributes: `hist_replicate.py:99`, `mod1_lift.py:76`, `laws_history.py:118`, `laws_osv.py:287`; attributes and tutorials: `sa3_outcomes.py:65`, `sa3ch_prepare.py:63`; attributes from a database: `laws_net.py:73`, `laws_imports.py:81`; plus with and without the generated flag and the LOC test |
| Snapshot cut recomputed in 6 places over different commit sets | confirmed | `hist_replicate.py:114`, `hist_hr23.py:48`, `hr1_bias.py:49`, `struct_null.py:107`, `mod1_lift.py:58`, `mod1_run.py:92`; two drop all merges, two keep them in first-parent repos, two decide by a flag |
| Tree-wide written 3 times, three denominators | confirmed | `mod1_lift.py:145` (fix commits, MOD-1 units), `sa3_outcomes.py:175` (SA3 universe), `sa3ch_prepare.py:130` (earlier snapshot's units) |
| Two keyword rules in SA3 | confirmed | KW: `fix_shas(h, "v3c")`, `sa3_outcomes.py:172`, `hist_fixlabel.py:26-42`; taint: `is_fix_message`, `sa3_outcomes.py:269`, `laws_history.py:68` |
| One `assert`, covering some outcome lists and not others | overstated | `sa3_score.py:115` covers the six outcome lists; `hp_commits` and the pool (`:120-121`) are not asserted but fail with a `KeyError`. The assert checks "positives are ranked", not "everything ranked can be positive" (see B1 e) |
| Universe never stored; three tools recompute it from the clone | confirmed, one word off | `sa3_outcomes.py:146`, `sa3_score.py:83`, `sa3_nest_scan.py:35`. The file set comes from the scan; the clone is read for the completeness count (`:82-86`) on every call |
| Seal lists 9 files by hand | confirmed | `sa3_score.py:36-38` |
| Seal omits every data input and 11 rule-defining code files, among them the universe rule | confirmed; I count 13 | closure of the scorer, outcome builder and scans: `_engine`, `fixlike_v2`, `hist_fixlabel`, `hist_meta`, `hist_replicate`, `label_card`, `label_cascade`, `laws_build`, `laws_history`, `laws_units`, `sa3_nest_scan`, `sa3_nesting`, `sa3_scan` |
| Result records no hash of any scan, label or history file | confirmed, with one exception | `sa3_score.py:356`: the nine blobs and the engine id. The marginals file (counts from labels) is among the nine |
| One random stream shared across repos; the placebo restarts it per repo | confirmed | `sa3_score.py:361`; `:247`. Also `boot_ci` restarts at 2982 on every call, `sa3_stats.py:179` |
| Building outcomes deletes and rebuilds one of its inputs | confirmed | `sa3_outcomes.py:58-60` |
| SA3's snapshot is what a MOD-1 tool last wrote to a JSON file | confirmed | `sa3_scan.py:50-51` |
| `sa3_outcome_marginals.json` is written by no tool | confirmed | read at `sa3_score.py:77`; no writer under `tools/` |
| 51 of 220 files hold an absolute path; study directory defined in 12 | overstated in detail | 225 `.py` files (192 top level); 56 with a quoted absolute path; `laws-study/pilot` in 16, assigned in 14 |
| Per-repo exceptions are lists in code | confirmed | `NEW_LANGS` `sa3_score.py:45`; `PRIOR` `mod1_run.py:31`, `mod1_score.py:30`; `PU_` cuts `sa3_score.py:483-484`; also the go/django cut `:488` |
| Nine text-versus-code disagreements; tainted merges counted | confirmed for the merge case | `sa3_outcomes.py:241-253`, `:302`, `:310`. The nine are entry 32; not re-counted |
| No test for any SA3 tool | overstated | minor 18 |
| Bot rule: one regex applied in three places, about 20 SQL filters | confirmed | `laws_history.py:156`, `sa3_outcomes.py:99`, `sa3ch_prepare.py:106`; `bot=0` on 28 lines in 14 files |
| Ten `auc`, two `boot_ci`, two `ro` | wrong on `ro` | ten `auc` and two `boot_ci` confirmed; three `ro`: `mod1_lift.py:45`, `mod1_run.py:41`, `hist_hr23.py:39` |
| Disagreement 1: `touch` built under "the looser rule" | wrong in one word | different, not looser: B1 e |
| Disagreement 2: cut over non-bot commits, merges dropped unless first-parent, commits touching no unit file included | confirmed | `mod1_lift.py:54-58`; `laws_history.py:161-162` stores every commit of the walk |
| Disagreements 3, 6, 7, 8 | confirmed | `sa3_outcomes.py:175`; `sa3_score.py:126` against `mod1_lift.py:110`; `laws_units.py:78-79` against `sa3_nesting.py:62-63`; `sa3_scan.py:73` |

## Defect-log walk-through

"Mechanical" = a build or test fails without anyone thinking of it. "Less likely" = the structure helps but
someone must still write the right case. "Nothing" = the spine does not touch it.

| # | fault | this architecture | why |
|---|---|---|---|
| 2 | ranked files that can never be positive | less likely | `file` is the one universe, but "can be positive" also needs `touch` to cover every universe file (B1 e). Add the invariant: every universe file's path is one `touch` could record |
| 11 | a licence sweep counted as a fix | less likely | `marginal` stores the largest commit's share; the floor rule reads it. Tree-wide stays one definition |
| 13 | statistic scored noise as "contradicted" | nothing | a design fault; found only by simulating the statistic. The control suite runs after the design is fixed |
| 16 | revert tier marked code written after the snapshot | less likely | caught only if the manifest's `reverts_of_new_code` case is in the suite and decided |
| 17 | merge inheritance in one sentence | nothing yet | the spec repeats it: `merges.inherit(...)` (finding 15.1) |
| 22 | merge search ran through bot commits | mechanical, if the mutation is in the suite | `bot_merges` on the control repository with a decided label. Today those labels are all "ambiguous" |
| 23 | else-if nesting counted differently per language | nothing | an instrument fault. Already covered by the control repository's own test 4, not by the spine |
| 25 | an unsimulated gate failed a correct pipeline 71% | nothing, and repeated | step F and section 10 add gates with no simulated failure rate (B4, finding 13) |
| 26 | a diagnostic leaked the estimates | less likely, with a new hole | declared outputs and sealed jobs help. The scramble as specified leaks (B4) |
| 29 | repo-level data faults (all merges bots, imported code, fixtures) | nothing | needs the data card and a person reading it. Mutations show the pipeline's response, not the fact |
| 30 | label precision 73–81% | nothing | a label-audit matter |
| 31 | missing filled with zero; a rule silenced two measures; outputs not coded | mechanical for the first and third, nothing for the second | `measure` forbids zero for missing (but see B1 b); declared outputs can be diffed. The silent rule has no home (finding 14) |
| 39 | rename map built and never read | less likely, new risk | the spine adds rename following that SA3 does not have (B1 a) |
| 42 | Holm step read a contradicted primary as a failure | nothing as specified | the truth table lacks the family dimension (finding 7) |
| 43 | "not robust" fired in one case only | mechanical | a cell-by-cell table test covers it |
| 44 | seal missed labels, scans, universe rule | mechanical, with gaps | generated seal; gaps in finding 9 |
| 45 | shared random stream | mechanical | named streams and the permutation test |
| 48 | a comparison of 18 repos against 15 | less likely | sensitivities name a repo set; the comparison itself still has to check the sets match |
| 49 | a reviewer's git command changed a clone | mechanical inside the spine, nothing outside | the wrapper binds spine code only; a reviewer's shell is not the spine |
| 54 | tainted merges: text against code | less likely | found by the control repository, not by the spine. Still needs the owner's ruling before any merge label is decided |

Of 20: mechanical 5 (two with conditions), less likely 8, nothing 7. **Classes the spine does not touch:**
statistic and gate design (13, 14, 15, 25, 28, 34, 50, 51, 53), power (10, 18, 27, 52), instruments (1, 23,
36, 37, 38), label validity (11's cause, 30), repo-level data faults (29), inference from what was seen (9),
and process (20, 24, 40). Those are about half the log. The spine's real targets are universe, spec-to-code,
seal, reproducibility and plumbing.

## What I did not check

- Any study data, scan, sidecar, label or corpus clone. So I could not size B1 (a), (b) or (e) on SA3's repos,
  and the directory sizes in B4 are assumed, not measured.
- Whether committer times are out of order in any SA3 repo (checked in this repository only).
- `tools/control_repo/` beyond its file list; another session is editing it.
- `hist_meta.py`, `fixlike_v2.py`, `label_cascade.py` and `sa3_nesting.py` beyond the lines cited.
- The engine: what an absent `amplified_cascading_flux` key means (B1 b needs that answer).
- The hash-canonicalisation and provenance findings (8, 9) are reasoned; nothing was run.
- The nine text-versus-code disagreements of entry 32 were not re-counted.
- `sa3_registration.md` and its four amendments; I read the consolidated text only.
