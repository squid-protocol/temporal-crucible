# UT-H1..H3 — unpatched twins of OpenSSL CVE-fixed functions (SCORED; aggregates only)

- post-fork OpenSSL CVE fixes: 192; (fix, function, fork) rows: 780; function in pre-fix query snapshot: 644
- fork function tables: boringssl 8,812, libressl 7,066

| claim | result | verdict |
|---|---|---|
| **UT-H1** twins are real copies | 13 / 21 accepted twins are textual copies (Jaccard ≥ 0.5) = **61.9%** (Wilson 99% lo 35.1%) | **not evaluable** |
| **UT-H2** renamed copies found | **0** twin copies under a different name | **not supported** |
| **UT-H3** audited-unpatched copies | 4 unpatched-looking twin copies; audit sample 4 — **pending manual audit** | **pending** |

## Descriptive

- **boringssl**: twin copies 0, status {}; name-match copies 18, status {'fix absent (addition-only)': 1, 'patched': 2, 'diverged': 15}
- **libressl**: twin copies 13, status {'unpatched-looking': 4, 'fix absent (addition-only)': 3, 'diverged': 5, 'patched': 1}; name-match copies 86, status {'unpatched-looking': 17, 'diverged': 36, 'fix absent (addition-only)': 12, 'patched': 21}
- twin recall on name-identified copies (same function retrieved): **12.5%** of 104
- rows with no fork counterpart by name or twin: 567 (code removed or never present in the fork)

Runtime 475s · seed 2982. Audit candidates are written to a private file outside the repo.
