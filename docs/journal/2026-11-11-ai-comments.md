---
date: 2026-11-11
title: How do declared-AI commits comment?
type: exploratory
status: scored
verdict: n/a
theme: comments
ids:
docs: docs/ai_comments_exploratory.md
links:
takehome: Declared-AI commits don't change how much code is commented on average, because tools pull opposite ways (in harfbuzz and OpenSSL, Claude-assisted commits comment about twice as much as Codex-assisted ones, either side of human commits); what AI consistently changes is style, with longer, more sentence-like comments.
---

## Question

Is AI-assisted coding changing how open-source C projects comment? The owner suspected the commenting culture seen in
the profile study might shift with AI tools. No published study has tied comment culture to explicitly AI-co-authored
commits.

## Why we asked

From the review mining after the comment → defect line closed (CPF). The profile study showed stable, distinct
commenting cultures; AI is the newest thing that could move them.

## What we did

- **Declared-AI commits:** commits whose message names an AI tool in a Co-authored-by / Assisted-by / Generated-by
  line. A bare `Assisted-by: <person>` is human help, as curl uses it.
- **Scope:** found in harfbuzz (~1,400 since 2026-02), OpenSSL (~350), prometheus, redis and nDPI. postgres,
  libxml2, curl and libgit2 are controls.
- **Measures:** comment share, length, prose-likeness, danger and debt wording of the lines each commit adds, for
  45,620 commits since 2024.
- **gitgalaxy:** an all-AI reference (the owner: every commit is Gemini or Claude), kept out of the AI-vs-other
  contrast.
- Outcome-blind. Report: [`../ai_comments_exploratory.md`](../ai_comments_exploratory.md).

## What we found

- **No consistent change in comment amount for AI vs other commits,** or within the same 14 authors (median +0.9%).
- **Tools pull opposite ways.** Claude-assisted commits comment about twice as much as Codex-assisted ones in the
  same repo: harfbuzz 16% vs 7%, OpenSSL 24% vs 10%, with human commits in between.
- **AI comments are longer and more sentence-like** in 3 of 4 adopting repos, and for 10 of 13 authors.
- **Danger wording is slightly higher** in AI commits.
- **No visible project-level culture shift yet,** even in harfbuzz at 85% declared-AI commits.

## Take-home

AI changes how comments are written (longer, more prose) more than how many are written, and the direction of "how
many" depends on the tool.

## What it changed

- Comment signals (danger wording especially) may need a tool-aware reading in the AI era.
- **Candidate registrations:** the Claude-vs-Codex comment gap, and the prose shift within authors, on repos and
  authors that adopt AI next.
