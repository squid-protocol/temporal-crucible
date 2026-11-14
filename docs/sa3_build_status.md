# SA3 / SA3-CH build status — paused for an independent review (2026-11-14, 8:22 AM Eastern)

**Nothing is scored in either study.** The owner asked for another independent review of the whole system and
its testing apparatus before any further work. This note is the hand-over for that review.

## What exists

| piece | file | state |
|---|---|---|
| Registrations | `docs/sa3_registration.md` (Amendments 1–3), `docs/sa3_change_registration.md` (Amendment 1) | reviewed twice each, reconciled |
| Rescans, full engine output, engine `f71181aae7` | `tools/sa3_scan.py` → `<pilot>/sa3_scans` | 46 of 46 |
| Fix labels, floors, frozen repo list | `tools/sa3_outcomes.py`, `docs/sa3_outcome_marginals.md` | done; 15 drawn + 5 earlier repos |
| Statistics | `tools/sa3_stats.py` | self-test passes on synthetic data |
| SA3 scorer | `tools/sa3_score.py` | `placebo` stage run; `score` stage **locked** (needs three markers in docs/) |
| Nesting depth | `tools/sa3_nesting.py`, `tools/sa3_nest_scan.py` → `<pilot>/sa3_nesting` | measured for the 40 complete repos |
| SA3-CH preparation (git only) | `tools/sa3ch_prepare.py` → `<pilot>/sa3ch_prep` | run for the 40 complete repos |
| SA3-CH scans (earlier snapshot, and t0 again with a fixed hash seed) | → `<pilot>/sa3ch_scans/{t1,t0}` | running when this was written |
| SA3-CH scorer, gates, power | — | **not written** |
| S5 (tree-wide commits left in), S8 (rename-following), "HP without reverts of prior-year commits" | — | **not written** |

## The placebo stage ran, and the validity gate FAILED

`docs/sa3_placebo.json`. Study mean over the 15 drawn repos, HP outcome:

| placebo | mean | 95% range over 200 draws | verdict |
|---|---|---|---|
| path hash | +0.0003 | −0.019 to +0.017 | centred |
| directory hash | +0.0005 | −0.033 to +0.029 | centred |
| block permutation of `in_degree` | +0.0150 | −0.002 to +0.029 | **not centred** |
| block permutation of `struct_branch` | +0.0181 | +0.004 to +0.035 | **not centred** |
| block permutation of `risk_safety_score` | +0.0035 | −0.010 to +0.022 | not centred (mean > 0.002) |
| block permutation of `amplified_cascading_flux` | +0.0122 | −0.005 to +0.030 | **not centred** |

The block-permutation placebo is the real predictor's values shuffled among blocks of 4 LOC-adjacent files. It
is supposed to keep the predictor's relation to size and nothing else. It comes out about +0.015, which is half
the effect the study can detect (about 0.032). **As registered, no SA3 result may be reported as a finding
until this is understood and fixed.**

## Diagnostics run so far — every one scored only shuffled values, never a file's own

`tools/exploratory/sa3_placebo_diag{1,2,3}.py`:

1. **It is not the choice of statistic.** The same shuffled values give about the same positive mean under
   the residualised statistic (+0.014 to +0.017), a ratio-balanced variant, and calipers of 1.25 and 1.15.
   Dividing the count by LOC first does not remove it (+0.013).
2. **It is not that a random shuffle leaves a quarter of files with their own value.** A cyclic shift, where no
   file ever keeps its own value, gives the same (+0.012 to +0.016).
3. **It is not directory clustering through the tie-break.** Breaking LOC ties by a hash of the path instead of
   the path gives the same (+0.017). Only 12% of LOC-adjacent files share a directory.
4. **It decays with distance in the size ordering.** Blocks of 4: +0.017. Blocks of 32: +0.001 to +0.005.
   Shuffling across the whole LOC band: 0.000.

So a file's outcome is predicted, a little, by the structural value of a file of almost exactly the same size
— and not by that of a file merely in the same size band. **The cause is not established.** Candidate
readings, none tested: (a) size still predicts the outcome at a finer grain than a 1.15 caliper controls, and
the neighbour's value is a fine proxy for it; (b) within a block of four, a shift hands one file's real value
to a neighbour that is then paired against it, so the placebo carries the real effect with some sign;
(c) something about how equal-LOC files are ordered.

## A blinding concern, stated plainly

If reading (b) is right, the placebo means above are a function of the real effects, and the direction and
rough size of the real effects could be inferred from them. I do not know that it is right. No real predictor
has been put against an outcome, but these placebo numbers have been looked at, and the diagnostics were chosen
after seeing them. Any change to the placebo or the statistic from here is therefore made with that possible
knowledge and must be justified on synthetic data alone.

## What is paused

Everything except the outcome-blind scans already running. No further diagnostics on real data.
