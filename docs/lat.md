# LAT-F1..F3, LAT-M1..M3 — the fingerprint lattice vs fix kinds and regressions (SCORED)

Registration: `docs/lat_hypotheses.md` (with Amendment 0). Aggregates only.

## LAT-F — fix kinds × pre-fix family and rung

- touched functions (commit × function, parent blob): 60,380 — latent 1,653, regression 1,462, extrinsic 4,392, other-fix 52,873
- unassigned (no signal shared with any of the 200 shapes): 0.0%

| claim | result | verdict | sensitivity (without #8010/#8016 signals) |
|---|---|---|---|
| **LAT-F1** latent-CVE in private-C upper rungs (F8 ∧ k ≥ 6) vs other-fix | 59.3% vs 56.9%; MH RR **1.08** [1.00, 1.14] (99%) | **not supported** | RR 1.08 [1.00, 1.17] → not supported |
| **LAT-F2** fix classes differ by family × rung beyond size (within-stratum permutation) | Cramér's V **0.068**, p = 0.0005 | **SUPPORTED** | V 0.067, p 0.0005 → SUPPORTED |
| **LAT-F3** not a size artefact (size-only placebo, 200 draws) | observed V 0.068 vs placebo 99th pct 0.043 (mean 0.037) | **SUPPORTED** | 0.067 vs 0.044 → SUPPORTED |

### Descriptive — family share by fix class (main)

| family | latent | regression | extrinsic | other-fix |
|---|---:|---:|---:|---:|
| F8 | 63.9% | 70.1% | 67.9% | 60.5% |
| F7 | 33.2% | 25.3% | 30.5% | 37.3% |
| F6 | 1.2% | 0.3% | 0.6% | 0.9% |
| F5 | 1.5% | 2.1% | 0.5% | 0.8% |
| F10 | 0.0% | 0.4% | 0.2% | 0.1% |
| F11 | 0.0% | 0.0% | 0.1% | 0.1% |
| F12 | 0.1% | 1.4% | 0.0% | 0.1% |
| F1 | 0.1% | 0.3% | 0.1% | 0.1% |
| F9 | 0.1% | 0.0% | 0.0% | 0.0% |

| rung band | latent | regression | extrinsic | other-fix |
|---|---:|---:|---:|---:|
| k ≤ 3 | 1.3% | 3.0% | 1.1% | 1.2% |
| k 4–5 | 7.1% | 15.5% | 5.2% | 6.7% |
| k ≥ 6 | 91.6% | 81.5% | 93.7% | 92.1% |

## LAT-M — lattice moves vs regressions (CHG-2 units)

- units 1,526,252; regression-hit 1,188; edited (churn > 0) 129,705; lattice signals available 25

| claim | result | verdict | sensitivity |
|---|---|---|---|
| **LAT-M1** lattice moves add recall@20% beyond churn (forward **and** LORO, ≥ +2.0 pt, lo > 0) | forward B0 42.5% → M2 42.9% (**+0.5%**, lo -1.9%; 666 pos); LORO 36.6% → 36.6% (**+0.0%**, lo -2.0%; 1188 pos) | **not supported** | fwd +0.8% (lo -2.7%), LORO -0.8% (lo -2.1%) → not supported |
| **LAT-M2** half-step edits precede regressions (edited units) | 2,007 half-step units, 5 regression-hit; MH RR **1.23** [0.20, 3.17] (99%) | **not supported** | RR 1.32 [0.00, 3.66] → not supported |
| **LAT-M3** control: permuted lattice features add ~nothing (\|diff\| < 1 pt) | forward +0.0%, LORO -0.8% | **PASS** | — |

### Descriptive (main)

- units whose shape moved: 1.6% (of edited units: 17.8%); functions whose shape never moved over all their intervals: **70.9%** of 57,382
- among moves: single-signal steps 67.6%, jumps (≥ 2) 32.4%; climbs 50.7%, descents 38.2%; family changes 10.8%; half-step present 9.0%; end shape off-lattice 14.5% of all units
- regression rate: moved 0.28% vs unmoved-but-edited 0.38% vs untouched 0.05%
- commonest single-signal moves: +def_freeze_hits 3,284, +state_cast_hits 2,293, −state_flux 2,226, −arch_globals 2,204, +struct_branch 1,972, −state_cast_hits 1,824, +struct_args 1,804, −struct_branch 1,663, −state_safety_neg 1,621, +def_safety 1,614
- commonest family changes: F7→F8 1,223, F8→F7 646, F6→F5 131, F8→F5 112, F8→F6 84, F6→F8 68, F6→F7 51, F7→F5 48

Runtime 713s · seed 2982 · 2000 file-cluster bootstrap rounds · 2000 permutations · 200 placebo draws.
