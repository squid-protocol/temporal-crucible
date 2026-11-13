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

## HR-2 — change entropy `HCM1_LD_30` (tc#24), operational definition fixed 2026-11-13 before any run

Hassan's History Complexity Metric, the variant the program selected on CVE labels and then validated frozen on
fresh bug labels (pooled AUC 0.868 vs LOC 0.830 on one repo). Unblocked by the line-delta harvest
(`tools/hist_deltas.py`), which supplies the per-file line counts the history DBs lack.

- **Period**: 30 days, tiled backwards from the cut.
- **Change amount** for file *j* in period *i*: `added + deleted` lines, from the harvest, non-merge non-bot
  commits only.
- **Entropy** of period *i*: `H_i = -sum_j p_ij ln p_ij / ln(n_i)`, `p_ij` the file's share of the period's
  changed lines and `n_i` the number of files changed in it. Normalised so a period is comparable to another
  with a different file count; a period with one changed file has `H_i = 0` by definition.
- **HCM1 attribution**: share-weighted, `p_ij * H_i` — the registered variant, not the uniform one.
- **LD, linear decay**: period *i* of *K* (1 = oldest, K = newest, all strictly before the cut) carries weight
  `i / K`, so the most recent period weighs 1 and the oldest ~0.
- **Predictor**: `HCM1_LD_30(j) = sum_i (i/K) * p_ij * H_i`.
- Cut, outcome window, baseline, exclusions, floors and metrics are **HR-1's, unchanged**, so the two are
  directly comparable on the same files.
- **Pass**: AUC lift over LOC > 0 in >= 6 of 8 repos and a pooled 95% interval excluding 0.
- **Also reported, not a bar**: lift over *recidivism*, since the live question is whether entropy adds
  anything to the predictor the program already has.

## HR-3 — function-grain recidivism (tc#28), operational definition fixed 2026-11-13 before any run

Does recidivism sharpen when the unit is a function rather than a file? Unblocked by the harvest's hunk ranges.

- **Unit**: a function identified by `(path, name)` — the LAWS node identity. Overloads and same-named methods
  of different classes in one file merge, and the **merge rate is reported with the result**, because it hits
  exactly the hot functions this test is about.
- **A fix hits a function** when a fix commit's hunk range in the new file overlaps `[start_line,
  start_line + loc)` of a function in that file, taken from the **quarterly snapshot nearest the commit**.
- **Candidates**: functions present in the snapshot nearest the cut.
- **Predictor**: count of prior fix hits. **Baseline**: the function's `loc`.
- **Outcome**: >= 1 fix hit in the 24 months after the cut. Floors, cut and metrics are HR-1's.
- **Pass**: AUC lift over function LOC > 0 in >= 6 of 8 repos, pooled interval excluding 0.
- **The question behind the bar**: file-grain lift is already known (HR-1). HR-3 is worth running only if the
  function-grain lift is **larger**, so that is reported beside it and is the real reading.
- **Stated in advance**: hunk-to-function mapping is approximate — the snapshot is quarterly, the commit is not,
  so a function that moved within a quarter can take a neighbour's hit. This biases toward noise, which makes a
  positive result conservative and a null uninformative.

## What is NOT claimed here

No causal claim; no claim about any language; no promotion of a predictor's confirmatory status. The cohort is
seen, the repos were chosen long ago for convenience, and the bar is replication breadth only.

## HR-1b / HR-2b / HR-3b — the same three with a cleaned fix label, registered 2026-11-13 before the re-run

**Why.** HR-1/2/3 used the history DB's keyword `fix` flag as both predictor and outcome. Measured afterwards,
that label is contaminated and **unevenly so**: commits matching cosmetic markers (javadoc, checkstyle,
formatting, typo, lint) are **41.7% of commons-lang's fix commits**, 19.7% of ripgrep's, and 4-10% elsewhere.
commons-lang carries HR-1's largest lift, so the contamination is concentrated exactly where the effect is
biggest. "Files that keep getting Javadoc touched" is a real thing to predict, but it is not a defect.

**The change, and only this.** Outcome and predictor both become the fix set that survives
`tools/fixlike_v2.drop_reason(..., rules="v3c")`: test/doc-only paths dropped, non-behavioural subjects
dropped (conventional-commit chore/style/docs types, named linters, javadoc/docstring, typo, whitespace,
build-warning, changelog), comment-edit subjects dropped unless the subject is about operating on comments as
content, and a fix word required in the subject. Cut, window, baseline, floors, metrics and repos are
**unchanged**, so b-runs are directly comparable to their originals.

**Honesty note, stated before the run.** FIXLIKE v3c was developed and audited on xc_harvest's `other-fix`
class, where it moved precision 0.38 -> 0.77 outside C. Applying it to the LAWS keyword `fix` flag is an
**adaptation to a different label family and inherits no audited precision**. It is a sharper label than the
raw flag, not a validated one, and results are reported as such.

**What would change the reading.** If a lift survives the cleaning, the original was not an artefact of
cosmetic commits. If it collapses, the predictor was partly predicting housekeeping. Both outcomes are
reported; neither is a reason to pick the more flattering label afterwards. **The raw-label results stay
published beside the cleaned ones.**
