Review of [self_function_rewrite_plan.md](file:///srv/storage_16tb/projects/temporal-crucible-wt-selfscan/docs/self_function_rewrite_plan.md) (incl. Amendment 1) against [fn_events.jsonl](file:///srv/storage_16tb/projects/gitgalaxy-history/ast/fn_events.jsonl) (4,561 body events; 1,429 commits) and [items.jsonl](file:///srv/storage_16tb/projects/gitgalaxy-history/gh/items.jsonl) (6,613 PRs; 2,166 issues):

1. **Grouped-CV leakage:** File-grouped CV leaks commits across folds—535/1,429 (37.4%) commits span >1 file (32.0% of ≤6; 68.1% of events), 114 shared issues span >1 file (507 commits; #4270 has 40), and 96.4% (1,191/1,236) of non-mechanical ≤6 commits form one file-commit component.
   **Fix:** Make **commit** the unit, group CV by linked-issue/epic ID (fallback: commit), plus a Sep–Oct → Nov time-blocked split.

2. **Underpowered `perf` / macro-AUC:** Only 23/1,429 commits have perf/complexity titles (21/958 = 2.2% in Sep–Nov ≤6, burst-clustered e.g. 2026-09-18), not 40–80. A 400-commit sample yields ~7–25 `perf` commits (SE 0.06–0.10; 80%-power Holm MDE ≈ 0.19–0.30 vs 0.10 target).
   **Fix:** Code all ~958 non-mechanical ≤6 agent-era commits (no 400 cap) and report prevalence-weighted alongside macro OvR AUC.

3. **Text–AST circularity:** Linked issues aren't mechanism-free: 69.0% (741/1,074) contain mechanism words, 17.6% code/`def`, 12.6% function names, and 38.3% were filed same-day as the PR; stoplist masking misses implicit terms (`quadratic`, `split`).
   **Fix:** Restrict low-circularity coding to issues filed >24h pre-PR with code/symbols stripped; frame PR-text AUC as narration fidelity.

4. **Unit mismatch & hidden tangling:** Copying commit labels onto `(commit, fn)` rows mislabels helper edits; 208 ≤6-body commits exceed 6 total events (`born`+`signature`+`deleted`), and 169 hot functions (>5 rewrites) hold 59.1% of events.
   **Fix:** Pool AST deltas to commit level (single-function commits for function-level claims) and cap tangling on all event kinds ≤6.

5. **Sampling bias & missing/truncated text:** 210/1,429 (14.7%) commits lack a matched PR (58/58 Mar–Jun); 261/1,219 (21.4%) matched PR bodies truncate at 4,000 chars. Ruling 3’s `≤2` or named-symbol gate biases buckets (`feat` 59% ≤2 vs `perf` 83%) and verbose PRs.
   **Fix:** Export untruncated commit/PR/issue bodies, drop the named-symbol gate, and code all non-tangled commits.

6. **Confounds (sweeps, renames, diff/message noise):** 78 mechanical-subject commits (650 events), 33 ≥5-identical-delta sweeps (773 events), 565 (12.4%) zero-delta rewrites, 486 (34%) 100-char truncated subjects, and 40 same-file / 23 cross-file `deleted`+`born` commits (21 exact moves).
   **Fix:** Deduplicate sweeps via AST-diff hashes pre-sampling, link `deleted`+`born` pairs by body similarity, and stratify zero-delta/docstring edits.

7. **Multiplicity & adaptive baseline leakage:** Picking the "best baseline", tuning models, and branching across text sources/cutoffs/residualizations inflates ΔAUC.
   **Fix:** Pre-register one locked baseline (size + month + module) inside nested CV; label all variants exploratory.
