# KF-R / KF-L gates (2026-11-06, before any KF-R/KF-L statistic)

**G1 — engine function extraction vs tree-sitter (engine `32619e4a5`, head snapshots, `tools/engine_validate.py`).**
Gate: tree-sitter R and P ≥ 95, span start and end exact ≥ 95.

| repo | functions vs tree-sitter R / P | vs ctags R / P | span start / end exact | G1 |
|---|---|---|---|---|
| libxml2 | 98.99 / 98.27 | 99.89 / 98.99 | 99.19 / 98.75 | PASS |
| file | **94.03** / 100.0 | 94.56 / 98.69 | 99.34 / 99.56 | **FAIL**: excluded from KF-L (kept in KF-R) |
| libexif | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | PASS |
| libtiff | 95.94 / 99.15 | 98.39 / 100.0 | 99.33 / 99.94 | PASS |
| libpng | 97.95 / 99.40 | 94.68 / 95.31 | 99.26 / 99.11 | PASS |

nDPI and openssl passed earlier (`engine_validation.md`).

**G2 — construct regex vs tree-sitter-c:** **PASS**. Exposure agreement is goto 99.76% and macro 99.86% pooled over
eight repos. Detail: `kf_construct_validation.md`. Regex-only disagreements are `goto` in comments and in multi-line
macro bodies, plus a few `#define`s tree-sitter does not parse.

**G3 — power:** **PASS**. Pooled over the new repos: lifetime 29 events (libxml2 22, file 5, libtiff 2), bounds 44
(libxml2 19, file 17, libexif 7, libpng 1), from the OSV harvest.
