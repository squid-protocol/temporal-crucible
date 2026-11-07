---
date: 2026-11-06
title: Projects have structural fingerprints; does their coupling evolve? (SFS, SIG, CPL)
type: confirmatory
status: scored
verdict: mixed
theme: provenance
ids: SFS-H1..H4; SIG-H1..H3, CPL-H1..H3
docs: docs/sfs_hypotheses.md; docs/sfs.md; docs/evo_hypotheses.md; docs/evo.md
links: temporal-crucible#71; temporal-crucible#72
takehome: A project's keyword mix (95.9%) and its sfs structural fingerprint (99.0%) identify it across eras five or more years apart, and its mix changes in spurts at architecture events; but turnover does not track regressions, and whether coupling centralises with age is project-specific.
---

# Projects have structural fingerprints; does their coupling evolve? (SFS, SIG, CPL)

## Question

Over a project's life:
- does its keyword mix, or the `sfs` structural fingerprint, stay a stable identity?
- does it change gradually or in spurts?
- does structural turnover go with regressions?
- does the project's coupling to libraries and platforms centralise with age, and does centralising make later dependency work cheaper?

## Why we asked

The owner asked how stable `sfs` fingerprints are and whether bugs correlate with change. NH had shown a settled structure with continuous activity. `sfs` also gives a name-free function identity that can check NH's name-based survival.

## What we did

- **SIG** (evo). The quarterly DBs of five repos (390 snapshots). The mix is a 22-family share vector.
  - H1: nearest-neighbour identification against same-repo snapshots at least 5 years away (bar 0.90).
  - H2: the top 10% of quarters carry at least 40% of drift.
  - H3: files keep their profile a year apart.
- **CPL** (evo). LIB's (repo, library) units plus a platform unit per repo.
  - H1: concentration rises with time. H2: footprint shrinks. H3: concentration leads to fewer files touched by later dependency work.
- **SFS.** 103 yearly snapshots, 5 repos, `sfs` at a pinned commit.
  - H1: identity across eras. H2: name-free twin retention agrees with name-based survival (ρ ≥ 0.50).
  - H3 and H4: turnover goes with regression share, and more than with CVE share.

## What we found

- **SIG-H1 supported:** 95.9% identification (chance 20%).
- **SIG-H2 supported:** the top 10% of quarters carry 45–89% of drift. The spurts are architecture events: backend removals, file splits, new layers.
- **SIG-H3 supported**, with a caveat: the median cosine is 1.000 largely because most files do not change in a year.
- **CPL-H1 to H3 not supported.** Median ρ is −0.26 and −0.22, and only 9 units have enough data for H3. curl walls its dependencies behind backend layers, while libarchive spreads them.
- **SFS-H1 supported:** 99.0%.
- **SFS-H2 not supported:** ρ 0.49 against a bar of 0.50. Names persist 95–100% a year, but only 59–72% of functions keep a structural twin.
- **SFS-H3 and H4 not supported:** turnover does not track regression share.

## Take-home

Identity is stable and the body is not. Projects are recognisable from their structure across decades and change in bursts. How they absorb the outside world is a project choice, not a law.

## What it changed

Fingerprint identity joined the engine's established uses (synthesis § 1). Replication on unseen repos is still owed. NH's lifecycle is now read as name-based: a name-free lifecycle would show faster turnover. CPL's project-specific direction fed the niche-construction reading in BURST.
