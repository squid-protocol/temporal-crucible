# Does repowise-bench suffer the same label artefacts? (2026-11-13)

`repowise-dev/repowise-bench` is where this programme took the churn/process-predictor idea. Assessed
against everything measured here today, from their `health-defect/BENCHMARK_REPORT.md` and
`agent_defect_labels.py`.

## Where their design is STRONGER than ours

1. **Their label is a structured convention, not free text.** A file is defective if a Conventional-Commit
   `fix:` touched it after T0. That is a declared type, often tooling-enforced, not a regex hunting for the
   word "fix" in prose. Our entire announcement-propensity problem — *who happens to write "fix"* — is much
   weaker against a label people must type deliberately in a fixed position.
2. **They tested label robustness.** Recomputing with AG-SZZ strips 17% of positives (216 → 179) and moves
   mean AUC by ≤0.01 (0.744 → 0.734). They report that leakage-free attribution is **not** the dominant
   accuracy lever, and keep the keyword-calibrated weights rather than the better-looking SZZ fit.
3. **They ship trivial baselines with bootstrap CIs over repos** — the thing we had to be told to do:

   | predictor | ROC AUC |
   |---|---|
   | LOC-only | **0.742** |
   | health (calibrated) | 0.734 |
   | prior defects | 0.644 |
   | churn (commits ≤90d) | 0.629 |
   | random | 0.490 |

   **health − LOC = −0.008 [−0.044, +0.029]** — they state plainly that the score does not beat a line count
   on AUC, and win only on effort-aware Popt (+0.109, CI excludes 0).

4. **They already found and published the size confound.** Within NLOC quartiles the AUC collapses — Q1
   0.600, **Q2 0.488, which is below random** — and they name it "the size confound" rather than burying it.

On the three things that most damaged our own results — no baseline, no label-robustness check, no
within-stratum analysis — **they were ahead of us.**

## The artefact they DO share

**The precision of the `fix:` label was never measured against ground truth.** They tested robustness to
SZZ — but SZZ is a *different derivation from the same label*, so it cannot tell you whether a `fix:` commit
is really a bug fix. The one check that could is their issue-gated subset, and they report it honestly as
unusable: **across all 13 repos only 5 fix commits link to a bug-labelled issue** (2 survive SZZ).

That is the same hole we found in ourselves, and it matters in the same way: their positives count 216 files,
and if `fix:` precision were 0.70 rather than ~1.0 the universe shifts materially. Our measurement of exactly
this quantity ran 0.27–0.86 across repos — on free-text labels, so it is an upper bound on the damage here,
not a direct estimate.

**Their null is `random` (0.490), not a label-noise null.** Today's bias analysis showed that when predictor
and outcome are both read off a noisy label, the manufactured lift is **positive, not zero** — null medians of
+0.157 and +0.142 on two of our repos. Their LOC baseline is the right instinct and absorbs much of this, but
their *process* predictors (co_change_scatter +0.37, change_entropy +0.24, ownership_risk +0.18) are
coefficients beyond size, not tested against a null that models the labelling process itself.

**And their `prior defects` baseline is structurally our HR-1** — prior bug-fixes before T0 predicting fixes
after T0, both from the same label definition. It scores **0.644 against LOC's 0.742**: on their corpus, by
their own numbers, recidivism does **not** beat size. That is independent corroboration of what we found on
the CGR eight, from a different team, corpus and label.

## A selection effect worth naming

Their corpus is Conventional-Commits repos. Zeng et al. (ICSE 2025) measured that **only 3.8% of 3,058
top-starred GitHub projects had adopted CCS by 2023**. So the protection in point 1 is bought by studying a
systematically unusual 4% — more tooling-mature, more automation-heavy, and plausibly more agent-assisted.
Whether their findings transfer to the other 96% is untested, and it is the mirror image of our problem: we
have a weak label on ordinary repos; they have a strong label on unusual ones.

Within CCS there is also still a choice — `fix:` versus `chore:` or `refactor:` for the same change — so
announcement propensity is reduced, not eliminated.

## Convergence

Two programmes, different corpora, different labels, same wall:

- repowise: health − LOC on AUC = **−0.008**; within-band AUC down to 0.488; churn 0.629 and prior-defects
  0.644, both **below** LOC's 0.742.
- us: HR-1 pooled **+0.009** on a cleaned label; HR-2 change entropy **+0.002** over LOC; only curl clears
  its own null.

**Process and history metrics look strong as coefficients beyond size and fail to beat size standalone, in
both programmes.** That convergence is worth more than either result alone, and it is the strongest reason to
trust the finding.

## What I would send them

1. **Measure `fix:` precision directly.** A 30-commit sample per repo, judged from the diff, is a day's work
   and is the one number their robustness check cannot supply.
2. **Replace `random` with a label-noise null** for the process predictors: simulate defects landing by size
   alone, let `fix:` adoption vary by author, and see what lift the pipeline manufactures.
3. **Report the CCS selection effect** against the 3.8% adoption figure — it bounds external validity and
   costs a sentence.

---

# Is it a good system? Is the equation actually good?

## As an engineering artefact: yes, and better practice than most published defect prediction

Leakage-free T0, cross-validated calibration, trivial baselines with bootstrap CIs over repos, within-stratum
analysis, a mixed-effects model separating repo from file, an explicitly published failure mode, and a
validated micro-fix with a null-result CI. Very little in this literature is held to that standard.

**They also found our hierarchical result independently.** A mixed-effects logistic gives a **repo
random-intercept SD ≈ 1.19 and language SD ≈ 1.02 on the odds scale** — baseline defect rates vary between
repos as much as a standardised feature moves within one. Their own words: *"A flat model conflates 'this
repo is buggy' with 'this file is risky.'"* That is the same thing our per-repo nulls said (τ 0.58–1.29), from
a different direction.

## As a predictor: the honest reading of their own numbers

| | AUC |
|---|---|
| LOC-only | **0.742** |
| health (calibrated) | 0.734 |
| health within Q1 (≤28 LOC) | 0.600 |
| health within **Q2 (29–68 LOC)** | **0.488 — inverted, below random** |
| health within Q3 | 0.670 |
| health within Q4 (>162 LOC) | 0.675 |

**The headline 0.73 is mostly the between-band size contrast**, which they say themselves. Within any band
it runs 0.49–0.68. So as a *risk ranker* it is not better than counting lines.

**But on the effort-aware metric it genuinely wins**: health − LOC Popt **+0.109 [+0.039, +0.204]**, CI
excludes zero. That is a different and more useful question — *given a fixed budget of lines to review, how
many defects do you catch?* Ordering by LOC finds defects but makes you read enormous files. Their score
finds smaller risky files, so it is more efficient per line read. **For the actual product use case —
allocating review effort — the score beats the baseline. For "rank files by risk", it does not.**

## Compared to ours

Not the same kind of artefact. They have a calibrated product score; we have law estimators and a label
audit. On the dimensions that overlap:

| | repowise | us |
|---|---|---|
| trivial baselines | **yes, with CIs over repos** | added only today, after being burned |
| label robustness | **yes (SZZ, ≤0.01 AUC move)** | yes (raw vs v3c, and it reversed our result) |
| within-stratum analysis | **yes, published** | no |
| hierarchical repo effect | **yes, measured (SD 1.19)** | yes, as per-repo nulls (τ 0.58–1.29) |
| label **precision** measured | **no** | **yes, 0.27–0.86 per repo** |
| label **recall** measured | no | **yes, 0.26–0.57, three instruments** |
| external benchmark | no | **yes, 35k validated commits** |
| null | `random` (0.49) | label-noise simulation (null medians up to +0.157) |

They are ahead on study design; we are ahead on knowing what the outcome variable actually is.

## Is there a better equation, given what we learned?

**Not a different feature set — a different shape.** Three changes their own data already supports:

1. **Score per repo, not pooled.** They measured repo SD ≈ 1.19 on the odds scale and then shipped a flat
   model anyway. Partial pooling is the standard fix and it is the single largest available improvement.
2. **Ship two scores, which they already concluded.** Size-relative reshaping lifts small bands and Popt
   ≈ +0.05 but costs −0.07 to −0.12 AUC, because big files genuinely carry more defects (42% defect rate in
   the top NLOC quartile vs 12% in the bottom). Removing size discards real signal. So: a discrimination
   score that keeps size, and a cost-effectiveness score that removes it — their conclusion, and the data
   supports it.
3. **Measure the label's precision.** Every coefficient — `co_change_scatter` +0.34, `nested_complexity`
   +0.33, `ownership_risk` +0.29, `change_entropy` +0.18 — is estimated against an outcome of unknown
   quality. Label noise attenuates coefficients **non-uniformly**, so the *ranking* of those features is not
   safe either. Thirty commits per repo judged from the diff would settle it.

**One caution against over-reading the Popt win**: Popt is computed against the same unvalidated label, so it
inherits the same noise. It survives better than AUC because it is a *within-label* comparison against LOC,
where shared error partly cancels — the same reason our HR-2 relative comparison kept moderate standing while
HR-1's absolute one did not.

## Bottom line

**Their system is good at the thing it ships for — ordering review effort — and not better than a line count
at ranking risk.** They know this and publish it. The equation's weakness is not its features; it is that it
is flat where the data says hierarchical, and calibrated against an outcome nobody has validated.
