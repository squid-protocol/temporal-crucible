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
