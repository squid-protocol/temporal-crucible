---
date: 2026-11-11
title: Commented-out code detector, re-checked on the whole fix-event panel
type: exploratory
status: scored
verdict: n/a
theme: comments
ids:
docs: docs/dead_code_panel.md
links: temporal-crucible#118, gitgalaxy#8255
takehome: After gitgalaxy#8255, the engine's commented-out-code rule is about 93% precise across 5 repos' fix-event files (Wave A's 4% was a curl include-comment artefact), so COM-H3 can use it, run directly on git blobs.
---

## Question

Wave A found the engine's `dead_code` rule (`state_graveyard`) about 4% precise on one curl snapshot. After the fix in
gitgalaxy#8255, is it precise enough across the whole fix-event panel to carry a COM-H3 study?

## Why we asked

COM-H3 (commented-out code vs fixes) was blocked on this check (`docs/comment_wave_a.md`, "What this means for
Wave B").

## What we did

- Ran the rule (Prism positional comment stream + the engine rule, as in Wave A) over every C/C++ file version in
  every fix event's parent commit. That is 25,268 events and 46,829 distinct blobs in curl, OpenSSL, harfbuzz, nDPI
  and libarchive.
- Ran it with the engine before and after #8255.
- Hand-judged a seeded random sample of 40 distinct matches per repo.
- No fix class was read: COM-H3 stays unscored. Report: [`../dead_code_panel.md`](../dead_code_panel.md).

## What we found

- **Precision is high.** 186 of 200 sampled matches are commented-out code or prototype notes: **93% [89%, 96%]**.
  Every repo is at 80% or above (curl the lowest).
- **#8255 cut panel matches by only 13%.** Outside curl's `/* for foo() */` include notes, most matches were already
  real.
- **The remaining false positives are block labels** like `} /* if(x) */` (12 of 200), plus 2 prose lines.
- **About a third of the real dead code is commented-out debug printing.**
- **libarchive's nested `test/` directories** slip through a root-level exclusion.

## Take-home

The commented-out-code instrument now works on C. Wave A's 4% was a curl include-comment artefact.

## What it changed

- **COM-H3 can be registered.** It should exclude `*/test/` paths and say whether commented-out debug output counts.
  It can run on git blobs directly; no re-scans are needed.
- **A small engine follow-up for block labels** (skip matches right after `}` or `else`) would remove most of the
  remaining false positives.
