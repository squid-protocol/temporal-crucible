---
date: 2026-11-07
title: What the signals actually count: the signal-name audit and engine fixes
type: engine-finding
status: scored
verdict: n/a
theme: engine
ids: 
docs: docs/signal_name_audit.md
links: gitgalaxy#8009; gitgalaxy#8010; gitgalaxy#8011; gitgalaxy#8012; gitgalaxy#8016; gitgalaxy#8024
takehome: Eleven signal names misdescribed their rules (struct_linear counts return/def/void keywords, not linear code), several tokens were counted by two rules, and 36 function columns are always zero. Display names and rule fixes went into the engine.
---

# What the signals actually count: the signal-name audit and engine fixes

## Question

Do the engine's signal names mean what this program has been reading them as?

## Why we asked

Reading real functions next to their fingerprints showed `struct_linear` matching `return` and `export`.

## What we did

Traced every function signal column to its engine rule and listed real matches on the comment-free code stream. A sweep found identical spans counted by two rules, and the population DB was used to find columns that are zero for every function.

## What we found

- 11 misleading names, e.g. `state_safety_neg` = unsafe constructs and `state_heat_triggers` = metaprogramming.
- Leaks: C `size_t` counted as both safety and pointers; Python `pass` as a bypass; PHP `exit`/`die` as prints; TS class `extends` as generics; TS type assertions as UI.
- 36 `function_data` columns are structurally zero.
- C rules miss kernel and Windows vocabulary (`spin_lock*`, `readl`/`writel`, `Interlocked*`): gitgalaxy#8016.
- No earlier statistic changes; plain-language readings do (e.g. "linear code" should read "structural keywords").

## Take-home

Read signals by what their rules match, not by their column names. The engine now carries display names (signal_display_name).

## What it changed

gitgalaxy#8024 (display names, brief labels, rule fixes, scope map) was combined from a five-PR stack. Kernel vocabulary is still open (#8016). Studies after it should note the rule version.
