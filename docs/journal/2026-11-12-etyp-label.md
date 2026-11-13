---
date: 2026-11-12
title: Can the edit-type vector label fixes? Mostly no (ETYP-LABEL)
type: exploratory
status: scored
verdict: n/a
theme: defect-prediction
ids:
docs: docs/etyp_label.md; docs/etyp_review.md
links: temporal-crucible#175
takehome: Fitted on one repo and scored on the other, a commit's edit-type vector adds no detectable AUC to commit size for telling message-labelled fixes from non-fixes (+0.016 and +0.002, both intervals including zero) and is at chance for regressions; extrinsic fixes score 0.65-0.69 but that largely recovers the subject rule that assigns the label; the labelling claim was withdrawn and the hand-judged samples were not spent.
---

# Can the edit-type vector label fixes? Mostly no (ETYP-LABEL)

**Superseded in part by an independent review: the numbers and claims in the sections below are the first
version; the corrections are in the last section and in `docs/etyp_review.md`.**

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

## Revised after independent review (2026-11-12)

With the corrected groups (`docs/etyp_review.md`) commit size alone reaches 0.58, and the types add nothing
detectable to it. The first version's "better than size by two or three points" came from cosmetic-subject
commits in the negatives. Its "usable cross-check on the extrinsic label" is withdrawn: the label is assigned
from platform words in the subject and platform-named commits edit preprocessor conditions regardless.
