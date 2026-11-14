# What this label quality permits, and what it forbids (2026-11-13)

Measured, externally: our fix label has **sensitivity ≈ 0.41** and **specificity ≈ 0.83** (benchmark: TP 3,070,
FP 4,645, FN 4,484, TN 22,968 over 35,167 commits). That is a very noisy binary measurement. What follows is
what that does and does not allow, and it is mostly determined by **where in a study the label sits**.

## The dividing line

Classical measurement-error theory splits cleanly here:

- **Non-differential misclassification** (error independent of the predictor) **attenuates toward the null**.
  Effects shrink, they do not reverse, and with known sensitivity/specificity they can be corrected.
- **Differential and correlated misclassification** — error that depends on the predictor, or shares a source
  with it — **can inflate or reverse**. It is not correctable by sample size.

Ours is the second kind, and provably so. The predictor in HR-1 (prior fix count) and the outcome (later fix)
are **computed from the same noisy label**, so their errors are correlated by construction: a file that
attracts cosmetic, announcement-style commits gets counted on both sides. That is exactly what we watched
happen — pooled lift +0.082 → +0.009 and curl +0.333 → +0.071 when the label changed, with no code change.

## Triage of what we currently hold

| result | does the fix label touch it? | standing |
|---|---|---|
| LAW-2 preferential attachment, 8/8, coverage-robust | **no** | **solid** |
| LAW-5 decay contradicted, 7 of 8 repos | **no** | **solid** |
| LAW-3 / LAW-4 instrument-dominated | **no** | **solid** (negatives) |
| Engine resolution profile, 18 snapshots, 81–99% | **no** | **solid** |
| Label precision 0.27–0.86 per repo; recall 0.41/0.26 | it *is* the label | **solid**, now externally confirmed |
| HR-2 entropy adds nothing over recidivism | both arms share one label | **moderate** — a *relative* comparison, so shared error partly cancels |
| HR-1 recidivism +0.082 → +0.009 | predictor **and** outcome | **troubled** — correlated error, the worst case |
| curl +0.071 on the v3c label | predictor **and** outcome | **troubled**, and the outcome is a 29%-complete, style-selected sample |
| HR-3 function-grain | both | **uninformative**, as pre-registered |

**The pattern is clean: everything that never touches the fix label is in good shape; everything that does is
compromised in proportion to how much it leans on it.** The LAWS structural findings are unaffected by any of
today's label work. The history-predictor findings are the ones to hold loosely.

## What is possible right now

1. **Structure-only studies.** Call graphs, trajectories, LAW-1..5, resolution profiles. No label, no problem.
2. **Within-repo, within-era contrasts** where announcement convention is roughly constant and partly cancels
   as a common factor. Cross-repo and cross-language fix-rate comparisons do **not** get this protection —
   they compare writing conventions as much as code.
3. **High-precision subset studies.** The revert and CVE tiers are near-certain. Small n, clean signal,
   genuinely usable for "what do fixes look like" questions.
4. **Relative comparisons of two predictors on one label** (HR-2's shape). Shared error cancels to first order.
5. **Rank/ordering claims within a repo**, which are more robust than absolute rates.

## What is not possible without more work

- Absolute effect sizes for fix prediction.
- Any claim where predictor and outcome share the label — **which is our headline claim**.
- Cross-language comparison of anything label-derived.
- Severity-flavoured claims: linked data skews to *less severe* bugs (Apache: 63% of minor vs 15% of blockers).

## "Assume the unlabelled pool is x, y, z" — yes, and it is actionable

From the recall sample, the fixes our label misses are concretely: static-analysis finds (`avoid derefencing a
possible NULL pointer`, Coverity CID), ignored return values, busy-loops, library-adaptation repairs. Terse,
internal, no external reporter, no ceremony. The literature adds the complementary skew: linked fixes are
biased toward *less severe* bugs and *more experienced* developers, so the missed pool leans the other way.

This is a **missing-not-at-random** problem, and it has a standard toolkit:

- **Rogan–Gladen correction** — adjusts a prevalence for known sensitivity/specificity. Valid only if the
  error is non-differential, so it is a lower bound on the work, not the answer.
- **Two-phase sampling with a validated subsample** — the right frame. Label everything cheaply, validate a
  stratified subsample properly, and estimate the correction from the second phase. We can build this: the
  strong tiers plus the external corpus are the beginnings of phase two.
- **Inverse-probability weighting** — model P(labelled | author, era, repo, change shape) and reweight. This
  is where the author/time model belongs, and note what it is: **a model of the labelling process, not of
  bugs.**
- **Quantitative bias analysis** — report the effect across a plausible grid of sensitivity/specificity rather
  than one point. Cheap, honest, and we should be doing it already.

## Is the answer just "lots of data"?

**No — and this is the central design point.** Sample size fixes *variance*. Our problem is *bias*. More data
gives a tighter estimate of a wrong number, and adding eras and languages makes it worse by pooling more
labelling conventions into one estimate.

**But the breadth is still the real asset, for a different reason than it first appears.** Variation across
eras, languages and projects is variation **in the labelling process itself** — and that is exactly what makes
the bias estimable instead of invisible. Concretely, it lets us:

- test whether an effect's size tracks label quality across repos. If the lift is large where precision is
  0.27 and small where it is 0.86, the effect is substantially label artefact — **and we have already seen
  this shape**: commons-lang had the worst label and the largest raw lift, and it reversed under cleaning.
- use the high-label-quality repos as an internal validation set for the low-quality ones.
- run the same hypothesis across label definitions and report the spread, which is a sensitivity analysis the
  programme currently cannot do.

So the design is **not** "lots of data". It is **lots of data, plus a validated subsample, plus an explicit
model of who announces fixes** — with breadth used as leverage on the bias rather than as a substitute for
addressing it.
