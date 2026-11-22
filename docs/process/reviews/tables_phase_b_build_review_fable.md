# Stored tables, phase B — review of the build

**Reviewer:** Claude Fable 5.2, 2026-11-14. **Built by:** Claude Opus from `docs/process/tables_phase_b_spec.md`
(Revision 2), on decoys only. **Reviewed:** `tools/harness/sandbox_ro.py`, `tools/tables/phase_b.py`,
`study_card.py`, `silence.py`, `manifest_stat.py`, `tests/test_tables_phase_b.py`, and the two phase A changes.

**Verdict: accept.** One test of phase A failed because the specification asked for a message change and for
the old tests to pass; the test is corrected.

| check | how | result |
|---|---|---|
| The sandbox and guard | read `sandbox_ro.py` in full | root read-only; the corpus root, the projects root, the home directory, `/tmp`, the study path and the pool path are empty read-only filesystems; only one repo's declared files and its clone are bound in, read-only; scratch and output are the only writable mounts; network unshared. The guard reads the kernel's mount table and the interface list and nothing else, and refuses a writable mount anywhere under a hidden root unless it is a declared scratch or output directory |
| No target, or `--real` without its second flag | run | refused, before any sandbox |
| Tests | re-run | phase B 26 passed; harness 6 passed; phase A 13 passed, 1 failed (the specification's contradiction) |
| A run by the reviewer | own control repository (`generic_dir_names`, seed 91) through the harness, laid out as a decoy **with the clone reached through a symbolic link**, as in the real pool | preflight, copy, tables and both silence stages ran in 1.8 s |
| Tables | file names (hashes) against phase A's for the same repository | `repo`, `snapshot`, `file`, `measure` all equal |
| Nothing from the label side | listing of the output | no `touch`, `event`, `link`, `pool`, `marginal`; the decoy's 86 qualifying commit hashes appear in no output and no scratch text file |
| Nothing changed | the reviewer's own listing of every file of the decoy study and the clone (size, modification time, change time), before and after | identical, 573 entries. The job's own manifest covers the linked clone's `.git`: pack files, refs, reflogs, config |
| A missing clone | an accident of the reviewer's first decoy | the tables stage failed for that repo with a recorded reason; the other stages ran |
| Counts on the decoy | the study card | 63 files excluded only by the four patterns, 48 of them with scan rows; registered completeness 1.0 against 0.969 measured against the tree; silence differs between the two rules for `def_safety`, `nest_max` and `risk_safety_nonzero`; the placebo check equal |

**Rulings on the builder's questions.** The window start is written as the later of the cut and the snapshot's
time. That restates one line of the outcome builder; it is accepted because Amendment 5 states the rule in
those words and the owner-run job will compare it with the stored value. Silence is a property of (repo,
measure); the study card reports it that way and also as the (repo, outcome, measure) cells Amendment 5 names.

**For the real run:** preflight first, on all repos, read before any table is built.
