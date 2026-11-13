# Quantitative bias analysis of HR-1 on curl (2026-11-13)

HR-1 reads its predictor (prior fixes) and its outcome (later fixes) off the **same** noisy label, so their
errors are correlated by construction. The question is therefore not "is the label noisy" — measured
externally at sensitivity 0.41 / specificity 0.83 — but **how large a lift that noise manufactures when the
true effect is zero.**

## The null being simulated

- True fixes land on files **in proportion to size and nothing else**. By construction prior fixes carry no
  information about later ones beyond what LOC already carries: the true lift is **zero**.
- Each file carries an **announcement propensity** `a_i`, lognormal with spread **τ**, constant across the
  cut. This is the whole mechanism: some files, authors and subsystems say "fix" and some do not, and the
  habit persists.
- A true fix is observed with probability `sensitivity · a_i`; a non-fix is observed as a fix with
  probability `(1 − specificity) · a_i` — the lint/javadoc/formatting churn the recall audit found,
  concentrated in the same files.

HR-1 then runs unchanged. Any lift it reports is pure artefact.

## What the null produces

| τ (announcement spread) | median lift | 95th pct | max |
|---|---|---|---|
| 0.00 (non-differential) | −0.109 | −0.077 | −0.041 |
| 0.25 | −0.098 | −0.067 | −0.035 |
| 0.50 | −0.068 | −0.031 | +0.007 |
| 0.75 | −0.028 | +0.009 | +0.044 |
| 1.00 | +0.020 | **+0.063** | +0.098 |
| **1.25** | +0.056 | **+0.101** | +0.129 |
| 1.50 | +0.094 | +0.140 | +0.164 |

**Observed HR-1 lift on curl: +0.071.**

With no heterogeneity (τ=0) the null produces a **negative** lift: non-differential noise attenuates the
predictor *below* size, exactly as theory says, and cannot invent a positive effect. The manufactured lift
only becomes positive once announcement behaviour varies strongly between files.

**The tipping point is between τ = 1.00 and τ = 1.25.** Below it the observed effect exceeds the 95th
percentile of the null; above it the effect is inside what noise alone can produce.

## Is the tipping point reachable? Estimated from curl's own data: no

Measuring the per-file labelled-fix rate across 529 curl files with ≥15 commits, and subtracting the binomial
sampling component by the delta method:

- mean labelled-fix rate per commit: **0.280**
- observed sd of log(rate): 0.444; sampling component 0.265
- **estimated τ ≈ 0.36**, a **2.5×** spread between a 90th- and a 10th-percentile file

The tipping point (τ ≈ 1.25) is a **~25× spread** — roughly **3.5× more heterogeneity than curl actually
shows.** At the measured τ ≈ 0.36 the null's lift is around −0.08, and the observed +0.071 sits far outside it.

## Reading

**The curl result survives the bias analysis.** The announcement heterogeneity needed to explain +0.071 as
pure label artefact is several times larger than the heterogeneity curl exhibits. This is the first result in
this programme to be *defended* by a bias analysis rather than demolished by one, and it is the right
treatment for a claim whose predictor and outcome share a noisy label.

## Limits, which are real

- **τ is estimated from the same label whose error is being modelled** — somewhat circular. It captures
  *file-level* heterogeneity only; author-level and era-level variation would add to it, and Bird's work says
  author-level variation is exactly where bias lives. The true τ is therefore **above** 0.36, and the margin
  to 1.25 is smaller than it looks.
- The null assumes true fixes follow `LOC^1`. A different size relationship changes the baseline.
- 451 files enter this frame against HR-1's 1,020, because a file must be touched both before and after the
  cut to simulate.
- This defends **curl only**. The CGR cohort's pooled +0.009 is not defended by anything here, and should
  still be read as "not shown".
