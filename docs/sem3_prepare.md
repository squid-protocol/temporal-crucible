# S3-H1..H2 — SEM-3 (new-to-file fix lines) on zlib + expat (SCORED; aggregates only)

- units 12,023; host states 956

| claim | result | verdict |
|---|---|---|
| **S3-H1** no new errors on verbatim truth, each library | zlib: wrong 0/1258 decided (upper 0.52%), coverage 81% of 1552 verbatim; expat: wrong 74/1509 decided (upper 6.54%), coverage 47% of 3228 verbatim | **not supported** |
- audit packets 60 (zlib 30, expat 30); packets starting at a file header: 0

## Descriptive

- zlib sem3: verbatim wrong 0/1258; coverage all units 71%
- zlib sem2: verbatim wrong 0/1229; coverage all units 74%
- zlib cv: verbatim wrong 0/1552; coverage all units 62%
- expat sem3: verbatim wrong 74/1509; coverage all units 43%
- expat sem2: verbatim wrong 687/2442; coverage all units 70%
- expat cv: verbatim wrong 0/3228; coverage all units 100%
- CMB's audited units (in-sample; motivated the design): {('zlib', 'sem3 right'): 23, ('zlib', 'sem3 wrong/abstain'): 7, ('expat', 'sem3 wrong/abstain'): 22, ('expat', 'sem3 right'): 4}

Runtime 136s · seed 2986.
