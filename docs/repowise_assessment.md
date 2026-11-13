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
