---
date: 2026-11-11
title: Do AI-assisted commits change structure differently?
type: exploratory
status: scored
verdict: n/a
theme: comments
ids:
docs: docs/ai_structure_exploratory.md
links:
takehome: Declared-AI commits change function shape no more and no less often than other commits (structure stays put), but within the same authors they add more new callees (11 of 13 people), and Codex-assisted changes move shapes more than Claude-assisted ones.
---

## Question

Do AI-assisted commits change code structure (fingerprint shape, lattice family, defensive signals, call
dependencies, footprint) differently from other commits? The program's structure findings had never been split by AI.

## Why we asked

The owner (2026-11-11) asked whether AI commits change the network or structure more often, after the AI-commenting
study found tool-specific comment habits.

## What we did

- Read every function touched by 18,932 commits since 2024, before and after, in harfbuzz, OpenSSL, redis and nDPI
  (adopters) and postgres, libxml2, curl and libgit2 (controls). That is 117,731 function changes, in about 5
  minutes.
- Used the engine's C/C++ rules and LAT's frozen lattice, as in LAT-F, plus tree-sitter callees.
- Compared declared-AI vs other commits within repo, size-matched, within author, and by tool.
- Outcome-blind. Report: [`../ai_structure_exploratory.md`](../ai_structure_exploratory.md).

## What we found

- **No AI effect on shape change.** 20/21/19% of modified functions move shape in AI commits vs 18/24/14% in others;
  median 0 within author. Control repos drift as much between years.
- **AI adds more new callees,** within author: median +0.28 per modified function, 11 of 13 authors.
- **Codex moves shapes more, Claude less,** than the repo's other commits.
- **Guards, branching and footprint vary by project and tool,** not by AI as such.
- **AI-born functions look like human-born ones:** a little smaller, same rung and family.

## Take-home

AI-assisted work keeps code structure where it was; what it changes is how much code calls into other code, and the
tool matters.

## What it changed

- **Candidate registration:** the within-author new-callee increase, on authors and repos adopting AI after today.
- The "structure describes" picture extends to AI-assisted work.
