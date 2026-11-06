# KF-H1..H4 — construct split and keyword → fault type (SCORED)

- events: 344 (nDPI + openssl pooled); fault types: ndpi/bounds 81, ndpi/lifetime 14, ndpi/other 15, openssl/bounds 37, openssl/lifetime 12, openssl/other 185
- files exposed (median per T0): goto 36.9%, function-like macro 20.0%

| claim | what | estimate | one-sided lo (α=0.0025) | 90% CI | verdict |
|---|---|---:|---:|---|---|
| **KF-H1** | RR(goto), all security fixes | 1.587 | 1.234 | [1.371, 1.897] | **SUPPORTED** |
| **KF-H2** | RR(function-like macro), all security fixes | 1.341 | 1.052 | [1.150, 1.575] | **SUPPORTED** |
| **KF-H3** | RR(goto | lifetime) / RR(goto | bounds) | 7.123 | 2.767 | [3.881, 25.042] | **SUPPORTED** |
| **KF-H4** | RR(macro | bounds) / RR(macro | lifetime) | 1.419 | 0.300 | [0.604, 2.976] | **not supported (inconclusive)** |

## Descriptive (no verdicts)

| subset | events | RR goto | RR macro | RR goto (50 LOC bins) | RR macro (50 LOC bins) |
|---|---:|---:|---:|---:|---:|
| all | 344 | 1.59 | 1.34 | 1.26 | 1.31 |
| bounds | 118 | 1.87 | 2.21 | 1.19 | 2.22 |
| lifetime | 26 | 13.30 | 1.56 | 6.27 | 2.11 |
| other | 200 | 1.35 | 1.10 | 1.20 | 1.10 |
| ndpi all | 110 | 2.35 | 2.16 | 1.64 | 2.58 |
| openssl all | 234 | 1.24 | 1.10 | 1.13 | 1.11 |
| curl all (context, never scored) | 185 | 1.09 | 1.63 | 0.90 | 1.23 |
| curl bounds (context) | 41 | 1.11 | 1.35 | 0.95 | 1.75 |
| curl lifetime (context) | 20 | 1.08 | 1.82 | 0.93 | 1.24 |

Runtime 210s · event bootstrap 5000 rounds, seed 2982.
