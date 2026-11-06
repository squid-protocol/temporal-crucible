# ARCH-S — archetype stability: openssl

- DB `.claude/worktrees/frec/dbs/openssl_out/openssl_galaxy_master.db` · 110 snapshots, 1998-12-31 .. 2026-03-31 · C files only

## S1 — determinism gate (unchanged blob between consecutive snapshots)

| label | pairs | same label | bar | gate |
|---|---:|---:|---:|---|
| file cluster (`file_archetype`) | 90,614 | 0.99997 | 0.999 | **PASS** |
| function (`func_archetype`), matched by (name, start_line) | 501,706 | 1.00000 | 0.999 | **PASS** |
| S4: composition (`composition_file_archetype`) — not gated | 90,614 | 0.99992 | — | (context-sensitive by design) |

File-cluster changes on unchanged blobs (first 10): `crypto/evp/c_allc.c` file_cluster_17→file_cluster_2 (212a08080c→01f06617b1); `crypto/ts/ts_conf.c` file_cluster_15→file_cluster_16 (9c119bc6b5→e382f507fb); `crypto/ts/ts_conf.c` file_cluster_16→file_cluster_15 (e382f507fb→4dcb150ea3)

## S2 — retention under edits (changed blob between consecutive snapshots)

| relative edit \|Δcoding_loc\|/coding_loc | pairs | file cluster kept | κ | composition kept |
|---|---:|---:|---:|---:|
| 0 (LOC equal) | 12,700 | 0.994 | 0.993 | 0.995 |
| (0, 1%] | 6,770 | 0.987 | 0.985 | 0.987 |
| (1, 5%] | 8,161 | 0.950 | 0.944 | 0.967 |
| (5, 20%] | 5,051 | 0.870 | 0.854 | 0.914 |
| > 20% | 2,133 | 0.659 | 0.614 | 0.742 |

**S2 bar** (file cluster, (0, 5%] bins combined): retention **0.967** on 14,931 pairs → **trackable** (bar 0.9).

Functions in changed files, matched by name: same (loc, complexity) kept label 0.9983 (n=366,731); changed shape kept 0.840 (n=43,393).

## S3 — one-year horizon (file cluster)

- origins: every 1 snapshot(s); pairs 115,546; agreement 0.947, κ 0.941
- unchanged over the year: kept 1.0000 (n=50,489); changed: kept 0.905 (n=65,057)
- distinct file-cluster labels over a file's life (files seen in ≥ 10 snapshots, n=2,695): 1: 64.5%, 2: 23.6%, 3: 8.6%, 4: 2.6%, 5: 0.5%, 6+: 0.3%

## S5 — does a thin centroid margin predict a flip? (changed files)

| margin decile (d₂ − d₁) | range | pairs | flip rate |
|---|---|---:|---:|
| 1 | 0.000–0.357 | 3,471 | 0.132 |
| 2 | 0.357–0.782 | 3,485 | 0.075 |
| 3 | 0.782–1.220 | 3,488 | 0.060 |
| 4 | 1.220–1.650 | 3,481 | 0.045 |
| 5 | 1.650–2.139 | 3,480 | 0.044 |
| 6 | 2.139–2.677 | 3,482 | 0.031 |
| 7 | 2.677–3.401 | 3,481 | 0.022 |
| 8 | 3.401–5.203 | 3,481 | 0.048 |
| 9 | 5.203–10.753 | 3,480 | 0.054 |
| 10 | 10.753–43.972 | 3,483 | 0.053 |

## Population drift (file-cluster distribution, JSD bits)

- consecutive snapshots: median 0.0001, p99 0.0059
- vs first snapshot, at the end: 0.093

Runtime 12s.
