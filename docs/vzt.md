# VZT-H1..H2 — vendored zlib through time (SCORED; aggregates only)

- host states (distinct vendored-zlib trees): 791 over 12 hosts; units (state × CVE file): **6,155**
- verbatim-upstream units: unpatched 1,127, patched 425; non-verbatim 4,603

| claim | result | Wilson 99% lo | verdict |
|---|---|---:|---|
| **VZT-H1** sensitivity (verbatim-unpatched called unpatched) | 919/1127 = 81.5% | 78.4% | **not supported** |
| **VZT-H2** specificity (verbatim-patched called patched) | 310/425 = 72.9% | 67.1% | **not supported** |

## Non-verbatim copies: code verdict × version verdict (descriptive)

| code \ version | patched | unpatched | no version |
|---|---:|---:|---:|
| patched | 1117 | 525 | 0 |
| unpatched | 254 | 1396 | 0 |
| undetermined | 962 | 349 | 0 |

- code-vs-version disagreements: **779**; audit sample 20 (private; audit labels added below by hand)
- verbatim units the check left undetermined: unpatched 208, patched 115

## Exposure windows (days from upstream fix release to the first state the code check calls patched; descriptive)

| CVE | hosts | median | min | max |
|---|---:|---:|---:|---:|
| CVE-2016-9840 | 12 | 266 | 5 | 1979 |
| CVE-2016-9841 | 12 | 266 | 5 | 1979 |
| CVE-2016-9842 | 1 | 804 | 804 | 804 |
| CVE-2016-9843 | 9 | 220 | 5 | 804 |
| CVE-2018-25032 | 12 | 49 | -1319 | 458 |
| CVE-2022-37434 | 11 | 70 | -67 | 455 |

Negative = the host carried the fix before the upstream release (it took the fix commit, or backported early).

Runtime 183s · seed 2982.
