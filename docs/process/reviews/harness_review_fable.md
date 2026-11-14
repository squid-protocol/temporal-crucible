# Harness — review

**Reviewer:** Claude Fable 5.2, 2026-11-14. **Built by:** Claude Opus from `docs/process/harness_spec.md`.
**Reviewed:** `tools/harness/` and `tests/test_harness.py`.

**Verdict: accept, with two changes to the comparison.** The sandbox is sound and stricter than specified.
The table's facts reproduce. One conclusion drawn from a single repository did not survive ten.

| check | how | result |
|---|---|---|
| Sandbox code | read `sandbox.py` in full | root read-only; the whole projects tree, the home directory, the corpus and `/tmp` are empty read-only filesystems; only the engine export and the Python user site are bound back, read-only; the study path is `WORK/study`; network, IPC and PID unshared; environment cleared. The guard reads the kernel's mount table before touching any path and compares device and inode of the study path with `WORK/study` |
| Tests | re-run | 5 passed, 21 s (four sandbox tests and one end-to-end run) |
| A fresh run by the reviewer | own control repository, own `WORK` | same summary as the builder's: 7 agree, 13 differ, 2 undecided; 16 s |
| Universe row | from the raw outcome file and the probe | 252 ranked, 306 unit files, all 54 missing under a `cache/` directory; the pattern is line 13 of the cached `vendor.yml` |
| LOC row | from the scan database | engine = manifest + 1 on 306 of 306 files |
| Label row | from the outcome file's commit list against the manifest | 78 against 103; 76 shared; the misses are bare Jira keys and commits whose positives are all outside the pipeline's universe; the 2 extra are a revert of the pipeline's own cut commit and the ambiguous quoted-ticket revert |
| Code claims | read the cited lines | Jira pattern (`hist_meta.py:45-50`), fail-open seal (`sa3_score.py:515-520`), swallowed errors (`sa3_nest_scan.py:47-51`), usable-commit stop (`mod1_run.py:90-91`): all as reported |
| Nothing outside the build was written | `git status` | only `tools/harness/` and `tests/test_harness.py` are new |

## Findings

1. **Effect rows at one seed are noise, and the builder read one.** Ten positive controls give a pipeline
   effect of +0.066 (standard error 0.014) against +0.081 on the expected labels and +0.133 on true fixes; the
   single-repository figures (+0.028 against +0.094) overstated the loss at the label step. The 0.01 tolerance
   the builder chose marks sound rows "differ". **Change:** `run.py` takes a list of seeds; effect rows report
   mean and standard error over them and compare within three standard errors; a single run prints the effect
   rows as "one seed: not comparable".
2. **The control-pool and keyword rows compare against a definition the specification got wrong.** The
   reviewer's specification described the manifest side loosely; the code's pool excludes HP-counted commits
   by construction. **Change:** derive the manifest side from the registration's wording (non-bot, in the
   window, in no fix tier, not tree-wide, not tainted) and say which words decided each difference.

The builder's ten notes on the specification are accepted; the route order and the second-snapshot point are
corrected in `harness_report.md`.
