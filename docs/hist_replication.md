# HR — history predictors on the CGR cohort, registered 2026-11-13 before any run

**What this is.** The program's one cross-repo replicated predictor is **recidivism** (prior fixes predict next
fixes, curl + nDPI, p<1e-4). It is file-grain and rests on two C repos. This registers its extension to the
**eight CGR repos in five languages** — libgit2, PostgreSQL, libxml2, redis (C), prometheus (Go), commons-lang
(Java), sphinx (Python), ripgrep (Rust) — using the quarterly walks and history databases LAWS built.

**Status: REPLICATION / EXTENSION ON SEEN REPOS, never fresh confirmation.** These eight are the CGR cohort and
have already carried CGT/CGN/CGK, LIB, CPF, DRP and CGN-CR. Results here cannot promote a predictor from
"1 repo" to "confirmed"; they can show breadth, or they can falsify. openssl (tc#26) stays the untouched
holdout, and nothing here is run on it.

**Why these repos are nonetheless worth it.** The *time axis* is new. Prior crucible work on this cohort was
snapshot- or pin-based; the LAWS walks carry 626 quarterly snapshots over 1999-2026 with function identity
across them. The trajectory questions have never been asked of these repos.

## HR-1 — recidivism at file grain, eight repos (tc#3, tc#28 base)

**Hypothesis.** A file's count of prior fix commits orders its next-window fixes **better than LOC does**, in
each repo independently.

- **Unit**: a file alive at the cut date, by `lineage` identity (renames followed).
- **Cut**: the date at the 80th percentile of each repo's commit history. Predictors use commits strictly
  before it; the outcome uses commits strictly after.
- **Outcome**: the file is touched by >= 1 `fix` commit in the **24 months** after the cut.
- **Predictor**: count of `fix` commits touching the file before the cut. Registered variants, fixed now:
  raw count, and a 365-day half-life exponential decay.
- **Baseline**: `total_loc` at the walk snapshot nearest the cut. Bots excluded; merges excluded.
- **Primary metric**: **AUC lift over LOC**, per repo. **Margin 0**, positive direction.
- **Secondary, effort-aware**: recall at a **20%-of-lines** review budget, predictor vs LOC.
- **Pass**: lift > 0 in **>= 6 of 8** repos, and the pooled lift's 95% interval excludes 0.
- **Falsified**: pooled interval contains 0, or fewer than 6 of 8 positive.
- **Stated in advance**: with 849 fix commits in commons-lang and far fewer in ripgrep, small repos may have
  too few post-cut positives. A repo with **< 30 positives** is reported `not evaluable` and pooled over, not
  counted as a failure.

## HR-2 — change entropy `HCM1_LD_30` (tc#24) — BLOCKED, data missing

The registered metric is share-weighted, linearly decayed, over **line deltas** in 30-day periods. The history
databases record which files a commit touched (`touch.status`), **not how many lines**. HR-2 cannot run until a
line-delta harvest exists (`git log --numstat` per repo). Recorded here so the gap is visible rather than
silently substituted: **a commit-count entropy is NOT `HCM1_LD_30` and will not be reported as it.**

## HR-3 — function-grain recidivism (tc#28) — BLOCKED, data missing

Needs changed **line ranges** per commit, mapped onto the function spans the walks carry (`func.start_line`,
`func.loc`). The harvest for HR-2 supplies the same input, so HR-2 and HR-3 unblock together.

## What is NOT claimed here

No causal claim; no claim about any language; no promotion of a predictor's confirmatory status. The cohort is
seen, the repos were chosen long ago for convenience, and the bar is replication breadth only.
