# Comparison scorer, part 2 — review of the build

**Reviewer:** the orchestrating session (Claude Opus 5.5), 2026-11-15. **Built by:** Claude Opus (part 2) and,
for `reading_b.py`, a fresh Claude Fable session working blind from sections 2.1, 2.1a and 2.4 only.

**Verdict: accept.** One question of wording is put to the owner (below); it changes no number.

| check | how | result |
|---|---|---|
| The reading rule | the reviewer's own transcription of the reference's Holm block (`sa3_score.py:424-444`) and of the two changes, written for this review, against `reading.py` and `reading_b.py`, on 327,680 inputs: four readings for each statistic of each test, control supported or not, five p-orders with ties, the gate both ways | **0 differences** among the three, for coded and corrected |
| The counts of the specification (729 space) | the builder's `counts_729` and the second builder's own enumeration | both 135/51, 604/0, 631/51; plain null unchanged |
| `coded` against the running reference | the builder ran the reference's own `stage_score` Holm block in the sandbox on 92,160 synthetic inputs, and against the stored readings of both decoy studies and the gate-failed variant | equal everywhere |
| Named streams | the builder's tests: reversing repo order leaves every per-repo cell bit-identical (summaries within 1e-12); dropping a predictor leaves every other cell identical; under the shared stream both change R cells (1,004 and 828). Part 1's cell maps stay all-equal with the hook in place | accepted |
| The two harvest variants | planted cases with expected leavers written beforehand; the late-revert resolution against the reference's own primary/all-reverts split | exactly the planted commits move; 206 cases, 0 disagreements |
| Variant output | the builder's runtime check refuses any output containing "supported", "contradicted" or a Holm level | in place |
| No sealed file changed | the reviewer's SHA-256 of all 26 sealed files against `docs/sa3_seal_run1.json` | 26 of 26 equal |
| Test modes | the builder's report: alone 23 of 23; reverse order 23; with every other test file 242 passed and 1 skipped (part 1's placeholder) | accepted |

**The table for the owner.** The generated exhaustive table is 65,582 lines; nobody can read it. A short table,
`docs/process/reading_rule_owner_table.md` (115 lines), shows each change on its own: 6 of 64 rows differ under
change 1, 9 of 20 under change 2. The exhaustive table stays as the record.

**Question for the owner (asked separately).** Read literally, change 2 also turns a test whose two statistics
are "not fitted" on one side only into "not robust". "Not fitted" is the absence of a reading (fewer than three
repos), not a reading. On SA3's 15 drawn repos a confirmatory primary cannot be "not fitted", so this changes
no confirmatory reading; it decides only what the table says for an input that cannot arise.

**Accepted readings of points the builder raised:** the late-revert variant's test on an unedited decoy expects
the planted commits plus the decoys' own late reverts carrying tickets (the specification's "equals" was wrong);
`PU_named_streams` is compared with the frozen run; a variant that deleted no row equals its baseline without
being re-scored; trailers and CVE ids are untouched by the late-revert variant, as specified.
