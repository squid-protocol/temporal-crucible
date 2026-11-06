# ARCH-S — archetype stability: curl

- DB `.claude/worktrees/rescan-engine-32619e4a5/dbs/curl_out/curl_galaxy_master.db` · 3547 snapshots, 2000-02-21 .. 2026-09-08 · C files only

## S1 — determinism gate (unchanged blob between consecutive snapshots)

| label | pairs | same label | bar | gate |
|---|---:|---:|---:|---|
| file cluster (`file_archetype`) | 2,090,684 | 1.00000 | 0.999 | **PASS** |
| function (`func_archetype`), matched by (name, start_line) | 10,040,924 | 1.00000 | 0.999 | **PASS** |
| S4: composition (`composition_file_archetype`) — not gated | 2,090,684 | 1.00000 | — | (context-sensitive by design) |

## S2 — retention under edits (changed blob between consecutive snapshots)

| relative edit \|Δcoding_loc\|/coding_loc | pairs | file cluster kept | κ | composition kept |
|---|---:|---:|---:|---:|
| 0 (LOC equal) | 20,067 | 0.994 | 0.993 | 0.993 |
| (0, 1%] | 12,389 | 0.992 | 0.990 | 0.995 |
| (1, 5%] | 7,572 | 0.962 | 0.956 | 0.971 |
| (5, 20%] | 3,059 | 0.888 | 0.860 | 0.923 |
| > 20% | 1,210 | 0.789 | 0.704 | 0.802 |

**S2 bar** (file cluster, (0, 5%] bins combined): retention **0.980** on 19,961 pairs → **trackable** (bar 0.9).

Functions in changed files, matched by name: same (loc, complexity) kept label 0.9991 (n=621,448); changed shape kept 0.699 (n=43,202).

## S3 — one-year horizon (file cluster)

- origins: every 23 snapshot(s); pairs 74,268; agreement 0.929, κ 0.914
- unchanged over the year: kept 1.0000 (n=14,724); changed: kept 0.912 (n=59,544)
- distinct file-cluster labels over a file's life (files seen in ≥ 10 snapshots, n=1,339): 1: 65.2%, 2: 22.9%, 3: 7.7%, 4: 2.8%, 5: 1.3%, 6+: 0.1%

## S5 — does a thin centroid margin predict a flip? (changed files)

| margin decile (d₂ − d₁) | range | pairs | flip rate |
|---|---|---:|---:|
| 1 | 0.000–0.482 | 4,427 | 0.083 |
| 2 | 0.482–1.022 | 4,430 | 0.046 |
| 3 | 1.022–1.628 | 4,428 | 0.020 |
| 4 | 1.628–2.081 | 4,431 | 0.014 |
| 5 | 2.081–2.535 | 4,429 | 0.013 |
| 6 | 2.535–2.877 | 4,425 | 0.006 |
| 7 | 2.877–3.893 | 4,437 | 0.009 |
| 8 | 3.893–5.363 | 4,428 | 0.018 |
| 9 | 5.363–9.416 | 4,430 | 0.018 |
| 10 | 9.416–44.235 | 4,431 | 0.025 |

## Population drift (file-cluster distribution, JSD bits)

- consecutive snapshots: median 0.0000, p99 0.0020
- vs first snapshot, at the end: 0.147

Runtime 293s.
