---
date: 2026-11-11
title: Comment profiles of whole files and whole systems
type: exploratory
status: scored
verdict: n/a
theme: comments
ids:
docs: docs/comment_profiles_exploratory.md
links:
takehome: Commenting is a property of systems and files more than of functions; nine C projects differ several-fold in density and header coverage, files keep their commenting culture for years, and danger wording grew in most projects; outcome-blind, so nothing yet says which culture is riskier.
---

## Question

Function-grain comment studies give thin, sparse effects. What does commenting look like as a whole, per file and
per system, and does it have stable structure worth testing?

## Why we asked

The owner (2026-11-11) found the per-function analyses unsatisfying and asked whether comments could be analysed as a
whole, per file or per system.

## What we did

- Profiled every C/C++ file at every quarterly snapshot of nine systems: curl, OpenSSL, nDPI, harfbuzz, libarchive,
  libgit2, libxml2, postgres and redis. That is 748 snapshots, 437,978 file versions and 165,421 distinct blobs, in
  3 minutes.
- Each profile has: density, danger share, TODO/FIXME debt, commented-out code, header coverage, and the license
  banner counted separately.
- Outcome-blind: no fix or CVE data was read. Report:
  [`../comment_profiles_exploratory.md`](../comment_profiles_exploratory.md).

## What we found

- **Systems differ several-fold.** Median file density runs from 0.08 (harfbuzz) to 0.41 (postgres). Header coverage
  runs from 0% to 89%.
- **Five file cultures, and they are sticky.** About 72–96% of files keep their culture over four years, against a
  40–65% baseline.
- **Danger wording grew** in five of eight long-lived systems. It may be vocabulary drift.
- **Commented-out code declined** almost everywhere.
- **Comment neglect** (code grows, comments don't) ranges from 8% (postgres, redis) to 29% (OpenSSL).
- **Size dependence.** Danger share and debt rise with file size; density does not.

## Take-home

Comments carry stable structure at file and system grain that function-grain studies cannot see. Whether it relates
to fixes is untested.

## What it changed

- **Next registration:** file comment profile → next-year fixes and CVEs, beyond size and history, on a later-era
  holdout. Density and header coverage as primary measures; the others size-stratified.
- **Unseen-repo replication.** libgit2, libxml2, postgres and redis already have quarterly walks and pool clones, so
  they are ready for it.
