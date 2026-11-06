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
