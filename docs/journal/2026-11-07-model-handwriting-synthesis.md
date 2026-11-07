---
date: 2026-11-07
title: Model handwriting: what we know so far (synthesis)
type: program
status: draft
verdict: pending
theme: natural-history
ids: WILD-H1..H2, WILD-C1
docs: docs/agents_lattice_exploratory.md; docs/gg_lattice_exploratory.md; docs/wild_hypotheses.md; docs/gg_hypotheses.md; docs/flt_hypotheses.md
links: squid-protocol/agent-habits; gitgalaxy-population-analyses agent-habits-round3
takehome: AI models leave a consistent structural handwriting that independent lenses detect in the lab (83–84%) and across GitGalaxy's eras (AUC 0.88), with habits that repeat between settings. Whether it survives inside one shared codebase (WILD) decides how far it can go for attribution.
---

# Model handwriting: what we know so far (synthesis)

## Question

Can you tell which AI model wrote a piece of code from its structure alone, without names, comments or metadata? How
strong is the evidence, and how far is it from forensic use?

## Why we asked

Four lines of work on 2026-11-06 / 07 touched the same question from different sides:
- **agent-habits:** the lab study;
- **GG and FLT:** GitGalaxy's own history;
- **agents on the lattice:** exploratory;
- **GitGalaxy eras on the lattice:** exploratory.

This entry puts them side by side, at their evidence levels.

## What we did

No new analysis. This collects the results of:
- agent-habits (registered habits; exploratory identification);
- GG (registered: eras distinguishable) and FLT (registered: fleet vs interactive not distinguishable);
- the two exploratory lattice studies;
- WILD (registered, scored in the companion entry `2026-11-07-model-handwriting-in-the-wild.md`).

## What we found

**Convergent identification** (independent lenses, same conclusion):

| evidence | setting | result | level |
|---|---|---|---|
| sfs structural profile | lab: 3 models × same 10 jobs | same-model nearest neighbour 83% (chance 27%) | exploratory |
| lattice family × rung mix | same programs | 84% (chance 28%); Sonnet 96%, Haiku 79%, Codex 0 of 2 | exploratory |
| head to head (own run vs rival) | same programs | 83–94%; Sonnet vs Haiku as separable as Claude vs Codex | exploratory |
| Gemini-era vs Claude-era functions | GitGalaxy | AUC 0.877 vs drift placebo ~0.7 | **registered (GG)** |
| same, lattice + habits | GitGalaxy | AUC 0.88, 0.86 size-matched; within-Claude drift 0.71 | exploratory |
| fleet (mostly Sonnet) vs interactive (mostly Opus) | GitGalaxy, same era | AUC 0.64, below within-group placebo | **registered (FLT), null** |
| Sonnet 5.5 vs Opus 5.5, matched directory × size | GitGalaxy, same era | *WILD pending* | registered |

**Habits that repeat across settings:**
- **Private helpers:** Claude models write about twice the human rate (lab 34% vs 17–21%; GitGalaxy Gemini → Claude
  32% → 48%).
- **Small, call-heavy functions:** Claude in GitGalaxy (median 35 → 13 lines); Haiku in the lab (many simpler
  functions).
- **Cleaner keyword grammar than human code:** Sonnet and Haiku in the lab, and Claude-era GitGalaxy. Codex is the
  exception: dense, more grammar-breaking.
- **No trivial "brick" functions:** 0% bare one-step functions for every lab model, vs 5–8% for humans.

**Model, not vendor:** Sonnet and Haiku run in the same tool yet differ as much as either does from Codex. Haiku
documents functions more than both rivals in 10 of 10 jobs (registered, confirmed).

**Against it:**
- FLT's same-era null.
- None of the five registered Sonnet-vs-Codex habits passed; the signal is in the overall pattern, not in any single
  habit.
- Codex is barely tested.
- Most lab matches are a model matching its own second run of the same job.

## Take-home

- **Most likely true:** each model writing on its own leaves a consistent, detectable structural style.
- **Not yet shown:** that it survives a shared codebase with house rules, review and task assignment, at an error
  rate you could act on.
- **The likeliest near-term use:** "AI vs human, and roughly which family", at file or PR level, by combining
  signals. Exact per-function model attribution is harder.

*WILD's result will be added here.*

## What it changed

The path to forensic-grade evidence:

| requirement | status |
|---|---|
| holds on fresh code | round 3 registered (90 runs + a new task; lattice lens added as R3-S5) |
| holds inside real codebases | WILD (running) |
| holds across organisations | not started |
| known error rates per function / file / PR | not measured |
| robust to formatters, linters, human edits, disguise | not tested |
| stable across model versions | not tested (GitGalaxy trailers record versions) |
