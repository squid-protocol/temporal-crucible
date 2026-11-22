# Function-rewrite study: what a commit says, what GitGalaxy structure shows, what `ast` shows (DRAFT, unregistered)

Status: exploratory plan written 2026-11-20 BEFORE any rewrite's commit/PR text was read for bucketing. Owner request: take
functions GitGalaxy rewrote, read what the commit/PR claims, measure before/after from two views (GitGalaxy structure
columns; Python `ast`), group into patterns. Needs two independent design reviews before any confirmatory claim (item 15).

## Feasibility (probe, tools/selfhistory/ast/probe.py, data rewrites/fn_events.jsonl.gz)
First-parent commits of engine code (gitgalaxy/ or backend/, no tests/standards/__init__): 9,394 function events:
4,561 body rewrites (same name and signature, `ast.dump` differs), 3,665 births, 870 signature changes, 298 deletions.
1,152 distinct functions have >= 1 body rewrite; 417 have >= 3. 3,986 of 4,561 rewrites move node count <= 20% (in-place
logic change, the case structure measures miss).

## Unit and sample
Unit = one (commit, function) body rewrite. Sampling frozen first: all rewrites of functions rewritten >= 3 times, plus a
random 300 of the rest (seeded); renames matched by qualname only (a rename shows as death + birth, reported separately).

## Three readings per rewrite
A. CLAIM: commit subject/body and the PR description (items.jsonl), coded into claim buckets by a rule list frozen before
   coding (perf/complexity, correctness/edge case, refactor/extract, feature, robustness/guard, regex/table, test/CI).
   A second coder (Gemini) codes a 20% subset blind; agreement reported.
B. GITGALAXY VIEW: the function's before/after GitGalaxy structure row (LOC, complexity, branching, fan-in/out, ...) from
   scanning the parent and the commit with the pinned scanner (localisation scans, light, only sampled commits).
C. AST VIEW: features from the two function bodies: node count, max loop depth, loop count, comprehension count,
   try/except and guard (early return/raise) counts, call count and distinct callees, regex literals + static risk
   (nested quantifiers, alternation), constants changed (numeric/string), `in` tests on list vs set literal, concatenation
   in loops, global/env reads, type-hint coverage, docstring change.
   Diff kinds from a tree edit summary: node types added/removed (the "what changed" vocabulary).

## Questions (exploratory; none is a verdict)
R1. Does the ast feature delta separate the claim buckets (e.g. perf claims show loop-depth or loop-count drops, set
    lookup swaps, hoisted compiles; correctness claims show added guards and constants)? Measure: multinomial or
    one-vs-rest AUC with cross-validation grouped by commit, against a size-only baseline.
R2. Do GitGalaxy structure deltas separate the same buckets? Compare AUC with R1; prediction (owner): structure is blind to
    most in-place rewrites, ast sees them.
R3. Patterns: cluster ast delta vectors (k chosen by stability, not fit); name clusters only after inspection of 5
    members each; report how much of each claim bucket falls in each cluster, and the share of claims whose cluster
    contradicts the claim (e.g. "perf" with no ast-visible cost change).
R4. Claim vs reality: for "perf" claims, tie to the measured speed events (35) and the 232 complexity-naming commits as a
    labelled subset; report the fraction of perf claims with an ast-visible algorithmic change.
R5. Descriptive evolution, no hypothesis: per month, ast feature totals/means over the whole engine (functions, loop
    depth distribution, regex literal count and risk, guard density, hint coverage, constant churn) at the monthly
    snapshots, next to the same GitGalaxy columns.

## Controls
Sizes/tests excluded; tangled commits (> 6 function rewrites) analysed separately and not used for claim coding; mechanical
sweeps (same edit in >= 5 functions) flagged and reduced to one unit; commit-grouped CV; placebo feature (identifier
length) must not separate buckets.

## Prior work check owed before registering
Commit-message-to-change classification (Hindle et al. maintenance activities, Levin and Yehudai), edit-script mining
(GumTree), refactoring detectors (RefactoringMiner), static ReDoS analysers; to be read, not assumed.

---
# Amendment 1 (2026-11-20): independent review by Claude Opus (ast/review_claude.md; Gemini 4 Neon review pending, to be reconciled in Amendment 2)

Review verified the counts (4,561 / 3,665 / 870 / 298; 1,152 and 417 functions; 3,986 within 20%). Corrections and rulings. Where this
differs from the plan above, this governs.

## Facts corrected
- "232 complexity-naming commits" came from my broad message regex (complexity classes, quadratic, linearity, ReDoS, backtracking, in
  subject OR body, incl. test-harness commits); the review's strict `complexit` search finds 34 first-parent commits. The 232 is NOT used
  as a label set. The perf/complexity label comes from the frozen intent coding below.
- 37 of the 52 refinement rows are SLOWDOWNS (cost up). R4 splits speed-ups (about 10-15 with an engine rewrite) from slowdowns
  ("unclaimed cost"); both are case studies, no AUC.
- The probe dropped 67 renamed engine files, counted 108 docstring-only and 45 nested-def changes, ignored decorators, excluded the 870
  signature changes and cut subjects at 100 chars (join must use the full subject). 88% of rewrite commits are agent-written; Mar-Jun
  is human, Oct is 554 agent commits to 3 human.

## Rulings
1. PROBE v2 (ast/probe2.py): follow renames (R/C), nested defs stripped from the parent's body hash, docstring-only as its own kind,
   decorators inside the signature, signature changes kept as a parallel kind (with body_changed flag), full subject stored, merge-of-
   branch commits flagged tangled. All analyses use v2 events.
2. UNIT/SAMPLE: sample COMMITS, stratified era (human / mixed / agent) x module, <= 5 units per function, inverse-probability weights,
   about 400 commits; seed and strata frozen before text is read. Effective n is commits, not units.
3. CLAIM ATTRIBUTION: a unit is coded only if its commit rewrites <= 2 functions, or the text names the function or file; sensitivity
   at cutoffs 1, 3, 6. Tangled = > 6 body rewrites or branch-merge commit or sweep hash (>= 5 units with the same normalised edit script, or
   frozen mechanical subject regex: ruff|lint|format|rename|typing|merge|autofix).
4. CLAIM BUCKETS = INTENT ONLY: fix/correctness, feature/extension, perf (incl. complexity), refactor/cleanup, other. Multi-label allowed
   with a `primary`. Mechanism words stay on the ast side; no regex/table or test/CI bucket.
5. CIRCULARITY CONTROL: intent is coded from (a) the linked issue title+body ("Part of/Fixes/Closes #N") and (b) PR text with a frozen
   mechanism stoplist masked (loop, set, dict, guard, regex, pattern, compile, cache, hoist, early return, try/except, constant, lookup,
   precompute, ...). R1 is reported on both; the gap is the narration effect.
6. ERA: primary analysis = agent era; human era descriptive. A "month + module only" baseline is mandatory.
7. VALIDATION: GroupKFold by FILE, plus a time-blocked check (train earlier, test later). Baselines: full size (n_old, n_new, signed and
   absolute delta, diff lines), file identity + date, month + module. A size-residualised ast model is also reported.
8. PRIMARY STATISTICS (two only): R1 = macro one-vs-rest AUC of the ast model minus the best baseline, permutation test within file
   groups; R2 = R1 minus the same for the GitGalaxy structure view on the SAME folds and SAME units, equal feature budget; Holm over
   the two. Group bootstrap CIs; minimal effect of interest 0.10 (power: perf has ~40-80 commits). Everything else descriptive, no p-values.
9. R2 FAIRNESS: report the share of units with a GitGalaxy function row first; compare only on units where both views exist.
10. PLACEBOS: label permutation within file group, and mismatched-text placebo (claim from a random other commit, same module and month).
    Identifier length is descriptive only.
11. R3: "contradiction" renamed "not ast-visible"; inspect 5 members per cell before naming a cluster; k by stability.
12. CODER RELIABILITY: second coder blind with a different prompt, 20% subset, kappa per bucket (not pooled); rules frozen after a
    20-commit pilot and before main coding. Owner may code a ~50-commit slice (offered, not required).
13. R5: normalise per function and per KLOC; mark the human/agent boundary and big sweeps (ruff adoption, autofix) on every plot.
14. Prior work added: Herzig and Zeller (tangled changes), Hattori and Lanza (commit-size classes), work on faithfulness of
    generated commit/PR text, GumTree / RefactoringMiner as an edit-type cross-check of the ast diff vocabulary.

---
# Amendment 2 (2026-11-20): reconciliation with the Gemini 4 Neon review (rewrites/review_gemini.md)
Probe v2 result: 9,443 events (body 4,429, born 3,686, signature 896, deleted 317, docstring-only 115); 633 events sit on merge commits.

Agreed by both reviewers: commit-level unit, circularity needs an intent-only text source, sweeps and tangling must be removed before
sampling, one pre-declared primary statistic. Where they differ:

| Issue | Claude | Gemini | Ruling |
|---|---|---|---|
| Sampling | ~400 commits, stratified | only ~23 perf-titled commits exist; a 400 sample gives 7-25 perf, minimum detectable effect 0.19-0.30 | **Code ALL eligible commits** (non-tangled, <= 6 events of any kind, agent era primary); no sample, no weights. Per-function cap of 5 units applies only inside the ast model. Power is reported honestly: perf has ~20-45 commits, so R1 for perf is descriptive with CI; macro AUC over the other buckets carries the test |
| CV groups | by file + time block | file groups leak: 37% of commits span files, 114 issues span files; 96% of non-mechanical commits form one component | **Group by connected component** (commits linked by shared issue/epic or shared file, union-find); plus time-blocked split (train Sep-Oct, test Nov) |
| Circularity text | issue text or masked PR | 69% of linked issues contain mechanism words, 38% filed same day as the PR | Primary text = linked issues filed > 24 h before the PR, code spans and symbols stripped, stoplist masked; PR text reported separately as **narration fidelity**, not intent |
| Attribution gate | <= 2 functions or named in text | named-symbol gate biases buckets (feat 59% <= 2 vs perf 83%) | **Drop the named-symbol gate.** Commit-level pooled ast deltas for commit-level claims; function-level claims only for single-function commits |
| Tangling | > 6 body rewrites | 208 commits exceed 6 once born/signature/deleted are counted | Tangled = > 6 events of ANY kind, merge commits, sweep hash, mechanical subject |
| Text export | -- | 21% of PR bodies truncated at 4,000 | Export untruncated commit/PR/issue text |
| Moves | link renames | 21 exact moves, 63 delete+born pairs in one commit | Pair delete+born by normalised body similarity (>= 0.9) and treat as a move, not a rewrite |
| Baselines | three baselines | adaptive best-baseline picking leaks | **One locked primary baseline: size + month + module**, inside nested CV; file-identity and others are labelled exploratory |

Zero-delta rewrites (565) and docstring-only changes are stratified out of R1 and reported on their own.
