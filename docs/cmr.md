# CMR — comments × call-graph role × fix class (SCORED)

- births with comment and role at birth: 48,214 (repos curl, openssl, ndpi, harfbuzz, libarchive); skipped: {('curl', 'comment'): 57, ('curl', 'role'): 1, ('openssl', 'comment'): 298, ('openssl', 'role'): 238, ('ndpi', 'comment'): 48, ('ndpi', 'role'): 1, ('harfbuzz', 'comment'): 410, ('libarchive', 'comment'): 19}
- registration `docs/cmr_hypotheses.md`

## Part P — placement (two-sided CMH, strata repo × loc bin, α = 0.01/6)

| id | role | OR | z | exposed | call |
|---|---|---|---|---|---|
| CMR-P1 | hub | 1.33 | +4.8 | 1,604 | **enriched** |
| CMR-P2 | hub | 1.26 | +1.8 | 760 | **n.s.** |
| CMR-P1 | orch | 0.87 | -2.9 | 4,016 | **n.s.** |
| CMR-P2 | orch | 0.60 | -7.4 | 3,129 | **depleted** |
| CMR-P1 | periph | 0.87 | -5.8 | 20,069 | **depleted** |
| CMR-P2 | periph | 1.25 | +4.2 | 6,609 | **enriched** |

Exposed = functions in the role (P1) or commented functions in the role (P2); OR > 1 = more commented (P1) / more danger-worded (P2) in the role.

## Part F — comment → first-fix rate ratio inside vs outside each role (interaction = RR_in ÷ RR_out; file-cluster bootstrap 2000; two-sided α = 0.01/9 per family)

| id | role | class | RR in role | RR outside | interaction [CI] | events (in: exp/unexp; out: exp/unexp) | call |
|---|---|---|---|---|---|---|---|
| CMR-FD | hub | latent | 0.61 | 1.45 | 0.42 [0.00, 15.99] | 4/18; 140/505 | **underpowered** |
| CMR-FD | hub | regression | 0.00 | 1.10 | 0.00 [0.00, 0.00] | 1/10; 94/411 | **underpowered** |
| CMR-FD | hub | extrinsic | 0.89 | 1.15 | 0.78 [0.00, 6.55] | 8/64; 279/1251 | **underpowered** |
| CMR-FD | orch | latent | 1.58 | 1.36 | 1.16 [0.58, 2.59] | 49/105; 95/418 | **n.s.** |
| CMR-FD | orch | regression | 1.27 | 1.06 | 1.20 [0.41, 3.65] | 33/90; 62/331 | **n.s.** |
| CMR-FD | orch | extrinsic | 1.31 | 1.09 | 1.20 [0.67, 2.15] | 82/228; 205/1087 | **n.s.** |
| CMR-FD | periph | latent | 1.23 | 1.49 | 0.82 [0.18, 2.59] | 17/93; 127/430 | **underpowered** |
| CMR-FD | periph | regression | 1.64 | 1.04 | 1.58 [0.44, 4.24] | 15/73; 80/348 | **underpowered** |
| CMR-FD | periph | extrinsic | 0.95 | 1.20 | 0.79 [0.46, 1.32] | 58/420; 229/895 | **n.s.** |
| CMR-FC | hub | latent | 1.77 | 1.06 | 1.67 [0.00, 163.56] | 22/9; 645/316 | **underpowered** |
| CMR-FC | hub | regression | 1.00 | 1.13 | 0.88 [0.00, 58.06] | 11/7; 505/277 | **underpowered** |
| CMR-FC | hub | extrinsic | 1.14 | 1.05 | 1.08 [0.27, 3.95] | 72/28; 1530/692 | **n.s.** |
| CMR-FC | orch | latent | 1.35 | 1.04 | 1.29 [0.58, 5.15] | 154/26; 513/299 | **n.s.** |
| CMR-FC | orch | regression | 1.65 | 1.06 | 1.56 [0.63, 5.38] | 123/17; 393/267 | **underpowered** |
| CMR-FC | orch | extrinsic | 1.32 | 1.05 | 1.26 [0.62, 2.86] | 310/35; 1292/685 | **n.s.** |
| CMR-FC | periph | latent | 0.83 | 1.19 | 0.69 [0.34, 1.71] | 110/130; 557/195 | **n.s.** |
| CMR-FC | periph | regression | 0.81 | 1.28 | 0.63 [0.32, 1.22] | 88/130; 428/154 | **n.s.** |
| CMR-FC | periph | extrinsic | 1.06 | 1.07 | 0.99 [0.62, 1.61] | 478/387; 1124/333 | **n.s.** |

## Descriptive (no verdicts)

- hub: 1,604 births; commented 47% (others 45%); danger among commented 11% (others 12%); comment lines per loc 0.138 (others 0.123)
  - top danger words: do not 15, must be 15, assume 10, overflow 8, security 5, null-terminated 5, must not 4, assumed 4, race 4, null termination 3
- orch: 4,016 births; commented 78% (others 42%); danger among commented 16% (others 11%); comment lines per loc 0.131 (others 0.121)
  - top danger words: must be 140, do not 104, assume 51, validation 44, security 41, must not 37, validate 29, overflow 26, xxx 25, warning 19
- periph: 20,069 births; commented 33% (others 54%); danger among commented 10% (others 13%); comment lines per loc 0.114 (others 0.127)
  - top danger words: must be 122, do not 83, assume 58, overflow 55, xxx 48, assumes 41, warning 32, security 27, must not 24, validation 19

- Role at the function's last live snapshot instead of birth (point interactions):
  - CMR-FD hub latent: 0.61
  - CMR-FD hub regression: 0.47
  - CMR-FD hub extrinsic: 0.81
  - CMR-FD orch latent: 0.92
  - CMR-FD orch regression: 1.16
  - CMR-FD orch extrinsic: 1.28
  - CMR-FD periph latent: 0.84
  - CMR-FD periph regression: 2.18
  - CMR-FD periph extrinsic: 0.85
  - CMR-FC hub latent: 0.71
  - CMR-FC hub regression: 1.06
  - CMR-FC hub extrinsic: 0.99
  - CMR-FC orch latent: 1.19
  - CMR-FC orch regression: 1.59
  - CMR-FC orch extrinsic: 1.50
  - CMR-FC periph latent: 0.76
  - CMR-FC periph regression: 0.67
  - CMR-FC periph extrinsic: 0.86

- Per repo, CMR-FD latent within role (RR in / RR out):
  - curl (8,291 births): hub 0.61/1.24; orch 1.47/1.12; periph 1.17/1.27
  - openssl (26,264 births): hub nan/1.64; orch 1.59/1.62; periph 1.70/1.60
  - ndpi (2,220 births): hub nan/1.90; orch 0.91/2.02; periph 0.24/4.30
  - harfbuzz (6,218 births): hub nan/1.72; orch 2.77/1.63; periph 2.31/1.68
  - libarchive (5,221 births): hub nan/nan; orch nan/nan; periph nan/nan

Runtime 172s · seed 2982.

## Run record

- Engine gitgalaxy `14e700054` (Prism comment split), melek, 2026-11-11. CGT networks from
  `gitgalaxy/cgt-study/scratch/net_<repo>.pkl`; `SFS_SRC` = the r3-lattice structural-fingerprint-scanner.
- **Coverage:** 48,214 births scored; 1,072 skipped (832 with no comment reading at the birth blob, 240 with no
  network node, almost all OpenSSL).
- **`nan` cells:** no events on one side. libarchive has no CVE-fix (`latent`) events in its panel. Hubs at birth are
  rare (1,604 births, 3%), so danger-commented hubs with CVE fixes number 4. The power rule marks these cells
  underpowered.

## Reading

**Part P: comments do sit differently by role, at equal size.**
- **Hubs are more often commented** (P1 1.33, z +4.8 ✓). The most-called functions, CGK's public workhorses, carry
  comments more often than same-size functions.
- **The periphery is less often commented** (P1 0.87, z −5.8 ✓). But when it is, it is **more often danger-worded**
  (P2 1.25, z +4.2 ✓). This is the predicted shape: private, low-level code (bit work, allocation) is seldom
  explained, and when it is, the comment is a warning.
- **Orchestrators are less often danger-worded** (P2 0.60, z −7.4 ✓), at equal size. P1 for orchestrators is not
  significant (0.87, z −2.9, above the 0.01/6 bar).
- **Size matters here.** In the raw shares, orchestrators look heavily commented (78% vs 42%) and more
  danger-worded (16% vs 11%). That is because they are big. Within loc strata, both reverse or vanish. That is why
  the registered test stratifies.

**Part F: no role changes what comments predict.** None of the 18 cells passes. Of the 18, 10 are n.s. with wide
CIs and 8 are underpowered, mostly hubs, plus periphery × danger × latent and regression.
- The largest point estimates (orchestrator × regression 1.2–1.6; periphery × regression 0.6 for any comment) are
  not significant.
- DC-2's danger → CVE link (about 1.4 outside every role) holds roughly evenly across roles, as far as this data
  can tell.

**Caveat.** Roles at birth are thin for hubs: functions gain callers over time (CGN-A2). The last-snapshot role rows
(descriptive) point the same mixed way.
