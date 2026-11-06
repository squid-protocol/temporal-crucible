# ARCH-S — archetype stability: ndpi

- DB `.claude/worktrees/frec/dbs/ndpi_out/ndpi_galaxy_master.db` · 555 snapshots, 2019-07-10 .. 2026-05-02 · C files only

## S1 — determinism gate (unchanged blob between consecutive snapshots)

| label | pairs | same label | bar | gate |
|---|---:|---:|---:|---|
| file cluster (`file_archetype`) | 131,940 | 0.99993 | 0.999 | **PASS** |
| function (`func_archetype`), matched by (name, start_line) | 622,824 | 1.00000 | 0.999 | **PASS** |
| S4: composition (`composition_file_archetype`) — not gated | 131,940 | 0.99998 | — | (context-sensitive by design) |

File-cluster changes on unchanged blobs (first 10): `fuzz/fuzz_ndpi_reader_alloc_fail.c` file_cluster_16→file_cluster_12 (f3ec1cca05→6eb2256ce6); `fuzz/fuzz_ndpi_reader_payload_analyzer.c` file_cluster_16→file_cluster_12 (f3ec1cca05→6eb2256ce6); `fuzz/fuzz_ndpi_reader_pl7m.c` file_cluster_16→file_cluster_12 (f3ec1cca05→6eb2256ce6); `fuzz/fuzz_ndpi_reader_pl7m_64k.c` file_cluster_16→file_cluster_12 (f3ec1cca05→6eb2256ce6); `fuzz/fuzz_ndpi_reader_pl7m_internal.c` file_cluster_16→file_cluster_12 (f3ec1cca05→6eb2256ce6); `fuzz/fuzz_ndpi_reader_pl7m_only_subclassification.c` file_cluster_16→file_cluster_12 (f3ec1cca05→6eb2256ce6); `fuzz/fuzz_ndpi_reader_pl7m_randomize_ports.c` file_cluster_16→file_cluster_12 (f3ec1cca05→6eb2256ce6); `fuzz/fuzz_ndpi_reader_pl7m_simplest.c` file_cluster_16→file_cluster_12 (f3ec1cca05→6eb2256ce6); `fuzz/fuzz_ndpi_reader_pl7m_simplest_internal.c` file_cluster_16→file_cluster_12 (f3ec1cca05→6eb2256ce6)

## S2 — retention under edits (changed blob between consecutive snapshots)

| relative edit \|Δcoding_loc\|/coding_loc | pairs | file cluster kept | κ | composition kept |
|---|---:|---:|---:|---:|
| 0 (LOC equal) | 2,250 | 0.989 | 0.987 | 0.967 |
| (0, 1%] | 1,326 | 0.990 | 0.988 | 0.997 |
| (1, 5%] | 1,075 | 0.968 | 0.963 | 0.950 |
| (5, 20%] | 580 | 0.916 | 0.899 | 0.945 |
| > 20% | 252 | 0.639 | 0.566 | 0.762 |

**S2 bar** (file cluster, (0, 5%] bins combined): retention **0.980** on 2,401 pairs → **trackable** (bar 0.9).

Functions in changed files, matched by name: same (loc, complexity) kept label 0.9985 (n=120,404); changed shape kept 0.919 (n=5,248).

## S3 — one-year horizon (file cluster)

- origins: every 3 snapshot(s); pairs 38,900; agreement 0.906, κ 0.884
- unchanged over the year: kept 1.0000 (n=4,727); changed: kept 0.893 (n=34,173)
- distinct file-cluster labels over a file's life (files seen in ≥ 10 snapshots, n=501): 1: 74.7%, 2: 19.0%, 3: 5.4%, 4: 0.6%, 5: 0.2%, 6+: 0.2%

## S5 — does a thin centroid margin predict a flip? (changed files)

| margin decile (d₂ − d₁) | range | pairs | flip rate |
|---|---|---:|---:|
| 1 | 0.003–0.266 | 546 | 0.095 |
| 2 | 0.266–0.637 | 550 | 0.045 |
| 3 | 0.637–1.085 | 548 | 0.047 |
| 4 | 1.085–1.584 | 549 | 0.040 |
| 5 | 1.584–2.095 | 548 | 0.024 |
| 6 | 2.095–2.605 | 549 | 0.020 |
| 7 | 2.605–4.737 | 548 | 0.022 |
| 8 | 4.737–6.389 | 548 | 0.016 |
| 9 | 6.389–9.877 | 547 | 0.029 |
| 10 | 9.877–20.736 | 550 | 0.045 |

## Population drift (file-cluster distribution, JSD bits)

- consecutive snapshots: median 0.0000, p99 0.0028
- vs first snapshot, at the end: 0.148

Runtime 26s.
