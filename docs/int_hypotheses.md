# INT — were the authors right? Does code written defensively from the start later get more CVE fixes? — registered 2026-11-06, before any INT statistic

**Why.** CVE fixes concentrate in already-defended code (GR's reversal, FORT, KF-R's `goto` cleanup). But guards can
be *added after* earlier security bugs, so "defended code gets CVEs" may just be recidivism.

The owner's question is about **intent at creation**: when authors wrote a function defensively from day one, did
vulnerabilities later show up there? In other words, did they correctly sense dangerous code?

## Data

- **Repos with CVE labels:** curl, OpenSSL, nDPI, harfbuzz. Quarterly engine snapshots (NH / CHG DBs); C/C++
  functions; CHG's identity rule.
- **Units:** functions **born after the first snapshot**, with loc ≥ 3 at birth.
  - The birth snapshot is the first in which the function appears.
  - Only functions whose **two-year follow-up** after birth ends before the repo's last labelled fix are kept.
- **Defence at birth:** D = (def_safety + state_safety_neg + state_bailout_hits) ÷ loc, from the birth snapshot.
  These are the engine's safety-check, negative-safety (e.g. `!ptr`) and bailout (abort / early-exit) counts.
- **Exposure:** within each stratum (below), units are ranked by D (average ranks).
  - **High-defence** = top third. **Low-defence** = bottom third. The middle third is excluded.
- **Outcome:** the function (same file and name, CHG's A1 join) is hit by a fix of class X within two years after
  its birth snapshot. CHG's tree-sitter fix mapping; XC classes; harfbuzz security events as latent.
- **Strata:** repo × log₁₀ loc bin (0.1) × **file had a CVE fix before the function's birth** (yes / no). The last
  removes file-level recidivism.

## Claims (α = 0.01/2; MH RR; 2,000-round file-cluster bootstrap)

| id | claim | supported iff |
|---|---|---|
| **INT-H1** | defensively written code later gets more CVE fixes | latent RR(high vs low) > 1 and lo > 1 → **"the authors were right"**. If RR < 1 and hi < 1 → **"defended code is safer"** (also reported) |
| **INT-H2** | …specifically CVEs, not all fixes | RR_latent ÷ RR_other-fix > 1, bootstrap lo > 1 |

- **Not evaluable** if < 30 latent hits on either side.
- **Descriptive:**
  - per-repo RRs;
  - regression and extrinsic outcomes;
  - a binary version (D > 0 vs D = 0);
  - the share of high-defence functions hit.

## Priors

- **H1 leaning "right"** (GR, KF-R).
- **H2 uncertain.** Defensive code may just be more complex, busier code.
