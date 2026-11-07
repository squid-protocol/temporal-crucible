# SEM2-H1..H3 (new fragments only) — semantic 'fixed differently' patch check (SCORED; aggregates only)

- units 6,155 (VZ-T's); verbatim-truth units 1,552

| claim | result | verdict |
|---|---|---|
| **SEM2-H1** no new errors on verbatim truth | wrong calls 0 / 1552 (line check: 0); Wilson 99% upper 0.43% | **SUPPORTED** |
| **SEM2-H2** meets VZ-T bars | sensitivity 919/1127 = 81.5% (lo 78.4%); specificity 310/425 = 72.9% (lo 67.1%) | **not supported** |
| **SEM2-H3** beats line check, fresh audit | SEM correct 19/20, line correct 15/20 | **SUPPORTED** |

## Descriptive

- guard fragments per CVE: {'eff308af4': 1, '1eb7682f8': 1, '5c44459c3': 5, '6a043145c': 3, '9aaec95e8': 0, 'e54e12994': 0, 'd1d577490': 0}
- abstention rate: line 26.5% → SEM 26.1%
- verdict changes line → SEM (all units): {('unpatched', 'patched'): 135, ('undetermined', 'patched'): 25}
- VZ-T's first audit sample (in-sample, the design example): (line, SEM) = {('patched', 'patched'): 13, ('unpatched', 'patched'): 4, ('unpatched', 'unpatched'): 3}

Runtime 21s.
