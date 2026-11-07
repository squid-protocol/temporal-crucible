# WILD — does a model's code handwriting survive inside a shared codebase?

**Status: REGISTERED 2026-11-07, before the scorer exists and before any structure × model statistic is computed.**
Feasibility facts read so far, none of them involving structure:
- main is squash-merged (6,019 single-parent commits);
- single-model `Co-Authored-By` trailers: Claude Sonnet 5.5 on 2,255 commits, Claude Opus 5.5 on 806;
- both models are active from 2026-10-03 to 2026-11-07.

## Why

Two of the program's own results pull in opposite directions:

- **In the lab, models have handwriting.**
  - agent-habits gave three agents identical jobs. 83% of programs' nearest same-job program came from the same model
    (sfs lens).
  - The lattice family mix alone gets 84% (`docs/journal/2026-11-07-agent-code-on-the-lattice.md`). Both are
    exploratory.
- **In GitGalaxy's own history, authorship looked invisible.** FLT found the autonomous fleet vs interactive sessions
  indistinguishable: AUC 0.640, below the within-group placebos (~0.70).

**Hypothesis:** a shared codebase's conventions (house rules, linters, review, existing code to imitate, task assignment)
dominate model handwriting. GitGalaxy's commits name their model in trailers, which allows a direct test inside one
codebase, in one era.

## Units and labels

- **Commits:** first-parent commits on GitGalaxy `main` dated 2026-10-03 .. 2026-11-07 (inclusive), whose
  `Co-Authored-By` trailers name exactly one model: `Claude Sonnet 5.5` or `Claude Opus 5.5`. The label is that
  model. Commits naming both, or neither, are excluded.
- **Functions born:** Python functions *born* in such a commit.
  - A function is born when its qualified name (`Class.method` or `func`) is in the commit's version of a `.py` file
    under `gitgalaxy/` or `tests/`, but not in the parent's version of that file.
  - New files count; renamed files are matched by `git diff -M` and are not births.
  - Parsing uses tree-sitter Python; nested functions are skipped. Functions must have loc ≥ 3.
- **Exclusions:** generated or vendored paths (`gitgalaxy/standards/language_standards/languages/*_generated*`, any
  path with `vendor`, `third_party` or `_pb2`). Commits that add more than 300 functions are excluded as bulk moves or
  imports.
- **Context strata:** directory (the first two path components, e.g. `gitgalaxy/core`, `tests/tools`) × size band
  (log2 loc, integer bins).
- **Cluster:** the commit (functions from one commit share a label).

## Features (per born function, measured in the commit's blob)

- **Lattice:** presence of the 26 lattice signals. Engine `b64f42bf` Python rules on Prism's comment-free code stream,
  mapped to `function_data` column names (as in LAT Amendment 0). Plus the lattice family, rung k and its band.
- **agent-habits-style habits** (tree-sitter on the function text):
  - log loc;
  - has a docstring;
  - comment lines per loc;
  - `return` count;
  - `while` count;
  - call count (fan-out);
  - maximum nesting depth of control blocks.

## Hypotheses

| id | claim | test | bar |
|---|---|---|---|
| **WILD-H1** | **Handwriting survives:** born functions' structure tells Sonnet from Opus beyond context | L2 logistic regression on the features above; 5-fold cross-validation grouped by commit; out-of-fold P(Sonnet). **Stratified AUC** = P(a Sonnet function outscores an Opus function in the same directory × size-band stratum), pooled over strata weighted by the Sonnet × Opus pair count. Null = model labels permuted **across commits within ISO week**, 1,000 draws (refit each time) | stratified AUC ≥ 0.60 **and** permutation p < 0.01 |
| **WILD-H2** | **Context dominates:** two functions from the same directory by different models are more alike than two from different directories by the same model | standardised feature vectors, Euclidean distance; pairs within the same size band; median distance of (same directory, different model) pairs ÷ median of (same model, different directory) pairs; 99% CI by commit-cluster bootstrap (1,000 rounds; up to 200,000 sampled pairs per arm) | ratio < 0.90 **and** 99% upper bound < 1 |
| **WILD-C1** | **Pipeline control:** a random split of **Sonnet** commits into two pseudo-models (within ISO week) is not separable | the H1 statistic on the pseudo-labels | stratified AUC < 0.55, otherwise H1 is void |

**Reading, fixed now.**
- **H1 fails and H2 passes:** the codebase's conventions dominate. A model's handwriting is a lab phenomenon that a
  shared codebase erases.
- **H1 passes:** handwriting survives conventions. Because of the confound below, it is a *model-and-role* signature,
  not proof of the model alone.
- **Both pass:** a signature exists, but context is larger.
- **Neither:** inconclusive about dominance; report the effect sizes.

## Known confounds (stated, not removable here)

- **Role:** Sonnet 5.5 is mostly the autonomous fleet (issue-sized worker PRs); Opus 5.5 is mostly interactive
  or orchestrator work. Model and role are confounded, as era and model were in GG.
- **Task mix:** different kinds of change. Strata control directory and size only.
- **Labels:** trailers record the committing session's model. A squash commit can carry code drafted in an
  earlier session.

## Descriptive (not tested)

- Per-model distributions of the lattice family, rung and habit features.
- The largest standardised coefficients.
- The lab-vs-wild comparison: agent-habits' same-model vs different-model distance ratio (0.32 / 0.62) against the
  wild ratio.

## Disclosure and multiplicity

- H1 and H2 are each tested at α = 0.01; C1 is a validity gate.
- Public outputs are aggregates; no per-commit lists.
- Any deviation is recorded here, dated, before the affected numbers.

## Amendment 1 (2026-11-07, before any WILD statistic was seen)

**The defect.** The scorer's `has a docstring` feature (`habits()`) tested for an `expression_statement` wrapping a
`string`. In the tree-sitter-python grammar in the engine venv, a docstring is a bare `string` child of the function
body, so the feature was constant 0.

**How it was found.** In a separate exploratory script on the same day, which showed 0% docstrings in GitGalaxy code.

**What happened to the run.** The first run (scorer `4da929c`) was stopped during its H1 permutations. It had printed
only progress lines (labelled commits 2,782: Sonnet 2,255, Opus 527; born functions 13,145 from 2,016 commits) and no
statistic.

**The fix.** The detector now accepts either form. Nothing else changed: same features, tests, bars and seed. The
scorer is re-run from the start.
