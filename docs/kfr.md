# KF-R and KF-L — replication and localization of goto ↔ lifetime faults (SCORED)

## KF-R — file level, five unseen repos

- events with a scanned T0 and ≥ 1 touched C file: 78; types: file/bounds 16, file/lifetime 5, file/other 3, libexif/bounds 7, libexif/other 4, libtiff/lifetime 2, libxml2/bounds 19, libxml2/lifetime 22
- G3 power: lifetime 29, bounds 42 → PASS

| claim | estimate | one-sided lo (α=0.0025) | 90% CI | verdict |
|---|---:|---:|---|---|
| **KFR-H1** RR(goto), all security fixes | 2.804 | 1.121 | [1.581, 6.909] | **SUPPORTED** |
| **KFR-H3** RR(goto \| lifetime) / RR(goto \| bounds) | 0.536 | 0.018 | [0.102, 2.120] | **not supported (inconclusive)** |

Descriptive: RR(goto | lifetime) 2.06, RR(goto | bounds) 3.83, RR(goto, 50 LOC bins) lifetime 1.82 / bounds 2.07; libxml2: RR(goto) 3.34 (41 events); libtiff: RR(goto) 0.56 (2 events); libexif: RR(goto) 0.00 (11 events); file: RR(goto) 4.50 (24 events)

## KF-L — function level (nDPI, openssl, libxml2, libtiff, libpng, libexif; file excluded by G1)

- events: 387 (lifetime 50, bounds 140); median functions per event 29; median share of candidate functions containing goto 9.5%

| claim | estimate | one-sided lo (α=0.0025) | 90% CI | verdict |
|---|---:|---:|---|---|
| **KFL-H1** RR(goto-function \| lifetime) | 2.072 | 0.766 | [1.204, 3.362] | **not supported** |
| **KFL-H2** RR(goto-function \| lifetime) / RR(goto-function \| bounds) | 1.024 | 0.329 | [0.542, 1.814] | **not supported (inconclusive)** |

Descriptive per repo (function level): ndpi: lifetime RR 1.51 (14), bounds RR 2.89 (80); openssl: lifetime RR 4.32 (12), bounds RR 0.90 (36); libxml2: lifetime RR 2.01 (22), bounds RR 2.19 (19); libtiff: lifetime RR 0.00 (2), bounds RR nan (0); libpng: lifetime RR nan (0), bounds RR nan (0); libexif: lifetime RR nan (0), bounds RR nan (5)

Runtime 286s · event bootstrap 5000 rounds, seed 2982.
