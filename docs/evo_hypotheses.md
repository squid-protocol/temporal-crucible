# SIG and CPL — the keyword mix and the coupling surface over time — registered 2026-11-06, before any statistic

**Why.** NH showed that code has a settled structure with continuous activity: functions die young and freeze;
include hubs are stable but busy. This entry asks two more natural-history questions:
- does a project's **keyword mix** stay constant, or change in spurts?
- does its **coupling to the outside world** (libraries, platforms) spread out or get centralised as it ages, and
  does centralising pay off?

**What has been looked at.**
- Column presence only: the five quarterly DBs carry the 22 `fam_*` signal-family columns.
- LIB's coupling results (per-unit means, not their time series).
- **Never computed:** any time series below.

## Part 1 — SIG: the keyword mix

**Data.**
- The NH quarterly DBs and snapshots: curl 105, nDPI 43, openssl 110, harfbuzz 62, libarchive 70.
- C/C++ files only. Families are the 22 `fam_*` columns.
- The mix at t = each family's share of the summed family counts over the snapshot's files (a 22-vector summing to 1).
- Drift = Jensen-Shannon divergence (base 2) between consecutive snapshots.

| id | claim | measure | supported iff |
|---|---|---|---|
| **SIG-H1** | **a project has a stable keyword fingerprint** | nearest-neighbour identification: each snapshot is assigned to the repo whose *other-era* snapshots (≥ 5 y away in time, or any snapshot of another repo) are closest in JSD | accuracy ≥ 0.90 over all snapshots (chance = 0.20) |
| **SIG-H2** | **the mix changes in spurts** | the share of a repo's total drift (Σ consecutive JSD) carried by its top 10% of quarters | ≥ 0.40 on ≥ 4 of 5 repos (even drift gives 0.10) |
| **SIG-H3** | **files keep their keyword profile** | for C files present at t and t + 1 y with ≥ 20 family hits at both: cosine similarity of their 22-vectors | median ≥ 0.90, pooled, with the snapshot-bootstrap lower bound ≥ 0.90 |

**Descriptive.** For each repo, the three largest-drift quarters with their top files by family change, to read what
happened.

## Part 2 — CPL: the coupling surface over time

**Units.**
- LIB's 21 evaluable (repo, library) units. Same dependency table and coupling regexes (`tools/lib_eval.py`), git
  only.
- Plus a **platform unit** per repo: ENV's `PATTERNS["P"]` platform conditionals.
- The four repos with LIB walks: curl, nDPI, harfbuzz, libarchive. openssl has no LIB units.

**Per unit and quarterly snapshot t:**
- `spread` = share of candidate files with ≥ 1 coupling line;
- `conc` = share of the unit's coupling lines held by its top 10% of coupled files (min 1 file).

Only snapshots where the unit has ≥ 3 coupled files count.

| id | claim | measure | supported iff |
|---|---|---|---|
| **CPL-H1** | **coupling centralises with age** (abstraction) | Spearman ρ(time, `conc`) per unit | median ρ > 0 over units, sign-test p < 0.01 |
| **CPL-H2** | **coupling's footprint shrinks as a share of the code** (encapsulation) | Spearman ρ(time, `spread`) per unit | median ρ < 0, sign-test p < 0.01 |
| **CPL-H3** | **centralised coupling makes later work cheaper** | per unit: Spearman ρ between `conc` at t and the median number of files touched by D-work commits (LIB's outcome; platform: XC extrinsic commits naming a platform family, TGT's subject regex) in (t, t + 180 d]. Snapshots with ≥ 3 such commits only | median ρ < 0 over units with ≥ 10 such snapshots, sign-test p < 0.01 |

**Priors.**
- SIG-H1 **leaning supported**: ARCH-S found the archetype mix drifts slowly.
- SIG-H2 **leaning supported**: the extrinsic bursts.
- SIG-H3 **leaning supported**.
- CPL-H1 / H2 **uncertain**. Mature projects add wrapper layers (curl's `vtls/`), but they also add new backends
  that each carry their own coupling.
- CPL-H3 **uncertain**, and the most interesting: it tests whether abstraction pays off.

---

## Results — 2026-11-06 (scorer `56bf3b2` committed before running; report `evo.md`)

### SIG — the keyword mix: all three SUPPORTED

| claim | result | verdict |
|---|---|---|
| **SIG-H1** stable project fingerprint | a snapshot is identified as its own repo from its keyword mix **95.9%** of the time (390 snapshots; only same-repo snapshots ≥ 5 y away count; chance 20%) | **SUPPORTED** |
| **SIG-H2** change comes in spurts | the top 10% of quarters carry curl 75%, nDPI 45%, openssl 84%, harfbuzz 89% and libarchive 88% of all drift | **SUPPORTED** |
| **SIG-H3** files keep their profile | median cosine a year apart **1.000** (lo 1.000) | **SUPPORTED**, with a caveat |

**Caveat on SIG-H3.** The median is 1.0 largely because most files do not change at all in a year (NH: 1–13% of
functions change shape per quarter). Among *edited* files the similarity is necessarily lower. That conditional figure
was not registered and is not computed here.

**What the spurts are** (the largest-drift quarters, read from their top files): architecture events, not gradual
accretion.
- **Removal:** curl 2025-06 dropped its SecureTransport and BearSSL backends.
- **Reorganisation:**
  - libarchive 2011-06 split `archive_write_disk.c` into POSIX and Windows files;
  - openssl 2017-06 removed engines;
  - curl 2001-03 replaced `highlevel.c` with `transfer.c`.
- **Expansion:**
  - harfbuzz 2026-03 added a raster/GPU layer;
  - libarchive 2009-06 added its core reader/writer files;
  - nDPI 2015-08 added protocol dissectors.

### CPL — the coupling surface: none SUPPORTED

| claim | median ρ | units in direction | sign-test p | verdict |
|---|---:|---:|---:|---|
| **CPL-H1** coupling centralises with age | −0.26 | 10 / 22 | 0.74 | not supported |
| **CPL-H2** footprint shrinks as a share of code | −0.22 | 16 / 23 | 0.047 | not supported (leans; misses α = 0.01) |
| **CPL-H3** concentration → later work touches fewer files | −0.13 | 6 / 9 | 0.25 | not supported (few units have enough data) |

**The direction is project-specific.** That is the finding.
- **curl centralises.**
  - OpenSSL coupling concentration rose 0.62 → 0.88 while its footprint fell from 13.2% to 2.4% of files.
  - c-ares went from 16.0% to 1.1%; libssh2 from 1.1% to 0.3%.
  - curl walled its dependencies behind backend layers (`vtls/`, `vssh/`, the async resolver modules).
- **libarchive spreads.** Concentration in bzip2, xz, zstd, openssl and zlib fell (e.g. zstd 0.50 → 0.25), while
  their footprints grew (zstd 0.5% → 1.1%): more format handlers call the compressors directly.
- **harfbuzz is mixed.** FreeType was encapsulated (5.8% → 1.4%); glib spread (7.8% → 13.6%).
- **Platform conditionals** concentrated in curl, nDPI and harfbuzz, and spread in libarchive (11% → 24% of files).

So abstraction over time is a *choice some projects make*, not a law of code evolution. It fits the niche-construction
reading (`burst_hypotheses.md`): projects decide how they absorb the outside world. Whether concentrating pays off
(H3) cannot be told from these data. Only 9 units have enough dependency-work commits, and they lean the predicted way
(6/9).
