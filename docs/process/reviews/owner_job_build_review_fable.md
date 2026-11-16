# The owner-run preparation job — review of the build

**Reviewer:** Claude Fable 5.2, 2026-11-14. **Built by:** Claude Opus from `docs/process/owner_job_spec.md`
(Revision 2), on decoys only. **Reviewed:** `tools/owner/` (prepare, tracker_keys, placebo_check, seal,
report), `tests/test_owner_prepare.py`, and the change to `tools/harness/sandbox_ro.py`.

**Verdict: accept, with one change** — a pass condition the specification omitted.

| check | how | result |
|---|---|---|
| The validator | read `report.py` in full | every published value is a non-negative integer, a yes/no, a member of a fixed list in the code, a hash of fixed length, a version string by pattern, or a repo or module name from a set the launcher builds from public sources. Map keys are validated as values are. An invalid value raises an error that names the field's place in the schema, never the value or the key. The Markdown page is rendered from validated values and fixed words |
| Tests | re-run | owner job 18 passed; phase B 27; tables 14; harness 6 |
| No target; `--real` without its second flag | run | refused |
| A clean run by the reviewer | own decoy (a control repository through the harness, the clone reached through a symbolic link) | `PASS` in 2 s. The public directory holds exactly `owner_report.json`, `owner_report.md`, `seal.json`, `run_log.json`. None of the decoy's qualifying commit hashes, none of its positive paths and not the byte size of its outcome file appears in them. The protected directory is mode 700 |
| A planted marker | a path that is in no universe added to the outcome file's primary file list and to one commit's list | `FAIL placebo_failed`, exit 1; the marker is absent from the terminal and from every public file |
| The count's definition | the builder's planted cases, read against the specification | lower-case key alone counted; beside `#N`, an upper-case key, a `Fixes:` trailer or a CVE not counted; "Fix UTF-8 decoding" not counted; late revert quoting a lower-case subject counted, early one not; a merge inheriting a lower-case key counted, beside another carrying `#N` not. All as specified |

## Findings

1. **A changed reference module does not fail the job.** The seal reports "unchanged since `8fb7fe0`: no" and
   the verdict stays `PASS`. The specification's definition of `PASS` left it out. The frozen code being what
   runs is the purpose of the seal. **Change:** two new failure codes, for "changed" and "could not be
   checked", with tests.

## Rulings on the builder's questions

- The six sealed documents are the five the reference `lock` names plus the registration. Accepted.
- A clone's `HEAD` is published as the SHA-256 of the id, so that no 40-character hash appears. Accepted.
- "The frozen list" is the repos with status `ok` in the committed marginals file; the placebo stage covers
  those that also clear the primary floor. Accepted.
- The side files of all three databases are sealed, not only the scan database's. Accepted.
- The report's path is printed before the `PASS` / `FAIL` line, so that the verdict is the last line. Accepted.

## Found by the builder, for the scoring step

In a linked git worktree whose main repository is not visible, git fails and the reference `lock` writes empty
hashes; its own check then passes. This checkout is a linked worktree. The seal's `--after-lock` check refuses
such a lock file. The scoring step's specification must say where `lock` is run.

## What cannot be known from decoys

How long the two runs of the outcome builder take on the real clones (each stage has a two-hour limit and is
then reported as not determined, never as zero), and whether the committed placebo file reproduces at all.

## Second pass: a fault in the launcher, found by running the tests together

After the pass condition was added, the reviewer ran all six test files in one process and one test of the
real-run path failed: every stage `ok`, then `FAIL launcher_error`. Run with the owner-job file alone, in
order, it passed.

**Cause (found by the builder from the launcher's own log on a decoy):** the launcher loaded its sibling
`tools/owner/seal.py` by the bare name `seal`. `tools/blind/seal.py` is loaded under the same name by the
blinding tests. In a process that had already loaded the blinding module, the launcher got the wrong one and
its call to compose the seal failed. A second, separate fault made the same test fail when run entirely alone:
it read another test's output directory without depending on that test.

**Would the owner's run have hit it?** No: a fresh run of the command never loads the blinding tools. But the
launcher's correctness depended on what else was in the process, and the test of the real-run path could pass
or fail for reasons unrelated to that path. Both are fixed in the code: every module of the job now loads its
siblings by file path under a unique name, and the tests declare what they depend on.

**Added:** a test that runs the real-run path in a **fresh interpreter**, with Enter typed into a
pseudo-terminal, a protected root that does not exist beforehand (created with mode 700), `PASS`, then
`seal.py verify` in another fresh process; and refusals when something other than Enter is typed. A table of
every branch a real run takes that a decoy run does not, each with the fresh-process test that covers it, is
in `tools/owner/DECISIONS.md`.

**Re-checked by the reviewer:** all six test files in one process, 184 passed; each real-path test alone,
passed; the owner-job file in reverse order, 21 passed; a fresh decoy run, `PASS`.

**Accepted.** The lesson for the builder's brief next time: run the new tests together with every existing
test file, alone, and in reverse order, before reporting.
