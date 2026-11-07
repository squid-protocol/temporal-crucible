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

---

## Results — 2026-11-06 (scorer `a40747d`; report `int.md`)

**Data.** 37,541 functions born with a full two-year follow-up: curl 6,219, OpenSSL 24,084, nDPI 1,873, harfbuzz
5,365. 9,111 in the high third, 5,774 in the low third.

| claim | result | verdict |
|---|---|---|
| **INT-H1** defensive-at-birth → CVE fix within 2 years | RR **0.97** [0.46, 1.72]; 52 vs 54 events | **not supported**: inconclusive, the interval spans both answers |
| **INT-H2** specific to CVEs | ratio 0.99 (lo 0.46) | **not supported** |

**Descriptive.**
- Per repo: OpenSSL 1.45, harfbuzz 2.86 (14 vs 2 events), curl 0.88, nDPI 0.52.
- Any defence vs none: 0.69.
- Regression 0.68; extrinsic 1.29.

**Reading.**
- **The question is not answered: the test is underpowered.**
  - Only 106 CVE fixes hit any function within two years of its birth.
  - CVE fixes overwhelmingly change *old* code: SRCH found them 2–4× older than ordinary commits.
  - So a two-year window after birth misses most vulnerabilities. They surface years later.
- That is itself a finding that bears on "were the authors right": **if authors sensed danger, the payoff, or the
  vulnerability, shows up years after the code is written, not in its first two years.**
- **The right design** is survival analysis over each function's whole observed life:
  - Cox-style hazard of a first CVE fix vs defence at birth;
  - the same strata;
  - functions censored at death or at the end of the labels.

  That needs a fresh registration.

---

## INT-S — whole-life version — registered 2026-11-06, before INT-S ran

**Why.** INT's two-year window caught only 106 CVE hits. CVEs surface years after code is written (SRCH).

**Changes from INT (everything else unchanged):**
- **Follow-up:** each function from its birth snapshot until the **first** fix of class X, its **death** (the first
  snapshot without it, under CHG's identity and move rule), or the repo's last labelled fix, whichever comes first.
- **Fix mapping:** each hit is resolved to a function **identity** at the snapshot preceding it (A1 join), so fixes to
  functions that later moved file are counted.
- **Estimate:** the stratified **Mantel–Haenszel rate ratio** of first-event rates per function-year, high vs low
  third (same strata as INT). File-cluster bootstrap, 2,000.
- No minimum follow-up: all births after the first snapshot are included.

| id | claim | supported iff (α = 0.01/2) |
|---|---|---|
| **INTS-H1** | defensive-at-birth code reaches a CVE fix at a higher rate over its life | rate ratio > 1 and lo > 1 ("the authors were right"). Reversed if < 1 and hi < 1 ("defended code is safer") |
| **INTS-H2** | …specifically CVEs | RR_latent ÷ RR_other-fix (first-event rates) > 1, lo > 1 |

**Descriptive.**
- Cumulative share with a first CVE fix by 5 and 10 years (life-table), per group.
- Per-repo rate ratios.
- Regression and extrinsic first-event rate ratios.

### INT-S results — 2026-11-06 (scorer `7943375`; report `ints.md`)

**Data.** 44,046 functions born after the first snapshot; 126,308 function-years (median observed life 4.6 years);
562 first-CVE events in the high and low thirds.

| claim | result | verdict |
|---|---|---|
| **INTS-H1** first-CVE-fix rate, high vs low defence at birth | **0.96** [0.73, 1.28]; events 245 / 317 | **not supported**: a fairly tight null |
| **INTS-H2** CVE-specific | 0.90 (lo 0.67); other-fix 1.06 | **not supported** |

**Descriptive.**
- Cumulative share reaching a CVE fix, crude and **not** size-stratified: 5 years high 1.6% vs low 2.5%; 10 years
  3.1% vs 4.1%.
- Per repo: OpenSSL 1.38, curl 0.79, nDPI 0.64.
- harfbuzz has only 2 low-defence events, so its stratified estimate is degenerate (0.00).
- Regression 0.80; extrinsic 1.74.

**Reading.**
- **Writing a function defensively from the start neither predicts nor prevents its later CVEs.** Over whole
  lifetimes, size- and file-history-matched, the rate ratio is 0.96. The data rule out effects much beyond ±30%.
- The repos disagree in direction: OpenSSL leans "the authors were right", curl and nDPI lean "defended code is
  safer". No consistent effect pooled.
- **This fits the rest of the program.**
  - CVE-fixed code is usually guarded (FORT: 72%) because most code is (70%).
  - What predicts security fixes is **history**: prior CVE fixes in the same place (RW-H2, WH: AUC 0.72). It is not
    the author's initial defensiveness.
  - The danger is learned by being found, not sensed at creation, or at least the sensing does not show in
    guard-keyword density.
