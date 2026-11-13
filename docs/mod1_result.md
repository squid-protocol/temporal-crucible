# MOD-1 result (2026-11-13): no age effect detected — and almost no sign split to explain

Registered in `docs/moderator_registration.md` (Amendments 1–3, all before any drawn repo was scored).
Scorer output verbatim: `docs/mod1_result.txt`; per-repo measurements: `docs/mod1/lift_<repo>.json`.

## Verdict: MOD-H1 not detected

| run | n | `old` coefficient | 95% CI | reading |
|---|---|---|---|---|
| Primary | 37 | −0.027 | [−0.073, +0.014] | not detected |
| S1 new-language repos removed | 30 | −0.028 | [−0.081, +0.021] | not detected |
| S2 drawn repos only | 29 | −0.006 | [−0.045, +0.033] | not detected |
| S3 low call coverage removed | 34 | −0.031 | [−0.077, +0.012] | not detected |
| S4 short window removed | 32 | −0.035 | [−0.088, +0.015] | not detected |
| S5 merge-workflow removed | 26 | −0.048 | [−0.119, +0.011] | not detected |

`C_family`, continuous age and the interaction (all secondary) also include zero. At this power an age
difference smaller than about 0.05 could not have been seen; this is "not detected", not "no effect".

## What the per-repo table shows instead

In-degree **loses to LOC in 31 of 37 repos**; the CI excludes zero on the negative side in **27**, on the
positive side in **3** (cpython, ndpi, sphinx), and includes zero in 7. Mean lift by cell: old/C −0.076,
old/managed −0.068, young/C −0.022, young/managed −0.064.

Two of the three solidly positive repos (ndpi, sphinx) are among the eight that generated the hypothesis.
Among the 29 drawn repos that could be scored, one (cpython) is solidly positive. The "four up, four down"
split that motivated the study was mostly the old file universe plus which repos happened to be looked at
first — not a property of repositories.

## Excluded, each with its reason (9 of 46)

- **Scan incomplete (< 90% of unit files scanned):** root (6,680 of 13,146), livecode (323 of 1,049),
  wrf-fortran (747 of 950), wordpress (907 of 1,082), pwntools (141 of 177), macports-base (0 of 128).
  Cause not yet traced; this removes two of the old/C census.
- **Under the 30-positive floor:** impacket (25), tigerbeetle (17).
- **Nothing to rank:** bugzilla — all 198 Perl unit files are positive, which points to a tree-wide commit
  being labelled a fix. The same thing could inflate positives elsewhere and has not been checked.

## Limits

- The label is still the cascade, whose recall is unmeasured; in merge-workflow repos the keyword tier sees
  little (S5).
- Call resolution in the seven languages added today is unverified; swift passes the pre-set check with only
  10% of its files having any caller.
- 1st-percentile dating moved go to young as expected; wrf-fortran would have moved to old but is excluded.
- A hand-collected pool of well-known survivors. No claim beyond it.
