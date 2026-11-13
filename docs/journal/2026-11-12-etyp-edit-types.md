---
date: 2026-11-12
title: Can every function edit be reduced to a discrete type? (ETYP)
type: exploratory
status: scored
verdict: n/a
theme: keyword-grammar
ids:
docs: docs/etyp.md; docs/etyp_hypotheses.md
links:
takehome: A closed set of 26 named edit types covers 99% of function edits in curl (54,890 edits) and libarchive (16,746), about 15 family combinations cover 80%, and a function's next edit resembles its last at 1.70x and 1.96x a size-matched null; outcome-blind, so nothing here is about defects yet.
---

# Can every function edit be reduced to a discrete type? (ETYP)

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
