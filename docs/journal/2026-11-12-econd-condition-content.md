---
date: 2026-11-12
title: What a new condition tests, and whether the new branch is a guard (ECOND)
type: exploratory
status: scored
verdict: n/a
theme: defect-prediction
ids:
docs: docs/econd.md; docs/etyp_review.md
links: temporal-crucible#175
takehome: Classifying what each new condition tests covers every case but gives no detectable gain in recognising a fix (at most +0.011 AUC across curl and libarchive); the one cell marked in both repos is that fixes add relational comparisons between two variables (1.80 and 1.67), and the null-check kinds turn out to be house style rather than meaning; a second look at burned data, with three labels corrected after review.
---

# What a new condition tests, and whether the new branch is a guard (ECOND)

**Superseded in part by an independent review: the numbers and claims in the sections below are the first
version; the corrections are in the last section and in `docs/etyp_review.md`.**

## Question

If the type of an edit cannot tell a fix from a feature, can what a new condition tests, and whether the
new branch exits?

## Why we asked

`etyp_label.md` found the edit-type vector reaches AUC 0.57-0.59 for fix vs not a fix and left one lead:
the content of an added condition, which ETYP abstracts away.

## What we did

`tools/cond_content.py` gives each new condition leaf one syntactic kind and each new `if` a shape (guard
or action), outcome-blind first, on curl and libarchive. A stop rule was set before the join: one session,
and stop if condition content made a fix no more recognisable than edit types did. Then the same join and
cross-repo model as `etyp_fix.md` and `etyp_label.md`.

## What we found

Exploratory. 30-32% of edits carry a new condition and under 0.5% are residual. The null-ish kinds are
house style: curl writes `if(!p)` (36.0% NEGATED, 1.5% NULL_CMP), libarchive `if (p == NULL)` (12.0%,
25.9%). Fixes add variable-to-variable relational conditions at 1.83x and 1.84x. "A fix adds a guard"
holds in libarchive (1.36) and not in curl (1.07). The gain in cross-repo AUC from condition content is
+0.000 and +0.005.

## Take-home

The syntactic shape of a change describes fixes on average and does not make one recognisable; three
attempts now agree.

## What it changed

The ETYP line is closed at exploratory. One narrow descriptive claim (relational variable comparisons in
fixes) is recorded as registrable on unseen repos and not registered.

## Revised after independent review (2026-11-12)

An independent review (`docs/etyp_review.md`) found GUARD_ADD, COND_NARROW and the constant test wrong in
8%, 33-42% and 15% of cases; all three are fixed. The first version's claims that the taxonomy was fixed
before any outcome and that the stop rule preceded the join are withdrawn as unprovable (same commit as the
results), and its reading of REL_VAR as a missing bounds check is withdrawn (not marked on new guards in
curl).
