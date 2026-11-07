---
date: 2026-11-06
title: The natural history of code: function lifecycles and include-graph hubs (NH)
type: confirmatory
status: scored
verdict: supported
theme: natural-history
ids: LIFE-H1..H3; HUB-H1..H3
docs: docs/nh_hypotheses.md; docs/nh.md
links: temporal-crucible#70
takehome: Code has a natural history: young functions die 2.9× faster than mid-aged ones, shape change slows to 0.46× with age, 88% of edited functions keep their archetype, and include hubs are stable and grow sub-linearly, but hubs change more than other files, not less.
---

# The natural history of code: function lifecycles and include-graph hubs (NH)

## Question

The question here is how structure lives, not whether it predicts fixes:
- how long do functions survive?
- does their shape freeze with age?
- are include-graph hubs stable?
- do hubs get richer?
- are hubs a frozen core?

## Why we asked

Every earlier study asked about prediction. A descriptive "biology" of codebases is a use of the engine that does not need to beat size. Each claim still had a pass rule fixed in advance, so it could fail.

## What we did

- Quarterly engine scans of five C/C++ repos: curl 105, nDPI 43, openssl 110, harfbuzz 62, libarchive 70. Function extraction was validated at 97–100% against tree-sitter and ctags.
- **LIFE-H1:** infant mortality, death hazard in the first year against years 3–5.
- **LIFE-H2:** structural freeze, shape-change rate at 3 years or more against the first year.
- **LIFE-H3:** archetype kept when (loc, complexity) changed.
- **HUB-H1:** hubs persist a year later. **HUB-H2:** attachment slope above 0. **HUB-H3:** hubs change less than same-size files.
- Snapshot bootstraps within repo, 5,000 rounds.

## What we found

- **LIFE-H1 supported:** pooled hazard ratio 2.93 (lo 1.80). Range 1.91 (curl) to 7.82 (libarchive).
- **LIFE-H2 supported:** change-rate ratio 0.46 (hi 0.59).
- **LIFE-H3 supported:** archetype kept in 0.876 of shape-changing edits (lo 0.862).
- **HUB-H1 supported:** 92–100% of hubs are still hubs a year later, on 5/5 repos.
- **HUB-H2 supported on 5/5, and sub-linear:** gain in includers scales with in-degree to the power 0.2–0.5.
- **HUB-H3 not supported, reversed:** hubs are more likely to change within a year (pooled RR 1.12; libarchive 1.62). Widely included headers are where new declarations land.
- Caveat: function identity is (file, name), so a rename within a file counts as a death and a birth.

## Take-home

Functions die young or settle down, and settled code freezes. Hubs are a stable position with active content.

## What it changed

Natural history became one of the engine's established uses (synthesis § 1). SFS later refined LIFE: names persist 95–100% a year, but only 59–72% of functions keep a structural twin. AGE tested whether the lifecycle shows up in the age of the code each fix class changes.
