---
date: 2026-11-07
title: GitGalaxy's own history on the lattice: Gemini vs Claude style, and how functions move (exploratory)
type: exploratory
status: scored
verdict: n/a
theme: natural-history
ids:
docs: docs/gg_lattice_exploratory.md; docs/gg_hypotheses.md
links:
takehome: Gemini-era GitGalaxy functions were long, nested, inline-commented and public; Claude-era ones are short, call-heavy and twice as often private helpers (as in the lab). Functions rarely change shape (88% never; 2.8% of weeks), and when they do it is one signal at a time, mostly growing.
---

# GitGalaxy's own history on the lattice (exploratory)

## Question

How did code written in GitGalaxy's Gemini era differ in *style* from Claude-era code, and how do functions move on the
lattice week by week?

## Why we asked

- GG showed the eras are structurally distinguishable (AUC 0.877) but not how.
- The agent-habits lab found Claude models favour private helpers.
- LAT described movement on quarterly C snapshots; GitGalaxy has weekly ones.

## What we did

- **Data:** GG's 32 weekly scans of the `gitgalaxy/` package (engine `32619e4a5`) and GG's binding eras.
- **Births:** functions born per era, compared on lattice family and rung, grammar fit against population Python,
  holes and attractions, and habits measured from source with tree-sitter.
- **Classifier:** era classifier grouped by file, size-matched, with a within-Claude drift reference.
- **Movement:** functions tracked week to week through file moves.

## What we found

**Style.** Gemini era (213 born functions) vs Claude era (2,574):

| | Gemini era | Claude era |
|---|---:|---:|
| median lines | 35 | 13 |
| nesting depth | 2.3 | 1.6 |
| comment lines per line | 0.07 | 0.01 |
| calls per 10 lines | 4.4 | 5.4 |
| returns | 1.5 | 2.0 |
| public/general (F7) | 68% | 51% |
| private helpers (F8) | 32% | 48% |
| grammar fit percentile | 53% | 62% |
| grammar-breaking (bottom 10%) | 11.3% | 6.7% |
| docstrings | 68% | 71% |

- Claude-era code has more private helpers (lab: Claude models 34% vs population 17–21%), fits the grammar better
  and breaks it less.
- Docstrings are about equal.
- The classifier separates the eras at AUC 0.878, 0.860 size-matched. Within-Claude drift (early vs late Claude) is
  0.71.

**Movement.** 18,144 function-weeks; 3,215 functions.
- A function's shape moved in 2.8% of weeks. 88% of functions never moved (61% of those living at least 8 weeks).
- Moves are 75% single-signal; climbs 42%, descents 22%, swaps 36%.
- Family changes are only 4% of moves (C repos: 11%).
- Mean rung grows slowly with age: 7.85 in week 1, 8.80 by week 20.
- Gemini-era weeks were almost all climbs (46 : 9); Claude-era weeks more balanced (163 : 104).
- The commonest moves add or drop imports, comprehensions and casts.

## Take-home

- The Gemini → Claude switch shows up as a different way of building functions: small, call-heavy private helpers
  instead of long, nested, commented public functions. It is consistent with the lab's Claude tell, but here it is
  confounded with tooling, workflow and codebase maturity.
- Functions are born with nearly their final shape and change rarely, one signal at a time.

## What it changed

- **Supports the WILD question:** a model's style is visible across eras of a codebase. Whether it survives *within*
  one era between models is what WILD tests.
- **Measurement fix:** this analysis exposed a docstring-detector bug (bare `string` docstrings in tree-sitter-python).
  It was fixed here and recorded as WILD Amendment 1 before any WILD statistic was seen.
