# Exposure history report — curl

Generated 2026-11-05 00:31 · engine scans temporally ablated (asserted: max |temporal Δ| = 0.0) · DB `curl_galaxy_master.db` · events pinned to pool HEAD `04bfe8fbbf55` · **PRELIMINARY — batch incomplete**

## Coverage

| class | analyzed | pending/skipped | of harvested |
|---|---|---|---|
| security-fix | 185 | 0 | 186 |
| control | 172 | 0 | 185 |
| introduced | 132 | 1 | 137 |

## Pre-registered hypotheses (gitgalaxy#2982; unit = event, mean structural Δ over its touched files)

| test | n | median Δ | vs | n | median Δ | p (one-sided MW) | verdict at α=0.01 |
|---|---|---|---|---|---|---|---|
| **H1** fixes < controls | 185 | +0.000 | controls | 172 | +0.000 | 0.3321 | not supported |
| **H2** introduced > controls | 132 | +0.007 | controls | 172 | +0.000 | 0.0422 | not supported |

Per-file pooled secondary (pseudo-replicated, labeled as such): H1 p = 0.0900 over 475 fix-file vs 443 control-file deltas; H2 p = 0.9686.

## H3 — which vectors carry it (event-level medians)

| vector | fixes | controls | introduced | H1 p |
|---|---|---|---|---|
| tech_debt | -0.003 | +0.000 | -0.011 | 0.0008 |
| safety_score | -0.004 | +0.000 | +0.000 | 0.0086 |
| dead_code | +0.000 | +0.000 | -0.000 | 0.0936 |
| spec_match | +0.000 | +0.000 | +0.000 | 0.1512 |
| state_flux | +0.000 | +0.000 | +0.000 | 0.1571 |
| api_exposure | -0.000 | +0.000 | +0.000 | 0.2573 |
| verification | +0.000 | +0.000 | +0.000 | 0.3374 |
| concurrency | +0.000 | +0.000 | +0.000 | 0.6686 |
| secrets_risk | +0.000 | +0.000 | +0.000 | 0.8025 |
| documentation | +0.000 | +0.000 | +0.000 | 0.8336 |
| cognitive_load | +0.004 | +0.000 | +0.000 | 0.9710 |

## Sign split — does a fix *reduce* exposure?

| class | Δ<0 (reduced) | Δ>0 (raised) | Δ=0 |
|---|---|---|---|
| security-fix | 85 (46%) | 79 (43%) | 21 |
| control | 72 (42%) | 63 (37%) | 37 |
| introduced | 54 (41%) | 70 (53%) | 8 |

The first pilot sample predicted this split: guard code added by a fix reads as complexity (dead_code, cognitive_load), so a security fix RAISING structural exposure is not a scan error — whether the *distribution* differs from controls is what H1 asks.

## Severity gradient (security fixes)

| severity | n | median Δ | p25 | p75 |
|---|---|---|---|---|
| Critical | 2 | -41.780 | -82.943 | -0.617 |
| High | 28 | +0.000 | -0.105 | +0.039 |
| Medium | 79 | +0.000 | -0.072 | +0.094 |
| Low | 76 | -0.001 | -0.131 | +0.045 |

## Top movers (security fixes, event mean Δ)

| direction | CVE | Δ | files touched |
|---|---|---|---|
| ↓ largest drop | CURL-CVE-2013-0249 | -82.943 | 1 |
| ↓ largest drop | CURL-CVE-2023-28321 | -20.935 | 3 |
| ↓ largest drop | CURL-CVE-2016-8615 | -12.129 | 1 |
| ↓ largest drop | CURL-CVE-2023-46219 | -6.475 | 1 |
| ↓ largest drop | CURL-CVE-2026-6253 | -5.420 | 3 |
| ↑ largest rise | CURL-CVE-2026-11586 | +47.090 | 2 |
| ↑ largest rise | CURL-CVE-2018-1000121 | +21.184 | 1 |
| ↑ largest rise | CURL-CVE-2026-5545 | +17.040 | 1 |
| ↑ largest rise | CURL-CVE-2026-11564 | +5.550 | 3 |
| ↑ largest rise | CURL-CVE-2026-8925 | +4.824 | 1 |

## CVE hotspot files (appearances across fix+introduced events)

| file | events |
|---|---|
| `lib/url.c` | 94 |
| `lib/urldata.h` | 80 |
| `lib/http.c` | 41 |
| `include/curl/curl.h` | 30 |
| `lib/transfer.c` | 30 |
| `lib/vtls/openssl.c` | 28 |
| `tests/data/Makefile.inc` | 27 |
| `lib/Makefile.inc` | 26 |
| `lib/setopt.c` | 24 |
| `lib/ftp.c` | 23 |

## Are the outliers where security events happen?

Each implicated file's **structural-exposure percentile within its parent snapshot** (all files ranked, before the event was known). Random targeting reads ~50; if GitGalaxy's high-exposure files are where CVEs live, security classes read high — a rung-7 preview from rung-6 data.

| class | files | median pre-event percentile | p25 | p75 |
|---|---|---|---|---|
| security-fix | 475 | 86.9 | 53.1 | 91.8 |
| introduced | 954 | 84.8 | 43.7 | 92.5 |
| control | 443 | 86.7 | 46.0 | 92.2 |

fix-files sit above control-files with one-sided MW p = 0.2469 (controls < fixes).

## CWE × vector — which exposure vector flags which weakness type?

Median **pre-event per-vector percentile** of implicated files (each file ranked per vector among all files in its parent snapshot). Reading guide: a high cell means files that later carried this weakness class already stood out on that vector before the event. Control-file rows give the baseline 'changed files look like this anyway' profile.

| class (events) | cognitive_load | safety_score | state_flux | api_exposure | verification | tech_debt | documentation | concurrency |
|---|---|---|---|---|---|---|---|---|
| memory (103) | 84 | 75 | 81 | 50 | 82 | 75 | 51 | 0 |
| other (99) | 85 | 76 | 81 | 50 | 81 | 76 | 52 | 0 |
| cert/auth (65) | 86 | 71 | 80 | 50 | 82 | 77 | 54 | 0 |
| info-leak (50) | 87 | 80 | 82 | 51 | 82 | 76 | 53 | 0 |
| control baseline (172) | 86 | 73 | 82 | 48 | 83 | 77 | 54 | 0 |

**Fix-delta by weakness family** (median event Δ, security fixes only): 
other -0.007 (n=58) · memory +0.000 (n=58) · cert/auth +0.001 (n=36) · info-leak +0.000 (n=33)

## First look over time (event-sampled snapshots, 5-year eras)

Repo-mean structural exposure and implicated-file percentiles per era. **Caveats before believing a trend**: sampling is event-biased (snapshots exist where CVEs were fixed/introduced), the codebase grows (absolute scores drift with file size — percentiles are the robust reading), and deleted files leave the panel (survivorship). The phase-W walk replaces this with a uniform panel.

| era | snapshots | repo files (median) | repo-mean structural exposure (median) | implicated-file percentile (median) |
|---|---|---|---|---|
| 2000–2004 | 22 | 162 | 249.14 | 88.0 |
| 2005–2009 | 19 | 348 | 243.03 | 70.5 |
| 2010–2014 | 50 | 570 | 257.50 | 79.8 |
| 2015–2019 | 115 | 678 | 256.12 | 86.5 |
| 2020–2024 | 172 | 862 | 253.47 | 86.5 |
| 2025–2029 | 111 | 1111 | 260.27 | 87.2 |

## Commit anatomy — what fixes and introductions physically are

| class | n | commits touching any TODO/FIXME/HACK | net markers | median net LOC | net-growing |
|---|---|---|---|---|---|
| security-fix | 185 | 1 | -1 | +6 | 142/185 (77%) |
| control | 172 | 2 | +2 | +3 | 110/172 (64%) |
| introduced | 132 | 24 | +89 | +88 | 115/132 (87%) |

**The tech_debt autopsy**: the H3 tech_debt drop in fixes coexists with fixes almost never touching a debt marker — the drop is the DENSITY DENOMINATOR (same markers over more lines; fixes net-add code). A formula artifact in the #2655/#2979 shape, caught by this table. The introduced side is real: vulnerability-introducing commits are large feature additions that carry new debt markers with them.

## Dwell time — how long vulnerabilities lurk

Introduced → fixed, n = 137 CVEs with both commits: median **4.5 years** (p25 1.3y, p75 11.4y, max 25.2y). The strategic number for rung 7: a predictive instrument has a years-long window in which flagging the file would have mattered.

## Security-system signals on implicated files

- **Credential shunt** (`has_credentials` / `risk_secrets_risk=100`): fires on 41339 file-rows across history — test keys and CA tooling (e.g. `stunnel.pem`, `stunnel.pem`, `ca-bundle.crt`, `mk-ca-bundle.pl`) — but on **8 of 416 CVE/control-implicated files**. The secrets surface and the vulnerability surface are orthogonal in curl: CVEs live in protocol code, credentials in test fixtures.
- **ML threat layer** (`ai_threat_score`, `is_malware`, `binary_anomaly`, `obfuscation_flag`): all zero in these scans — the scan environment lacks the ML dependencies (the engine's known security_auditor ML-deps gap), so this layer is UNEXERCISED here, not exonerated. A full-deps rerun is the test.
- **Granular lens counts** (`sec_tainted_injection`, `sec_db_hooks`, …) are not persisted to the scan DB (audit-JSON only) — adding them to `file_data` (or capturing audit JSONs in the harness) is the enabling change for a per-CVE injection-surface analysis. Filed as future work in the epic.

## Instrument controls

- **Untouched-file spillover** (files the commit did not touch; expected ~0, graph ripple via api_exposure is the legitimate exception): n = 391297, median |Δ| = 0.000000, p99 = 0.0000, max = 5.0203.
- **LOC coupling** on touched files (is Δ just size change?): Spearman ρ = -0.210 over 918 files. The length-leak lesson says watch this; a high ρ routes to the score-contract program, not to a corpus tweak.
- **Temporal ablation**: asserted exactly 0.0 across every delta in this run.

---
*Regenerate: `python tools/delta_report.py --events events/curl.json` — reads only the events file and the history DB; every number above is a pure function of those two artifacts.*
