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

---

# The same analysis on the CGR cohort (2026-11-13)

Each repo's announcement spread **τ estimated from its own data**, the null simulated at that τ with the
externally measured label error (sensitivity 0.41, specificity 0.83), then compared to that repo's observed
lifts.

| repo | τ | files | null median | null 95th | raw lift | **v3c lift** | verdict |
|---|---|---|---|---|---|---|---|
| commons-lang | 0.40 | 237 | −0.018 | +0.027 | +0.143 | **−0.015** | no positive effect |
| libxml2 | 0.30 | 141 | +0.049 | +0.095 | +0.025 | **−0.010** | no positive effect |
| postgres | 0.50 | 2,228 | +0.038 | +0.056 | +0.110 | **+0.026** | **inside null** |
| prometheus | 0.28 | 113 | −0.062 | −0.026 | +0.009 | **−0.013** | no positive effect |
| redis | 0.32 | 127 | −0.003 | +0.034 | +0.091 | **+0.020** | **inside null** |
| sphinx | 0.43 | 239 | +0.057 | +0.148 | +0.117 | **+0.046** | **inside null** |

**Not one CGR repo clears its own null.** Three have a cleaned lift at or below zero, and the three that are
positive (postgres +0.026, redis +0.020, sphinx +0.046) all sit **inside** what label noise alone manufactures
at their measured heterogeneity. curl, by contrast, clears its null by a wide margin at τ ≈ 0.36.

The measured τ is strikingly consistent across the cohort — **0.28 to 0.50**, curl 0.36 — so the difference
between curl and the eight is **not** that curl has unusually tidy labelling. It is that curl's effect is
roughly three times larger than anything the others show.

## Two things this analysis makes visible that the earlier runs did not

**The null is frequently positive.** At τ ≈ 0.3–0.5 the simulated lift runs from −0.06 to +0.06 depending on
the repo, and for libxml2 and sphinx the *median* null lift is positive (+0.049, +0.057). A small positive
lift is the **expected** output of this measurement under no effect at all. Reporting "+0.02, interval
excludes zero" against a zero null was the wrong comparison; the right null is the repo's own noise
distribution, and it is not centred on zero.

**The raw lifts are not uniformly explained away.** commons-lang's raw +0.143 and postgres's +0.110 exceed
their nulls. But those nulls assume specificity 0.83, and commons-lang's raw label was audited at **0.27
precision** — far worse than the simulation assumes — so for that repo the null understates the artefact. The
honest statement is that the raw column cannot be rescued by this analysis either: its label is outside the
error model the null was built with.

## Where this leaves HR-1

- **curl: survives.** +0.071 against a null whose 95th percentile at the measured τ is around −0.05, and a
  tipping point ~3.5× beyond the measured heterogeneity.
- **CGR cohort: does not survive, and now for a stated reason** rather than merely failing a bar. The pooled
  +0.009 was already "not shown"; this says the per-repo positives are individually inside their own noise.
- **The claim narrows to one repository.** "Recidivism beats size" is defended on curl and nowhere else in
  this bank. That is a much smaller claim than the programme has been carrying, and it is the first one
  standing on an audited label, an external benchmark and a bias analysis at once.

---

# Author-level spread, and what it does to the curl margin (2026-11-13)

The analysis above recorded a limitation: τ was estimated at the **file** level only, and author-level
variation would add to it. `tools/author_model.py` measures that addition.

| component | τ | units |
|---|---|---|
| between **authors** | **0.83** | 70 curl authors with ≥15 commits |
| between **files** | 0.36 | 529 curl files with ≥15 commits |
| **combined** | **0.91** | — a 10.2× spread between a 90th- and 10th-percentile unit |

**Author variation is more than double the file variation**, which is what Bird et al. predicted and what the
earlier figure missed. Some curl contributors with 15–22 commits have an announcement rate of **0.00** — they
never write "fix" — while others sit near 0.50–0.67.

## Re-running curl's null at the honest τ

| τ | null median | null 95th | null max |
|---|---|---|---|
| 0.36 (file only, what was reported before) | −0.086 | −0.053 | −0.012 |
| **0.91 (combined, correct)** | **+0.001** | **+0.036** | **+0.061** |
| 1.00 | +0.020 | +0.062 | +0.098 |
| 1.10 | +0.034 | +0.077 | +0.113 |

**Observed curl lift: +0.071.**

**The result still survives** — at τ = 0.91 the observed lift exceeds even the maximum of 400 null replicates.
But the margin is much smaller than reported earlier. The tipping point moves from τ ≈ 1.25 to **τ ≈ 1.05–1.10**,
so the heterogeneity needed to explain curl's effect away is now only about **1.2× the measured value**, not
the ~3.5× stated above. **That earlier margin was wrong because it used the file-level τ, and this paragraph
supersedes it.**

The honest standing: curl's effect clears its null, and clears it at a realistic τ, but it is no longer a
comfortable margin. A modest further source of announcement heterogeneity — era effects, subsystem effects,
anything not captured by author and file — would close it.

## The audit queue: where to spend expensive reading

The same model says which commits to look at. Rank by **uncertainty**, not size: an unlabelled, small,
non-feature change by an author who never announces is where the cheap label is most likely wrong.

The first cut of this ranking sorted by *most files touched* and surfaced `HTTP/3: add proxy CONNECT`, a
REUSE-compliance sweep and a ternary-spacing pass — large commits that are confidently **not** fixes, from
which a reader learns nothing. Re-ranked to prefer 1–4 files and to push feature verbs down, it surfaces:

```
[0.00 announce, 1 file] ares__send_query() now varies the retry timeout pseudo-randomly to avoid packet loss
[0.00 announce, 1 file] If the server returns garbage or nothing at all ...
[0.00 announce, 1 file] multi: unmark handle as used when no longer head of pipeline
[0.00 announce, 1 file] SNI: set name to custom Host header
```

That is the right population — terse, unannounced, plausibly real repairs — and it is the queue a diff-reading
model or a human reviewer should work, because it is where each judgement buys the most information.

## What is deliberately NOT modelled

**Defect-proneness by author.** "Who writes buggy code" is not identifiable here: author assignment is
confounded with subsystem, seniority, era, review intensity and task difficulty, and the only bug signal
available is the same label whose reliability varies *by author*. Any such number would measure the labelling
process and report it as a property of a person — the exact error this programme spent the day correcting,
with the added problem that it is about people rather than files.

What **is** identifiable, and is what this model provides: announcement behaviour, label reliability
conditioned on author, and a ranked queue for where to spend validation effort.
