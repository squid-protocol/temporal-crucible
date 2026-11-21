# Function rewrites: what the commit says, what GitGalaxy structure shows, what `ast` shows (2026-11-20, exploratory)

Plan: `docs/self_function_rewrite_plan.md` with Amendments 1-2 (two independent reviews, `rewrites/review_*.md`). Scripts `tools/selfhistory/ast/`, data
`docs/self_evolution/rewrites/`. Nothing here is registered; no claim is confirmatory.

## Data
- Probe v2: 9,443 function events over first-parent engine commits (4,429 body, 3,686 born, 896 signature, 317 deleted, 115 docstring-only).
- Eligible commits (> 0 body/signature rewrite, <= 6 events, not merge, not mechanical subject, not a sweep): 1,055; 1,005 in the agent era.
- Intent coded for all 1,055 from masked PR text (A, "narration") and for 492 from linked issues filed > 24 h before the PR (B, "intent").
  Labels: fix 569, feature 366, refactor 61, other 32, perf 23, unclear 4 (A). PR text and issue text agree on the primary label for 65% of the 492 commits;
  the main disagreement is PR=fix versus issue=feature (57) and PR=feature versus issue=other (40).
- GitGalaxy structure view: the touched files (old and new versions) scanned once per side with the pinned scanner; 98% of events find a function row
  on both sides. Within-file call-graph measures only (the files are scanned in isolation).

## R1: do `ast` deltas tell intent apart beyond where and how big the change is? (locked baseline: size + month + module)
Logistic regression, folds grouped by linked issue, 100 label permutations within module, time-blocked check train < Nov, test Nov.
| text | n | macro AUC change over baseline | permutation p |
|---|---|---|---|
| B (issue intent) | 487 | -0.007 | 0.34 |
| A (PR text) | 1,005 | +0.015 | 0.06 |
Per-class gains are all within +-0.03 except `other` on A (+0.07, n = 24). Perf (22 commits) is too small to test and goes negative on B.
Reading: with intent taken from issue text there is no detectable ast signal over the locked baseline. The PR-text gain, if real, is the narration effect (agents
describe their own diff), and it is small. The baseline alone reaches AUC 0.75 for feature/fix because module and size already say much about intent.

## R2: ast versus GitGalaxy structure (same 995 commits, same folds, same baseline)
| view | B macro vs base | A macro vs base |
|---|---|---|
| ast | +0.018 | +0.001 |
| GitGalaxy structure | +0.026 | -0.005 |
| both | +0.027 | -0.004 |
R2 (ast minus structure) is -0.008 on B and +0.006 on A: no difference. Neither view reads intent from pooled deltas. The owner's expectation
that `ast` would see in-place logic that structure misses is NOT supported at this resolution.

## What each kind of rewrite looks like in ast (descriptive, PR-text intent; share of commits whose pooled delta shows the feature)
| | fix | feature | refactor | perf | other |
|---|---|---|---|---|---|
| commits | 548 | 353 | 58 | 22 | 24 |
| guards added | 20% | 37% | 3% | 18% | 12% |
| nodes grew > 10% | 15% | 26% | 3% | 9% | 8% |
| nodes shrank > 10% | 2% | 1% | 16% | 9% | 0% |
| in place (node change <= 5%) | 67% | 56% | 71% | 64% | 75% |
| loop depth down | 2% | 1% | 3% | 9% | 0% |
| new constants | 9% | 17% | 2% | 5% | 4% |
| median node delta | +34 | +53 | -8 | +22 | +1 |
- Refactors are the one clear signature: they shrink, add no guards, add no constants.
- Features add guards and new constants more often and grow most.
- Fixes look like small in-place edits; two thirds change the function by 5% or less.
- Perf commits do NOT show the textbook signatures: only 2 of 22 lower loop depth; none add set-literal lookups. The ones listed are batching
  (`executemany`), indexing once, memoising, scheduling (largest-first), pool sizing, a threshold on file count and bounded regexes. Those are idioms, not the
  loop/set shapes the extractor looks for, so v1 features are blind to most perf mechanisms. Next features should be idiom counts (cache decorators,
  `executemany`, `bisect`, dict-index builds, `lru_cache`, pool settings), pre-declared from this list only for a NEW set of commits.
- Clustering of ast delta vectors: only k = 3 is stable (ARI 0.92); the clusters are small edits (621 commits), large edits (343) and a 41-commit
  lopsided group (median 79 nodes, 2 events: new rule families). They are size classes, not intent classes. No further patterns were named.

## Limits and departures
- Folds are grouped by linked issue/epic only. The plan's "or shared file" linking makes almost all commits one component, so it is dropped.
- Several coder agents report reading only the first 230-650 characters of long items in their batch (A_01, A_02, A_07, A_08, B_00, B_01, A_10 item 54). The
  second-coder check (blind, 20%, kappa per bucket) is NOT yet run, so label quality is unmeasured; the A/B agreement of 65% is a floor-type indicator.
- Perf n = 22-23 commits: power is too low for any perf claim (Gemini review item 2).
- The structure view is within-file only; call-graph centrality (the earlier speed-step finding) is not in it.
- Pooled commit-level deltas dilute function-level change; a function-level analysis on single-function commits is not run.
- The earlier "232 complexity commits" figure is withdrawn (Amendment 1).
