# Comparison scorer, part 1 — review of the build

**Reviewer:** the orchestrating session (Claude Opus 5.5), 2026-11-15. **Built by:** Claude Opus from
`docs/process/comparison_scorer_spec.md` (Revision 2), on decoys only. **Reviewed:** `tools/compare/`,
`tests/test_compare.py`, and the change to `tools/tables/canon.py`.

**Verdict: accept.** No finding against the build. Four corrections to the specification, found by the
builder, are adopted (below).

| check | how | result |
|---|---|---|
| The reference result and the comparison result are the same | the reviewer's own comparison (`mydiff.py`, written for this review, sharing no code with `cellmap.py`): walk both JSON files key by key, exact equality, a missing number equal only to a missing number | **0 differences in 8,559 values in each of the two decoy studies**; no key absent on either side |
| The match is not trivial | the reference file is the reference `score`'s own output (byte-identical to the copy in its work tree); `scorer.py` neither reads that file nor imports the reference scorer | confirmed |
| The decoys carry what they should | the reference result's confirmatory readings | study N (no effect): all three "not detected"; study P (`branches=0.5`): `struct_branch` "supported, defect-specific", mean +0.083 over 10 drawn repos |
| No sealed file changed | the reviewer's own SHA-256 of every code file, job-code file and document listed in `docs/sa3_seal_run1.json` | 26 of 26 equal |
| The table-writer change | read the diff; ran the hash-stability tests (phase A hashes, phase B, canonical bytes, determinism) | existing tables take exactly the old code path (no `spec` given); 10 of 10 pass |
| The builder's test modes | its report: all files together 216 passed and 1 skipped (24 min); each test alone 32 passed and 1 skipped; reverse order, cold, 32 passed and 1 skipped (31 min) | the skipped test is the placeholder for the independent statistic, as specified |
| Coverage of the reference's scoring stage | the builder's traced runs | every executable line except the two "LOCKED" refusals and three reading words no decoy produces: "not detected (Holm: an earlier test failed)", "not robust to the statistic", "supported, but tracks activity". Those three are exercised by the corrected reading rule's truth table in part 2 |

## Corrections to the specification (adopted)

- **F1, duplicate paths.** The loader keeps, per column, the later **non-null** value; for the telemetry record,
  the later record that parses; both file ids count toward the degrees. Stored tables cannot hold a duplicate
  (phase B refuses one), so this affects only the description.
- **F2, nesting.** A null element reads as missing in the loader; phase B's `measure` builder would crash on it,
  and an empty entry stops the loader. Neither occurs in SA3's data (phase B ran on all 46 repos; nesting
  coverage was 100% where a file exists).
- **F3, non-finite telemetry values.** `Infinity` reads as +∞; `NaN` reads as missing. Added to the case table.
- **F4, repo order moves D summaries.** The study summaries add per-repo values in loop order, so swapping
  two repos changes D summaries at the rounding level (at most 1e-12 relative), unless the two are the first
  two. The blind test's expectation for "two repos swapped" is therefore **R, and D summaries**, and exact
  equality is right: a reordering is a real difference.
- The placebo layer of the blind test is defined as an exact re-run of the reference placebo compared with the
  sealed file; "flux rows flagged" counts universe files only; "one call row removed" is made in the degree
  table.
