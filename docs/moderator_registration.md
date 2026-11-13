# Registration: what moderates the sign of the structural effect? (MOD-1)

**Registered 2026-11-13, before any drawn repository was scanned.** The draw
(`docs/draw40.json`, seed 20261113) was made first and is fixed; no result from any of the 38 new repos
existed when this was written.

## Why

`struct_null.py` found call-graph in-degree beating LOC in four repos and losing in four, every one with a
bootstrap CI excluding zero, pooling to **+0.006** — a null no repository exhibits. In those eight, **age and
language are perfectly confounded**: all four anti-predictive repos are old C. The confound is the reason for
this study.

## Draw

38 repos from `/nvme-data/gitgalaxy-data`, stratified, excluding the 10 already assessed:

| cell | available | drawn |
|---|---|---|
| old C (first commit < 2006) | 8 | **8 — the whole cell** |
| young C | 12 | 10 |
| old managed | 10 | 10 |
| young managed | 41 | 10 |

**Pre-registered deviation**: old-C is short (8, not 10) because the pool holds only 8. Recorded here rather
than back-filled from a different source.

With the 8 previously assessed repos, the analysis set is **up to 46**.

## Hypotheses

- **MOD-H1 (age).** The in-degree lift over LOC is lower (more negative) in older repositories.
  *Mechanism*: in a long-lived codebase a hub is battle-tested — its bugs were found years ago — so hubs are
  fixed less than their size predicts.
- **MOD-H2 (language family).** The lift is lower in C/C++ than in managed languages.
- **MOD-H3 (interaction).** Age and family interact.

**MOD-H1 is primary.** H2 and H3 are secondary and reported whatever they show.

## Measurement, fixed now

- **Outcome**: `in_degree` AUC minus `loc` AUC, **cascade label**, one snapshot nearest the cut
  (`CUT_Q` of commits), fix window `WINDOW_DAYS` — all exactly as `struct_null.py` already computes them.
- **Floor**: a repo needs `MIN_POSITIVES` positives, as in `hist_replicate`. Repos below it are **excluded
  and listed**, never rescued with a different label.
- **Primary test**: OLS of lift on `old` (binary) + `C_family` (binary), bootstrap CI over repos.
  MOD-H1 is supported iff the `old` coefficient's 95% CI excludes zero.
- **Secondary**: the same with the interaction term; and a sign test (positive vs negative) by cell.
- **Age cut**: first commit before 2006 = old. Fixed now. Repos whose first commit date is implausible
  (imported history, e.g. `go` dated 1972) are **re-dated from the first commit on the current default
  branch**, and if still implausible, excluded and listed.

## What would falsify

If the `old` coefficient's CI includes zero while repos continue to split by sign, **age is not the
moderator** and the split is driven by something else — which is a reportable result, not a failed study. We
report it either way, including a flat null.

## What this does not test

Label quality is unchanged: cascade precision is better than keyword but its **recall remains unmeasured**.
This study is about the *sign* across repos, not the accuracy of any single repo's estimate.

Only `in_degree` is tested. Out-degree and function count lost to LOC in all eight earlier repos under every
label and are not promoted here.
