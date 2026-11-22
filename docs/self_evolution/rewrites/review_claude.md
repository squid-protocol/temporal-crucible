# Independent design review (Claude): self_function_rewrite_plan.md

Reviewer: Claude (Opus), 2026-11-20, read-only. Reviewed the plan, `ast/probe.py`, `ast/fn_events.jsonl`,
`gh/items.jsonl`, `mirror.git` and `speed/refined*.jsonl`. I worked out every number below from the data myself; the
scripts were one-off and have not been kept.

## Facts checked against the data

| Plan claim | Check | Result |
|---|---|---|
| 9,394 events: 4,561 body / 3,665 born / 870 signature / 298 deleted | count kinds | matches |
| 1,152 functions with >= 1 rewrite, 417 with >= 3 | group by (file, fn) | matches; the 417 own **3,631 of 4,561** rewrites (80%) |
| 3,986 rewrites move node count <= 20% | recomputed | matches (565 have zero node delta) |
| 35 measured speed events | distinct `found` SHAs with class LOCALISED in refined + pass2 | matches (35 commits, 52 rows); **37 of 52 rows are slowdowns** (`down: false`); 29 of 35 commits have an engine body rewrite, 7 of those are tangled (> 6) |
| 232 complexity-naming commits | regex `complexit` | **not reproduced**: 34 first-parent commits (20 with engine rewrites), 62 lines across all refs, 51 PRs and 112 issues+PRs. Cite the source or correct the figure |
| commit -> PR join via `(#N)` | full subject (not the 100-char `subj` in fn_events) | 1,323 of 1,429 rewrite commits (93%) and 3,827 of 4,561 rewrites (84%) join to a PR whose body is >= 200 chars after stripping the template and checkboxes. 56 commits (444 rewrites) have no PR, 28 (256 rewrites) have an empty or template-only body, mostly in the early human era. 1,148 commits link an issue (`Part of` / `closes` / `fixes #N`) |

Other facts that affect the design:
- **Authorship:** 1,259 of 1,429 rewrite commits (88%) carry Claude/agent markers in the commit or PR text. By month the
  human-only commits are 2026-03 to 06, July is split 62/59, and Oct is 554 AI to 3 human.
- **Tangled commits:** 131 commits with > 6 rewrites hold 1,796 rewrites (39%). Hot functions (>= 3 rewrites) with
  tangled commits removed: 2,296 units, 1,195 commits, 385 functions.
- **Concentration:** the top 15 functions supply 26% of the hot stratum (`RecordKeeper.record_mission` alone has 115).
- **Probe artefacts:** 108 body rewrites change only the docstring, 45 change only inside a nested def (so they are
  counted twice, once in the parent), and 486 subjects are cut at 100 chars.
- **File renames:** `--name-status` with git 2.43 reports renames as `R###`, and the probe keeps only `A/M/D`. 67 engine
  file renames are silently dropped, for example `physics/signal_processor.py -> metrics/signal_processor.py` (R086).
  Edits made in those commits are lost, and function histories are split across paths.
- **Sweeps:** 58 commits with mechanical subjects (ruff, lint, format, rename, typing, merge) hold 561 rewrites. 33
  commits have >= 5 rewrites sharing an identical node delta. The single "Merge pull request #87" diff accounts for 130
  rewrites.

## Ranked problems and minimal fixes

1. **Circularity: the claim text is the agent's own narration of its diff.** 88% of rewrites come from AI agents whose
   PR bodies routinely describe the mechanism ("add a guard", "hoist the compile", "set lookup", "early return"). A rule
   list that codes "robustness/guard" or "regex/table" from that text, scored against ast guard and regex-literal
   counts, measures how faithfully the agent describes its edit, not whether a stated intent matches the code. R1/R3
   AUCs will be inflated by construction.
   *Fix:* code claim buckets from **intent text only**: the linked issue title and body (1,148 commits link one), or
   the PR text with a frozen mechanism stoplist masked first (loop, set, guard, regex, pattern, compile, cache, hoist,
   early return, try/except, constant, ...). Report R1 both ways. The gap between the two is itself the narration
   effect.

2. **Era and author confound.** The human-to-AI shift (Mar-Jun human, Sep-Nov AI) coincides with changes in PR
   template, message length, module mix (det/cics translation code arrives late) and coding style. Any separation
   between buckets can come from era alone.
   *Fix:* add `era` (human / mixed / AI) as a stratum. Make the primary R1 analysis AI-era only (the bulk of the data)
   and report the human era descriptively. Add a "month + module only" baseline model.

3. **CV leakage: grouping by commit is not enough.** 385 functions supply 2,296 units, some functions are rewritten
   59-115 times, and bucket correlates with file (translator files mean feature/correctness, recorders mean
   feature/refactor). Commit-grouped folds put the same function, file and month in train and test, so the model can
   learn identity rather than edit type.
   *Fix:* use GroupKFold on **file** (or top-level module) with a time-blocked check (train on earlier months, test on
   later ones). Add a "file identity + date only" baseline. The ast model must beat this baseline, not only the
   size-only one.

4. **Sampling is near-census and dominated by hot functions.** "All rewrites of functions with >= 3 rewrites + 300
   random" is about 3,931 of 4,561 units. It is too many to hand-code and is weighted toward the 15 hottest functions.
   Units within a commit share a single claim text, so the effective n is the number of commits (about 1,200), not the
   number of units.
   *Fix:* sample **commits**, stratified by era x module, with at most 5 units per function and inverse-probability
   weights. About 400 commits coded is enough (see item 7). Freeze the seed and strata before reading any text.

5. **Probe defects bias the unit.**
   - (a) File renames are dropped. Add `R`/`C` handling (old path from `p[1]`, new from `p[2]`) and key function
     lineage on (path-lineage, qualname).
   - (b) Docstring-only rewrites (108) should be removed or put in their own bucket.
   - (c) Nested-def changes (45) are double counted. Hash the body with nested defs stripped.
   - (d) Decorator changes are invisible. Add the decorator dump to the signature or as a separate field.
   - (e) Signature changes (870) are excluded, which removes the largest rewrites. Add them as a parallel unit kind
     (same name, signature plus body changed) rather than dropping them.
   - (f) Store the full subject and body, and join PRs on the full subject.
   - (g) Flag merge commits whose second parent is a branch ("Merge pull request #87", 130 rewrites) as tangled.

6. **The buckets mix intent and mechanism, and they are not exclusive.** "regex/table" and "robustness/guard" are
   mechanisms, and "regex/table" is especially loaded because GitGalaxy's engine *is* a regex/table scanner (regex
   keywords hit 371 rewrite commits). "test/CI" cannot apply once tests are excluded. A single fix often carries
   several claims.
   *Fix:* use intent buckets only (fix/correctness, feature/extension, perf, refactor/cleanup, other), allow
   multi-label coding with a "primary" field, and keep mechanisms on the ast side. Drop test/CI.

7. **Power is thin for the interesting buckets.** Perf vocabulary appears in only 121 rewrite commits (393 rewrites),
   and "complexity" in 22. Removing tangled commits, sampling, and grouping by file leave perhaps 40-80 perf commits. A
   one-vs-rest AUC at n_pos about 50 has a 95% CI of roughly +/- 0.08-0.10, so "beats the size baseline" needs a gap of
   at least 0.1 to be visible. R4's labelled subset is 35 speed commits, but most are slowdowns that no commit claimed,
   so speed-up commits with an engine rewrite number about 10-15.
   *Fix:* report CIs with a group bootstrap, pre-state a minimal effect of interest, and pool perf with complexity.
   Treat R4 as case studies, and split speed-ups from slowdowns (slowdowns are "unclaimed cost", a separate and useful
   question).

8. **Multiplicity.** 7 buckets x 2 views x ~20 features, plus cluster-by-bucket tables and a k search.
   *Fix:* set one primary statistic per question (R1: macro one-vs-rest AUC minus the best baseline, tested by
   permutation within the file group; R2: the AUC difference R1 - R2 on the same folds) and apply Holm across those
   two. Everything else is labelled descriptive, with no p-values.

9. **R1 vs R2 is not a fair comparison.** The ast view has about 20 features and the structure view about 6. The
   GitGalaxy per-function match rate (nested defs, methods, renamed functions) is unknown, and a missing row would
   count against structure.
   *Fix:* report the match rate first, compare on the units where both views exist, and use the same learner with
   nested feature selection or an equal-k feature budget.

10. **The size confound is underspecified.** Most ast counts scale with node delta.
    *Fix:* the size baseline should hold n_old, n_new, signed and absolute delta, and diff line counts. Add a
    size-residualised ast model.

11. **The placebo is weak.** Identifier length may genuinely track feature/refactor work, so a failure would be
    ambiguous.
    *Fix:* use a label permutation within the file group, plus a mismatched-text placebo (pair each diff with the claim
    from a random other commit in the same module and month). Keep identifier length only as a descriptive check.

12. **Claims are attributed to a function when the claim belongs to the commit.** A commit-level claim is copied to
    every unit in the commit. The "> 6" cut is arbitrary, and even 2-6 functions dilute the claim.
    *Fix:* code a unit only when the commit touches 1-2 functions or the text names the function or file. Report a
    sensitivity analysis with cutoffs of 1, 3 and 6.

13. **Sweep detection.** "Same edit in >= 5 functions" needs an operational definition.
    *Fix:* hash a normalised edit script (GumTree-style action types plus inserted node types) per unit, and flag
    commits where >= 5 units share a hash or the subject matches a frozen mechanical regex (58 commits, 561 rewrites,
    found by subject alone).

14. **R3 "contradiction" overreaches.** "Perf claim with no ast-visible cost change" is not a contradiction. The cost
    may live in a callee, in data, in regex semantics, or in caching.
    *Fix:* rename it to "not ast-visible". Validate only against measured speed events, and inspect 5 cases per cell
    before naming any cluster.

15. **Second coder.** Gemini coding Claude-written text on a 20% subset is the only reliability check.
    *Fix:* add one human-coded slice (about 50 commits) or a second model coding blind with a different prompt. Report
    kappa per bucket, not pooled, and freeze the rules after the pilot and before the main coding.

16. **R5 drift.** The engine grows several-fold. Normalise per function and per KLOC, and mark the human/AI boundary
    and big sweeps (ruff adoption, the py310 autofix) on the plots so steps are not read as trends.

17. **Prior work to add.** Herzig and Zeller on tangled changes; work on commit-message and PR-description generation
    and its faithfulness (relevant because the text is agent-written); Hattori and Lanza on commit-size
    classification. Keep RefactoringMiner (Python port) or GumTree as an edit-type check on the ast diff vocabulary.

## Bottom line
The study is feasible: the PR join works for 84% of rewrites. The main threat is circularity (problems 1 and 6) plus
the AI-era confound (2), and after those, identity leakage in CV (3). Fix those four, sample commits rather than units,
and repair the probe (5) before any claim coding starts.
