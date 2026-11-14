# The owner-run preparation job — label tables, the last count, two checks and the seal (specification)

**Status: specification, 2026-11-14. Nothing built, nothing run.** It covers Amendment 5's order of operations
from the rest of step (d) through step (f). It does **not** score SA3 and does not build the comparison scorer
(Amendment 5 section 9, layer 3); that is a later specification.

**Who runs it.** The owner, in their own terminal, with one command. It is the first job that binds SA3's
outcome files and link harvest. A session builds and tests it on decoys only, and afterwards reads one file:
the public report.

**What that restriction is worth, stated.** Sessions run as the owner's user, so nothing technical stops a
session from running the job. The protections are: the job's default target is a decoy; the real run needs a
flag whose name says who may use it; everything the job prints or writes outside the protected directory is a
fixed list of counts and verdicts; and the protected directory holds nothing that the existing plain-text
outcome files do not already hold. The job makes an accident hard and leaves a record. It is not a wall.

## What the job reads

Per repo, bound read-only in the sandbox of `tools/harness/sandbox_ro.py`, one repo at a time: everything
phase B binds (history database, scan database with its side files, scan sidecar, nesting file, the clone,
GitHub's two lists), **plus the outcome file and the link harvest** (`sa3_outcomes/<repo>.json`,
`meta_sa3/<repo>.db`). For the placebo regeneration (below), all scored repos' inputs at once, read-only.
Databases are copied to scratch and the copies opened, as in phase B.

## What the job writes

**To the protected directory** (given with `--protected DIR`; mode 700; outside this repository and outside the
study directory): per repo the tables `touch`, `link`, `event`, `pool`, `marginal`, built by phase A's builders
(made importable, as phase B did for the other four, with phase A's table hashes unchanged), with `index.json`.
Nothing else reads this directory until the scoring job.

**To the public directory** (`--out DIR`): exactly these, and a test asserts the list is closed:

| file | holds |
|---|---|
| `owner_report.json`, `.md` | per repo: the tracker-key count (below); the verdicts of layer 1; for each failed invariant its number and count; table row counts. For the study: the verdict of layer 2; the seal's hash; versions; start and end times |
| `seal.json` | hashes only (below) |
| `run_log.json` | stages and return codes |
| `manifest_before.json`, `manifest_after.json`, `manifest_diff.json` | the stat manifest of every input and each clone's `.git`, as in phase B |

**On the terminal:** stage names, repo names, "ok" or "failed", and at the end the path of the report. No path
inside a repo, no commit hash, no count per file.

## The four things it computes

**1. The label tables**, and their invariants (`tables_spec.md` invariants 4 to 6), reported for a protected
table by number and count only.

**2. The tracker-key count** (Amendment 5 section 7 item 5, last part): per repo, the number of commits that
count under the primary outcome **only** because of a tracker key that is not all capitals. Defined as: a
commit with an `event` row under HP, whose links that could qualify it are all of the tracker-key form, each
with a key containing a lower-case letter. The builder establishes from `tools/hist_meta.py` and the stored
`link` rows how a tracker-key link is told apart from the other forms of the same pattern, and **states it**;
if the stored rows do not allow it without re-applying a pattern, the two patterns of Amendment 5 section 5
are applied to the stored commit messages by **calling the reference module's own compiled patterns**, never a
copy. Also reported per repo: commits under HP in all; commits that have at least one lower-case tracker-key
link beside another qualifying link. Three integers per repo, nothing else.

**3. Layer 1 of Amendment 5 section 9 — the inputs are the same.** Per repo, printed as equal or not equal:

- the set of universe paths in the stored `file` table (phase B's, read from its output directory and checked
  against the hash in its index) against the set `universe()` returns now;
- for each outcome tier, the set of (commit, path) pairs in `event` against the outcome file's lists; the pool
  likewise; each `marginal` row against the committed public marginals file.

**4. Layer 2 — a known output is reproduced.** The reference scorer's `placebo` stage is run, unchanged, on
the real inputs, from a copy of the code in scratch, so that it writes its output there and not over the
committed file. Compared with the committed `docs/sa3_placebo.json`: byte for byte when the interpreter,
numpy and its linear-algebra library are the versions recorded below; otherwise number by number within 1e-9.
The report gives the verdict, the largest absolute difference, and the versions. (The placebo output is
already public.) **No version was recorded with the original placebo run**; the report therefore states the
versions now and whether the bytes matched, and says that a byte mismatch with a number match within tolerance
cannot be told apart from a library change.

## The external seal (Amendment 5 section 2)

`seal.json`: the SHA-256 of every input file the confirmatory run will read — for every repo on the frozen
list its scan database (with side files), sidecar, history database, link harvest, outcome file and nesting
file; GitHub's two lists; `docs/sa3_outcome_marginals.json`, `docs/sa3_placebo.json`, `docs/sa3_power.md`,
`docs/sa3_code_review.md`, `docs/sa3_registration.md`, `docs/sa3_registration_consolidated.md`; every code file
the reference scorer loads (found by running its `placebo` stage with an import recorder and listing the
modules loaded from `tools/`), each with its git blob hash at `HEAD` and a check that it equals the reference
contents of Amendment 5 section 1; the interpreter's and each loaded package's version; each clone's `HEAD`.
The seal's own SHA-256 is printed and written in the report. Hashes only: no content.

`seal.py verify` recomputes it and prints which entries differ. The scoring job will call it first.

## How it runs

```
python3 tools/owner/prepare.py --decoy DIR --protected P --out O           # ordinary mode; what tests use
python3 tools/owner/prepare.py --real --i-am-the-owner --protected P --out O --phase-b DIR
```

- No target: refused. `--real` without the second flag: refused. With it: every stage still runs inside the
  read-only sandbox and its guard.
- `--phase-b` names phase B's output directory, read-only.
- Before anything else on a real run it prints, and waits for Enter: what it will bind, where it will write,
  and that it does not score.
- A repo whose stage fails is recorded and the run continues. A failure is not investigated on real data.

## Before the owner runs it

1. **Tests on decoys** built by the harness from control repositories (base Python and C, `merge_workflow`,
   `bot_merges`, `generic_dir_names`, a repo with no outcome file):
   - the five label tables equal phase A's, hash for hash;
   - layer 1 reads "equal" everywhere on an untouched decoy, and "not equal" — naming the table, never a row —
     when one path is removed from an outcome file's list, one commit added to the pool, one universe file
     dropped from the stored `file` table, or one marginal altered;
   - layer 2 reads "equal" on an untouched decoy and "not equal" when one input value is changed;
   - the tracker-key count equals the number planted: control-repository commits rewritten in the decoy's
     harvest and outcome file to carry "Fix utf-8 …"-style subjects, alone and beside another link;
   - the seal: unchanged inputs verify; a change to any one input, code file or document is reported by name;
   - **the closed list:** after a run, the public directory holds exactly the files above, and no string from
     the decoy's outcome files or link harvest (commit hashes, paths) appears in any of them or on the
     terminal — tested with planted marker strings;
   - the sandbox tests of phase B, with the label-side inputs added to the declared list.
2. An independent review of this document, then of the build.
3. The owner is given the one command, what it will print, and how long the decoy run took.

## Deliverables

```
tools/owner/prepare.py      the job
tools/owner/layers.py       layers 1 and 2
tools/owner/seal.py         write and verify
tools/owner/README.md, DECISIONS.md
tests/test_owner_prepare.py
```

and one listed change to phase A: the `touch`, `link`, `event`, `pool` and `marginal` builders made importable
from `tools/tables/build.py` without changing what they produce.

## Rules for the builder

- Decoys only. Never `--real`. Never open, list or stat the real study directory, the corpus, the pool, the
  phase B output directory under `/srv/storage_16tb/projects/temporal-crucible-tables/`, or `~/.blind`.
- Write only the deliverables and the listed phase A change. No commits. No edit to any SA3 tool, to
  `tools/harness/sandbox.py` or `sandbox_ro.py` (if `sandbox_ro.py` needs a change to declare more inputs,
  report it instead of making it).
- Report: what was built; test results; the decoy run's time; exactly how a tracker-key link is recognised;
  every module the import recorder found; anything here that is wrong, ambiguous, unsafe or impossible.
