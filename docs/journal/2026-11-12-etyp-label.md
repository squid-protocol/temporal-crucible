---
date: 2026-11-12
title: Can the edit-type vector label fixes? Mostly no (ETYP-LABEL)
type: exploratory
status: scored
verdict: n/a
theme: defect-prediction
ids:
docs: docs/etyp_label.md
links:
takehome: Fitted on one repo and scored on the other, a commit's edit-type vector separates message-labelled fixes from non-fixes at AUC only 0.57-0.59 (size alone 0.54-0.55) and regressions not at all, but recognises extrinsic fixes at 0.67-0.71 through preprocessor and type edits; the labelling claim was withdrawn before registration and the hand-judged samples were not spent.
---

# Can the edit-type vector label fixes? Mostly no (ETYP-LABEL)

## Question

Can a commit's edit-type vector, which never reads the message, tell a fix from a non-fix well enough to
improve the fix label?

## Why we asked

`etyp_fix.md` found replicating fix signatures and recommended labelling as the likelier use of the edit
types. The owner asked to start it. The `other-fix` label is 0.76 precise and carries 85-97% of outcome
mass, so a second, independent instrument would be worth a lot.

## What we did

`tools/etyp_label.py`: L2 logistic regression on the 26 label fractions per commit, fitted on curl and
scored on libarchive and the reverse, against size alone, for three targets (fix vs not a fix, extrinsic vs
other fixes, regression vs other fixes). The reference is the v3c message label. The hand-judged samples
on libgit2, postgres, libxml2 and redis were deliberately not scored.

## What we found

Exploratory. Fix vs not a fix: AUC 0.587 and 0.571 (size 0.542 and 0.553). Extrinsic: 0.668 and 0.705
(size 0.588 and 0.527), led by PREPROC and TYPE in both directions. Regression: 0.468 and 0.482.

## Take-home

The edit types describe fixes on average but do not make an individual fix recognisable; only the
extrinsic class carries to an unseen repo.

## What it changed

The labelling recommendation in `etyp_fix.md` is marked superseded and the draft registration carries a
note withdrawing it. The open lead is what an added branch tests, not that a branch was added.
