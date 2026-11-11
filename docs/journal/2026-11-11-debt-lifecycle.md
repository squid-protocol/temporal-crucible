---
date: 2026-11-11
title: TODO/FIXME debt in C: how long it lives and what repays it
type: exploratory
status: scored
verdict: n/a
theme: comments
ids:
docs: docs/debt_lifecycle_exploratory.md
links:
takehome: In nine C projects about three quarters of TODO/FIXME/XXX comments are eventually removed, but projects range from 38% to 98% and from months to decades; about half are repaid by their own author, and debt is repaid in clean-ups rather than fixes (fix commits repay it at about half their share of commits).
---

## Question

Self-admitted debt comments (TODO, FIXME, XXX, HACK): how long do they live in C projects, who removes them, and what
kind of commit repays them? The SATD survey literature names repayment as the least-studied part.

## Why we asked

After the comment → defect line closed (CPF), the owner chose to study comments as a record of how people work. This
is option 2 from the review mining: SATD repayment, in C, at scale.

## What we did

- Followed every debt comment line through the full non-merge history of nine repos: about 8,500 items, in 94 s.
- Moves, rewordings and file renames are handled, so they don't count as removals.
- Part B read fix labels for the five core repos only; the four unseen repos stay unread for a registration.
- Report: [`../debt_lifecycle_exploratory.md`](../debt_lifecycle_exploratory.md).

## What we found

- **About 74% of debt comments are eventually removed,** but projects range from 38% (nDPI) to 98% (curl). Median
  life runs from 0.1 years (harfbuzz) to 20.7 years (libxml2).
- **About half are repaid by their own author;** more in single-maintainer projects.
- **`XXX` lives longest.**
- **Fix commits repay debt at about half their share of commits** in every core repo, and CVE fixes almost never do.
- **Cross-check:** open debt at HEAD matches the independent profile study in 8 of 9 repos.

## Take-home

Debt comments behave like a project's housekeeping habit. They are paid down in clean-ups, not in bug fixes, and how
fast depends on the project.

## What it changed

- **Candidate registration:** "fix commits repay debt less often than their share of commits", tested on the unread
  libgit2, libxml2, postgres and redis, with commit-level counting and a bootstrap.
