# SEM-H1..H3 — semantic 'fixed differently' patch check (SCORED; aggregates only)

- units 6,155 (VZ-T's); verbatim-truth units 1,552

| claim | result | verdict |
|---|---|---|
| **SEM-H1** no new errors on verbatim truth | wrong calls 227 / 1552 (line check: 0); Wilson 99% upper 17.09% | **not supported** |
| **SEM-H2** meets VZ-T bars | sensitivity 726/1127 = 64.4% (lo 60.7%); specificity 387/425 = 91.1% (lo 86.8%) | **not supported** |
| **SEM-H3** beats line check, fresh audit | SEM correct 17/20, line correct 12/20 | **SUPPORTED** |

## Descriptive

- guard fragments per CVE: {'CVE-2022-37434': 1, 'CVE-2018-25032': 5, 'CVE-2016-9840': 3, 'CVE-2016-9841': 0, 'CVE-2016-9842': 2, 'CVE-2016-9843': 0}
- abstention rate: line 26.5% → SEM 15.2%
- verdict changes line → SEM (all units): {('undetermined', 'patched'): 699, ('unpatched', 'patched'): 804}
- VZ-T's first audit sample (in-sample, the design example): (line, SEM) = {('patched', 'patched'): 13, ('unpatched', 'patched'): 4, ('unpatched', 'unpatched'): 3}

Runtime 53s.
