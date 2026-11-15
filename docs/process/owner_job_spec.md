# The owner-run preparation job — the last count, the placebo reproduced, and the seal (specification)

**Status: Revision 2, 2026-11-14, after an independent review. Nothing built, nothing run.** It covers
Amendment 5's order of operations from the rest of step (d) through step (f). It does not score SA3.

**What Revision 2 changed.** The first version was reviewed (`reviews/owner_job_spec_review_claude.md`: 4
blockers, 9 major, 8 minor; "safe after changes; not safe to build as written"). No public output would have
given a session a predictor-against-outcome estimate. The faults were elsewhere:

- **Smaller.** The label tables and "layer 1" are gone from this job. Tables built from the outcome file and
  then compared with the outcome file cannot disagree; and the sorted tables lose the order of commits the
  reference scorer's matched control depends on. Both belong to the comparison scorer's specification. Only
  the count and the seal are required before scoring; the placebo reproduction is kept because it is cheap
  and is the only check here that can fail.
- **The count is redefined** so that it can be computed, by running SA3's own outcome builder twice.
- **Nothing free-form can reach the public report.** Stages cannot write to the public directory; the launcher
  writes the report from values it validates against a fixed shape.
- Byte sizes and row counts of label-side files are no longer public. The seal no longer hashes files that
  change when read, and is checked after the reference `lock`, not only before.

**Who runs it.** The owner, in their own terminal, with one command. A session builds and tests it on decoys
only, and afterwards reads the public report.

**What that is worth, stated.** Sessions run as the owner's user. The label rule, the commit messages and the
code are all readable, so a session could reconstruct labels without this job. What the job preserves is
narrower and real: nothing it publishes relates an outcome to a predictor, nothing it publishes confirms a
reconstructed label set, and every run leaves a record. It makes an accident hard. It is not a wall.

## What the job computes

### 1. The tracker-key count (Amendment 5 section 7, item 5, last part)

A stored fix-reference link whose value contains a hyphen is a tracker key — the only form of the pattern
that keeps one — and its case is kept. So "a lower-case tracker key" is a link row with `kind = 'issue_fix'`,
a hyphen in `value`, and `value != upper(value)`.

- **A** = the commits under the primary outcome when the reference `sa3_outcomes.build(repo)` is called,
  unchanged, on the real inputs.
- **A′** = the same call on a copy of the link harvest from which those rows have been deleted. The copy keeps
  its `meta` rows, so the builder does not try to re-harvest.
- **The count is the number of commits in A and not in A′.**

Merges, trailers, reverts, CVEs, the 50-commit cap and bots are handled as the frozen code handles them,
because it is the frozen code. `build()` returns its result and writes nothing.

Published per repo, all integers or yes/no:

| value | meaning |
|---|---|
| the count | commits that are positives only through a lower-case tracker key |
| A equals the stored outcome file's primary commits, as a set | yes / no. A "no" means the builder no longer reproduces the stored file; the count for that repo is then not reported |
| disagreements between the hyphen rule and the reference module's own pattern re-applied to the stored messages | a number, expected 0 |
| determined | no, with a fixed reason code, where `build()` cannot run (for example a clone that cannot serve the archive without a fetch). Never reported as zero |

Not published: A itself, any file count, any path or hash.

**A note for the reader of Amendment 5.** "Fix UTF-8 decoding" is not in this count: `UTF-8` is in capitals and
matches the key pattern as registered. The count is of keys with a lower-case letter ("fix x86-64 build",
"Fixed sha-1 fallback"). See the proposed erratum, `docs/sa3_amendment5_erratum_draft.md`.

### 2. The placebo output reproduced (Amendment 5 section 9, layer 2)

The reference scorer's `placebo` stage is run unchanged, from a copy of the reference code in protected
scratch whose `docs/` directory is writable and holds copies of the files the stage reads there. It reads the
outcome files (through the scorer's own loader). Its output is compared with the committed
`docs/sa3_placebo.json`.

| verdict | meaning | what follows |
|---|---|---|
| `bytes_equal` | the code and inputs reproduce the published gate result exactly | proceed |
| `numbers_equal` | every number within 1e-9, bytes differ | proceed; the report gives the largest difference and the versions. A library change and a formatting change cannot be told apart, and the report says so |
| `differs` | some number is beyond 1e-9 | **stop.** Nothing after this job proceeds. The report gives the largest difference and how many numbers differ, not which. It is reproduced on a decoy; the real cells are not examined |
| `failed` | the stage did not complete | stop; a fixed reason code |

The committed placebo file was produced by the code as at `8fb7fe0` on a date and with library versions that
were not recorded. The report states the versions now.

### 3. The external seal (Amendment 5 section 2)

`seal.json`, hashes only:

- every input file the confirmatory run reads, for every repo on the frozen list: the scan database's main
  file and its write-ahead file (**not** the `-shm` file, which changes on an ordinary read), the sidecar, the
  history database, the link harvest, the outcome file, the nesting file; GitHub's two lists; the six
  documents the reference `lock` names;
- every Python module the reference scorer loads from `tools/` (found by an import recorder around the
  `placebo` stage; the review counted twelve), each with its SHA-256 and its git blob hash, **and a check that
  the file has not changed since `8fb7fe0`**;
- **the nine blob hashes the reference `lock` is expected to write**, so that after the owner runs `lock` the
  seal can be checked against `docs/sa3_lock.json` (the reference `lock` writes empty hashes when git fails,
  and its own check then passes);
- versions: the interpreter, every loaded package, git, tar, the linear-algebra library numpy links; and the
  environment variables that can change a result (thread counts, the hash seed);
- each clone's `HEAD`.

`seal.py verify` recomputes it and prints which entries differ, by name. `seal.py verify --after-lock` also
compares the nine hashes with `docs/sa3_lock.json`. The scoring job will call both.

The seal says what the files were when it was taken. It does not prove that the run read those bytes; the
read-only sandbox does that part.

**Sizes of label-side files are not written anywhere public.** A size is a cheap test of a guessed label set.
The before-and-after manifest of label-side files is kept in the protected directory; the public report
carries only "unchanged: yes / no" and the number of entries.

## Where things are written

- **The protected root** (`--protected DIR`): a new directory, mode 700, under
  `/srv/storage_16tb/projects/temporal-crucible-protected/`, outside this repository, the study directory and
  every place sessions use for scratch. All stage scratch, all stage logs, the copies of databases, the
  harvest copy and the label-side manifest live here. `tools/harness/sandbox_ro.py` today allows writable
  directories only under the session scratch roots; **it gains one more allowed root, this one**, as a listed
  change with tests.
- **The public directory** (`--out DIR`): `owner_report.json`, `owner_report.md`, `seal.json`, `run_log.json`.
  **No stage's sandbox has it bound.** The launcher alone writes it, after validating every value:

  | field | allowed |
  |---|---|
  | repo names | only names in the committed marginals file |
  | counts | non-negative integers |
  | verdicts, reason codes, stage results | members of fixed lists written in the code |
  | hashes | 64 hexadecimal characters |
  | versions | the pattern of a version string |
  | times | integers |
  | the largest placebo difference | one real number |

  Anything else stops the launcher with "invalid report value" and the field's name. **Exception text is never
  copied**: a stage that fails contributes its stage name and a reason code. (The reference loader raises a
  `KeyError` whose text is a file path from an outcome file; the phase B launcher would have logged it.)
- **The terminal:** stage names, repo names, `ok` / `failed`, and at the end one line: **`PASS`** or **`FAIL`**
  with the reason codes, then the path of the report.

## PASS and FAIL

`PASS` means all of: every repo on the frozen list has a determined count with "A equals the stored file" =
yes and zero pattern disagreements; the placebo verdict is `bytes_equal` or `numbers_equal`; the seal was
written; the manifests are unchanged. Otherwise `FAIL`, with the codes. The report's first line is the same
word, so the owner can judge it without help.

A run that stops partway leaves a `run_log.json` saying where. A second run **refuses** a protected directory
that is not empty; the owner names a new one. Nothing is resumed or overwritten.

## How it runs

```
python3 tools/owner/prepare.py --decoy DIR --protected P --out O           # ordinary mode; what tests use
python3 tools/owner/prepare.py --real --i-am-the-owner --protected P --out O
```

No target: refused. `--real` without the second flag: refused. On a real run it first prints what it will
bind, where it will write and that it does not score, and waits for Enter. Every stage runs inside the
read-only sandbox and its guard; the clone and every study input are bound read-only; databases are copied
into protected scratch and the copies opened.

## Before the owner runs it

Tests on decoys built by the harness from control repositories:

1. **The count**, against planted commits in a decoy's harvest and messages: a lower-case key alone (counted);
   with `#N`, with an upper-case key, with a `Fixes:` trailer, with a CVE (not counted); a late revert quoting
   a lower-case-key subject (counted) and an early one (not); a merge inheriting a lower-case key from one
   brought-in commit (counted) and from one beside another carrying `#N` (not); a `Fixes: deadbeef-1` subject,
   whose reading is stated and tested. On an untouched decoy, "A equals the stored file" is yes.
2. **The placebo:** `bytes_equal` on an untouched decoy, twice in a row; `differs` when one scan value is
   changed; `failed` with its code when an input is missing; the committed-file path is never written.
3. **The seal:** verifies on unchanged inputs; a changed input, module or document is named; a `-shm` file
   touched by a read does not fail it; `--after-lock` passes against a correct lock file and fails against one
   with empty hashes.
4. **No way out for label-side text:** with marker strings planted in a decoy's outcome file and harvest —
   in paths and commit hashes that occur nowhere else — a normal run, a run where a stage raises an exception
   carrying a marker, and a run where a stage prints a marker each leave no marker in the public directory or
   on the terminal. The validator rejects a report carrying a path, a 40-character hash or free text.
5. The sandbox tests of phase B with the label-side inputs declared, and the new protected root: writable
   inside the sandbox, refused if it lies in any data root or in a session scratch root.
6. An independent review of the build. The owner is then given the command, what it prints, how long the
   decoy run took, and what `PASS` and `FAIL` mean.

**Amendment 5's seeded-fault test** (five faulty copies and five clean ones, judged blind) is not part of this
job: a fault in the scorer can only be seen by the comparison scorer. It is carried by that specification.

## Deliverables

```
tools/owner/prepare.py        the launcher and its in-sandbox stages
tools/owner/tracker_keys.py   the count
tools/owner/placebo_check.py  the placebo reproduced
tools/owner/seal.py           write, verify, verify --after-lock
tools/owner/report.py         the validator; the only writer of the public directory
tools/owner/README.md, DECISIONS.md
tests/test_owner_prepare.py
```

and one listed change: `tools/harness/sandbox_ro.py` allows the protected root as a writable location.

## Rules for the builder

- Decoys only. Never `--real`. Never open, list or stat the real study directory, the corpus, the pool,
  `/srv/storage_16tb/projects/temporal-crucible-tables/`, `/srv/storage_16tb/projects/temporal-crucible-protected/`
  or `~/.blind`. Tests use a throwaway directory as the protected root, with the production path a parameter.
- Write only the deliverables and the listed change. No commits. No edit to any SA3 tool.
- Report: what was built; test results; the decoy run's time; the modules the import recorder found; anything
  here that is wrong, ambiguous, unsafe or impossible.

## Review record

| point | disposition |
|---|---|
| B1 outcome-side text has ways out; the protected directory had nowhere safe to live | adopted: a protected root; no stage can reach the public directory; exception text never copied |
| B2 the closed list was a test of file names | adopted: a validator of values |
| B3 the count was not computable as defined | adopted: two unchanged runs of the reference outcome builder |
| B4 layer 1 cannot fail; the tables lose the commit order and the keyword files | adopted: label tables and layer 1 moved to the comparison scorer's specification |
| M1 the placebo copy needs a writable `docs/` | adopted |
| M2 no rule for a placebo mismatch | adopted: four verdicts and what follows each |
| M3 the seal hashed files that change when read | adopted: no `-shm`; the limit of a seal stated |
| M4 the closure beyond Python modules | adopted: tool and library versions, environment |
| M5 `lock` writes after the seal and passes with empty hashes | adopted: the nine expected hashes; `--after-lock` |
| M6 pass or fail; partial runs | adopted |
| M7 the amendment's example is not in the count | adopted: stated here; an erratum is proposed to the owner |
| M8 the seeded-fault test | carried by the comparison scorer's specification; an erratum is proposed to the owner |
| M9 two of four parts not needed before scoring | adopted |
| sizes and row counts of label-side files | no longer public |
| Not adopted | none |
