---
date: 2026-11-07
title: Agent-written code on the lattice and the keyword grammar (exploratory)
type: exploratory
status: scored
verdict: n/a
theme: fingerprints
ids:
docs: docs/agents_lattice_exploratory.md
links: squid-protocol/agent-habits; gitgalaxy-population-analyses agent-habits-round3
takehome: AI coding agents skip the tiny "brick" functions humans write (0% bare one-step vs 5–8%), the Claude models write far more private helpers, Codex fits the human grammar worst, and a program's lattice family mix alone identifies its model 84% of the time (chance 28%).
---

# Agent-written code on the lattice and the keyword grammar (exploratory)

## Question

Where does AI-agent code sit on the function-shape lattice and against the human keyword grammar, and does the lattice carry
the "model handwriting" the agent-habits study found?

## Why we asked

agent-habits found that each model has a structural handwriting: 83% of programs' nearest same-job program came from the
same model. The lattice and grammar work offered a second, independent lens on the same programs.

## What we did

- **Data:** the 60 agent-habits programs, rescanned with the population engine (`b64f42bf`) so comparisons are like for
  like.
  - Models: Claude Code + Sonnet 5.5 (two rounds), Claude Code + Haiku 5.5 (two rounds), Codex.
  - Jobs: chess and SAT × C, Java, Python, Rust, COBOL.
  - 58 programs had functions in their language; 1,433 functions with loc ≥ 3.
- **Lattice:** functions placed with the frozen lattice (family, rung). Comparison: a 150k-function population sample per
  language, matched to each model's language mix.
- **Grammar:** fit percentile within population strata (language × size × signal count).
- **Holes and attractions:** rates of the avoided and favoured pairs.
- **Identification:** nearest program in the same task × language by family × rung mix, tested with a within-cell label
  permutation.

## What we found

- **No bricks:**
  - F6 (bare one-step) is 0% for every model vs 5–8% in the population.
  - Rung k ≤ 3: Sonnet 9%, Haiku 4%, Codex 5%, vs 19%, 12% and 20% for the matched population.
- **Private helpers:** F8 is 34% for Sonnet and Haiku vs 17–21% in the population. Codex is 7% vs 6%, and is instead
  heavier in F7 public/general (58% vs 48%).
- **Grammar fit:**
  - Sonnet median percentile 54% and Haiku 50%; both break the grammar less than human code (bottom 10%: 7.0% and 7.3%).
  - Codex median 32%, with 12.1% grammar-breaking.
- **Holes:** agents avoid the human holes even more (public + private 0.0–0.5% vs 2.0–3.1%). The Claude models pair
  concurrency with locks more than the population does (1.0–1.1% vs 0.3–0.4%).
- **Identification:** the family mix alone finds a same-model nearest neighbour in **42 of 50 (84%)**, chance 28%,
  permutation p 0.0005. The sfs structure lens got 83%.

## Take-home

- Model handwriting is visible in *which kinds of functions* a model builds, not only in fine-grained structure.
- Agents write fewer trivial functions than humans; the Claude models favour private helpers.
- All exploratory, on programs that already informed agent-habits. Chess and SAT solvers are not typical open-source
  code, so the population differences mix authorship with task.

## What it changed

- **Round 3:** the lattice lens is registered for round 3 as a secondary claim, before any round-3 run (dated addendum
  in gitgalaxy-population-analyses `agent-habits-round3/`).
- **Next:** led directly to the WILD registration: does model handwriting survive inside a real shared codebase
  (GitGalaxy's own history, labelled by model trailers)?
