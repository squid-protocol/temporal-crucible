---
date: 2026-11-12
title: Every fix as a vector of edit types: class, impact, cause, follow-up (ETYP-FIX)
type: exploratory
status: scored
verdict: n/a
theme: defect-prediction
ids:
docs: docs/etyp_fix.md
links:
takehome: Against non-fix commits of the same size and magnitude, a fix edits conditions and operators in place or adds a branch and does not rewire (LOGIC 1.18 and 1.28, WIRING 0.81 and 0.67 in curl and libarchive), and extrinsic fixes are marked by TYPE and PREPROC edits in both repos; as a forward signal the type of an edit moves the one-year fix rate only about 1.1x after size, history and magnitude; exploratory and uncorrected.
---

# Every fix as a vector of edit types: class, impact, cause, follow-up (ETYP-FIX)

## Question

If every fix is rewritten as counts of the ETYP edit types, what do those vectors correlate with: fix
class, CVE impact, outside reports, the commits that introduced the defect, and the next fix?

## Why we asked

ETYP gave a closed set of edit types without reading any outcome. The owner asked to put the buckets to
work against impacts and issues.

## What we did

`tools/etyp_fix.py` joins the edit rows to the existing event files on curl and libarchive, which were
already burned for the taxonomy; openssl and nDPI were not touched. Lifts are standardised on commit size
two ways (function edits and tokens changed); the follow-up rate on function size, prior edit count and
edit magnitude. Intervals are 95% bootstraps. About 30 labels by 10 groups, no multiplicity correction.
The first run lacked the changed-token control and overstated the defect-introducing lifts about twofold;
both runs are recorded.

## What we found

Exploratory. A fix is LOGIC-heavy and WIRING-light in both repos. Extrinsic fixes carry TYPE (1.96, 2.21)
and PREPROC (2.39, 1.48). CVE fixes do not differ from their matched controls on structure; they differ
in carrying no rename, format or type change. CVE-introducing commits add branches, exits and calls
(curl only, 113 commits). After a non-fix edit that adds a branch or statement the function is fixed
within a year about 1.05-1.15x as often as size, history and magnitude predict; LOGIC edits predict
nothing forward.

## Take-home

Edit types describe what a fix is, and tell fix classes apart, better than they predict where the next
fix lands.

## What it changed

The draft ETYP registration carries a note: its predictor mixes a family with no forward signal, and a
labelling claim (recognising fixes and fix class from the type vector) looks better supported than a
ranking claim.
