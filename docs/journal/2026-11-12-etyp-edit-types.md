---
date: 2026-11-12
title: Can every function edit be reduced to a discrete type? (ETYP)
type: exploratory
status: scored
verdict: n/a
theme: keyword-grammar
ids:
docs: docs/etyp.md; docs/etyp_hypotheses.md; docs/etyp_review.md
links: temporal-crucible#175
takehome: A closed set of 26 named edit types covers 99% of function edits in curl (54,890) and libarchive (11,541 without test code), about 15 family combinations cover 80%, and once patch series, shared authors and shared files are removed a function's next edit resembles its last at only about 1.3x on labels and 1.1x on families; outcome-blind, and the first version's 1.70x / 1.96x is withdrawn.
---

# Can every function edit be reduced to a discrete type? (ETYP)

**Superseded in part by an independent review: the numbers and claims in the sections below are the first
version; the corrections are in the last section and in `docs/etyp_review.md`.**

## Question

If a function's structure is fixed at birth, what changes between fixes, and can each change be given a
discrete type?

## Why we asked

KWNEST found the control skeleton is never rearranged, CEIL found about 22 points of unmeasured rate
heterogeneity, and REW found rewiring beats edit count but not size. The owner asked whether every code
change can be reduced to a discrete type, as the thing worth measuring instead of structure.

## What we did

`tools/edit_types.py`: for every non-merge commit, every modified `.c` file under the source roots, and
every function present by name on both sides with different text, tree-sitter features of both sides are
compared and the edit gets a set of atomic labels (26 named, 2 residual, 8 families) and one primary
family by a fixed priority. The tool reads no fix label, event file or commit message; a test pins that.
One rule changed after a 3,000-file smoke run and before the full run (token-kind labels fire only on
in-place edits), decided from label counts alone and recorded in the doc.

## What we found

Exploratory. UNCLASSIFIED is 0.8% (curl) and 0.7% (libarchive). Edits are compounds (2.61 and 2.74 atomic
labels each), but 14 and 15 family combinations cover 80% of edits. Primary-family shares agree across the
repos (WIRING 32-35%, STRUCTURE 25-27%, LOGIC 19-20%). Consecutive edits to one function share labels at
1.70x and 1.96x a size-matched null; RETURN_VALUE, LOOP_CHANGE, PREPROC, STRING_LITERAL and ARG_ARITY are
the stickiest named types in both.

## Take-home

Function edits fall into a small closed set of types and the type is partly a property of the function.
Whether it predicts fixes is not known.

## What it changed

A draft registration (`docs/etyp_hypotheses.md`, unapproved) asks whether the count of behaviour-changing
edits beats the raw edit count and the size order, on repos the taxonomy has not seen.

## Revised after independent review (2026-11-12)

The first version of this entry reported 1.70x and 1.96x against a size-matched stranger. An independent
review (`docs/etyp_review.md`) showed about half of that is patch series, one author and one file: against
another function in the same file, with a different author and at least 30 days between edits, it is 1.34x
and 1.26x on atomic labels and 1.09x and 1.10x on families. libarchive's test code (31% of its edits) was
removed. The taxonomy was corrected after outcomes had been seen (1.2% of label sets changed), so it is no
longer outcome-blind in the strict sense. The draft registration is withdrawn.
