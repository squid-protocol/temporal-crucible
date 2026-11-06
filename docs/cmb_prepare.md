# CMB-H1..H3 — zlib + expat; SEM-2 vs closest-version (SCORED; aggregates only)

- fixes: zlib 7, expat 37; host states 956; units 12,023

| claim | result | verdict |
|---|---|---|
| **CMB-H1** SEM-2 no new errors on expat verbatim truth | wrong 687 / 3228; Wilson 99% upper 23.20% | **not supported** |

## Per library and method (descriptive)

| library | method | verbatim accuracy (decided) | wrong calls | coverage (all units) |
|---|---|---:|---:|---:|
| zlib | sem2 | 1229/1229 | 0 | 74% |
| zlib | line | 1229/1229 | 0 | 73% |
| zlib | cv | 1552/1552 | 0 | 62% |
| zlib | ver | 1551/1552 | 1 | 100% |
| expat | sem2 | 1755/2442 | 687 | 70% |
| expat | line | 1830/2400 | 570 | 68% |
| expat | cv | 3228/3228 | 0 | 100% |
| expat | ver | 3191/3191 | 0 | 99% |

- audit sample (SEM-2 vs CV disagreements, non-verbatim): 60 units; zlib 30, expat 30
- non-verbatim SEM-2 × CV (both decided): {('zlib', 'unpatched', 'unpatched'): 951, ('zlib', 'patched', 'patched'): 786, ('zlib', 'unpatched', 'patched'): 64, ('zlib', 'patched', 'unpatched'): 53, ('expat', 'unpatched', 'unpatched'): 806, ('expat', 'patched', 'unpatched'): 501, ('expat', 'patched', 'patched'): 339, ('expat', 'unpatched', 'patched'): 6}

Runtime 114s · seed 2985.
