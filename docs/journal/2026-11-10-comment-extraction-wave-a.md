---
date: 2026-11-10
title: Can we trust the comment instruments? (comment-extraction Wave A)
type: exploratory
status: scored
verdict: n/a
theme: comments
ids:
docs: docs/comment_wave_a.md
links: gitgalaxy#8200; gitgalaxy#8240; gitgalaxy#8244; gitgalaxy#8245; gitgalaxy#8255; gitgalaxy#8256; temporal-crucible#109; temporal-crucible#116
takehome: Comment prose is 14% of hunk-grain branch hits but does not drive the fix gradient; the new header-comment flag is about 95% precise on curl; but the commented-out-code signal is about 4% precise on curl (mostly "/* for foo() */" include notes), so no study should read it until the rule is fixed.
---

# Can we trust the comment instruments? (comment-extraction Wave A)

## Question

Before testing anything about comments and defects, do the comment instruments measure what their names say? Three
checks:
- Does comment prose leak into the hunk-grain grammar?
- Do the documentation flags work on traditional C?
- Do the comment signals reach the right functions, and are they what they say?

## Why we asked

Gemini's 2026-11-09 review of comment extraction found four engine problems:
- comment signals never reached functions;
- star banners read as Doxygen;
- `#include` lines read as docstrings;
- comment prose was scored as code in patches.

Fixing them (gitgalaxy#8200, #8240, #8244, #8245; temporal-crucible#109, #116) still left open whether the fixed
instruments can carry a study. The comment *line* extraction itself already passed CMT-G (C 99.9% precision, 98.0%
recall).

## What we did

- **Data and engine:** curl at the events' pinned head (`04bfe8fbbf`), with the fixed engine (main plus the three
  open PRs, merged locally).
- **COM-E1:** scored all 1,756 event patches three ways: raw, code-only, comments-only.
- **COM-E2 and COM-E3:** one scan. Then a hand audit of 40 header-comment decisions and of all 48 commented-out-code
  matches.
- **Scorer:** `tools/comment_wave_a.py`. Details are in [`../comment_wave_a.md`](../comment_wave_a.md).

## What we found

All results are exploratory.
- **Comment prose is real in patches, but it is not the signal.** It was 14.4% of added branch hits. Stripping it
  moves each class's fix-shaped rate by at most 3 points, and the security-fix vs control gap goes from 18 to 20
  points.
- **Documentation flags.** `is_documented` marks 1.1% of curl's C functions; `has_header_comment` marks 27.1%. The
  latter is about 95% precise in a 20-case sample. Its misses come from one curl idiom (a `UNITTEST` prototype
  between the comment and the definition) and from a `#define` trailing-comment tail. Both are fixable in the engine.
- **Attribution works.** TODO, FIXME and commented-out-code hits now land in the right function, or correctly
  outside all of them. Before #8200 all were 0 at function grain.
- **`state_graveyard` is about 4% precise on curl.** Only 2 of 48 matches are commented-out code; 39 are prose,
  mostly `/* for offsetof() */` notes after `#include`.

## Take-home

The comment-line extraction and the new header-comment flag are good enough to study. The commented-out-code signal
is not: on curl it mostly counts include notes, so earlier results that leaned on `state_graveyard` should be read as
comment style until the rule is fixed.

## What it changed

- **gitgalaxy follow-ups:**
  - Fix the C-family `dead_code` keyword arm to need code shape: **done in gitgalaxy#8255** (curl 48 → 9 matches,
    2 real plus 7 prototype notes).
  - Fix the two `has_header_comment` misses (trailing-comment tail; the unit's own prototype): **done in
    gitgalaxy#8256** (curl 1,196 → 1,223).
- **COM-H3 is on hold until the `dead_code` fix.**
- **COM-H1, H2 and H4 can be registered.** H4 should use `has_header_comment`, not `is_documented`.
- **`hunk_grammar.py`'s cache file name now carries a strip version.** `hunk_grammar.md` is to be regenerated on
  melek, where its file-grain cache lives.
