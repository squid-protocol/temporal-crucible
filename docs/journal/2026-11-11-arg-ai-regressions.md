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
takehome: Registered as a living study with looks on 2026-11-11, 2027-05-11 and 2027-11-11.
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

Pending.

## Take-home

Pending.

## What it changed

Pending.
