---
date: 2026-11-11
title: Does AI-assisted code break more often? (ARG, living study)
type: confirmatory
status: registered
verdict: pending
theme: comments
ids: ARG-1, ARG-2
docs: docs/arg_hypotheses.md
links:
takehome: Look 1 (2026-11-11): within the same developers and at matched size, declared-AI commits are blamed for later fixes about as often as their other commits (0.96, CI 0.51–1.49); no verdict until a later look.
---

## Question

Are commits that declare AI assistance named as the cause of a later fix (reverted, or cited in `Fixes:`) more often
than the same developers' own commits of similar size?

## Why we asked

The owner asked for the question that matters most about AI-assisted code, built to be updated as AI commits mature.

## What we did

- Registered (owner OK 2026-11-11): [`../arg_hypotheses.md`](../arg_hypotheses.md).
- **Repos chosen by a frozen rule** (heavy declared-AI use, and how often each project names a bug's cause) from a
  17-project survey, so they are not cherry-picked:
  - primary: Linux, LLVM, Mesa, VS Code, FFmpeg, OpenSSL;
  - secondary: Home Assistant, Ruby, harfbuzz, Bun, Node, Deno, CPython, llama.cpp.
- **Re-run any time** with `python tools/ai_regress.py --fetch [--look N]`.

## What we found

**Look 1 (2026-11-11), [`../arg_look1.md`](../arg_look1.md): no verdict yet.**
- **ARG-1 (primary):** 3,162 AI and 117,676 other eligible commits. Within author and size, RR 0.96, 99.8% CI
  [0.51, 1.49].
- **ARG-2 (secondary):** 1.25 [0.19, 12.3].
- **Raw rates mislead.** AI 1.6% vs other 3.7% in the primary repos, which is author and size, not AI.
- Next look: 2027-05-11.

## Take-home

Pending.

## What it changed

Pending.
