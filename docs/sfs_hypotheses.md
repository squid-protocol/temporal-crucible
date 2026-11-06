# SFS — structural-fingerprint stability, name-free survival, and whether change tracks bugs — registered 2026-11-06, before any sfs statistic on these repos

**Tool.** `structural-fingerprint-scanner` (`sfs`, gitgalaxy-population-analyses `5685ec2`).
- It places every function in a fixed 37-dimensional reference frame, fitted on 8.2 M functions.
- It builds repo fingerprints and profile distances.
- It finds **structural twins**: functions measured almost identically, matched without names, at a calibrated
  false-twin rate.
- `retention` is `sfs timeline`'s measure: the share of the previous snapshot's eligible functions with a twin in the
  next snapshot.

**Why.**
- The owner asked how stable `sfs` fingerprints are, and whether bugs correlate with changes.
- `sfs` also gives a **name-free** function identity. That checks NH's name-based survival, whose known caveat is
  renames.
- It tests a three-bucket prediction: *structural turnover should go with regressions (change-driven), not with
  latent CVEs (old, frozen code)*.

**What has been looked at.** The `sfs` README and METHOD. No `sfs` output on these repos exists.

## Data

- **Snapshots.** From the NH quarterly scans (same DBs and engines: curl and nDPI `e246915aa`; openssl, harfbuzz and
  libarchive `da852aa54`): the **first snapshot of each calendar year**.
- Each is exported to a single-commit DB: its `file_data`, `function_data` and `repo_data` rows. `sfs` reads one
  commit per DB.
- These DBs have no persisted call edges (`fcall_data` empty), so `sfs`'s call-graph-shape component is zero for every
  snapshot alike. All other components are unaffected.
- **sfs settings (defaults):** structure lens, `--min-loc 3`, `--twin-min-loc 6`, ratio 0.8, FDR 0.01.
- **Fix labels:** XC (`events/*_xc.json`, rules v2). harfbuzz's latent class comes from `events/harfbuzz.json` OSV
  security fixes, with those SHAs removed from its other classes, as in INP.
- Year y's window is from snapshot y to snapshot y + 1.

## Claims

| id | claim | measure | supported iff |
|---|---|---|---|
| **SFS-H1** | **sfs fingerprints are stable project identities** | nearest neighbour by `sfs` profile distance (one cohort of all yearly snapshots), excluding same-repo snapshots < 5 y apart | accuracy ≥ 0.90 (chance 0.20) |
| **SFS-H2** | **name-free survival agrees with name-based survival** | per repo-year: `retention` against NH's name-based survival (share of year-y functions of ≥ 6 lines present a year later, by (file, name) or NH's move rule) | Spearman ρ over repo-years ≥ 0.50 |
| **SFS-H3** | **structural change goes with regressions** | per repo-year: turnover = 1 − retention, against regression share = regression commits / all labelled fix commits in the year | mean within-repo Spearman > 0, permutation p < 0.01 (years permuted within repo, 10,000 rounds) |
| **SFS-H4** | **…and not with CVEs** (the three-bucket prediction) | mean within-repo [ρ(turnover, regression share) − ρ(turnover, latent share)] | > 0, permutation p < 0.01 |

**Repos per claim.**
- H1, H2: all five.
- H3, H4: curl, nDPI, openssl, harfbuzz. libarchive's regression labels are withheld, and it has too few CVEs.
- Repo-years with < 5 labelled fix commits are dropped from H3/H4.

**Descriptive.**
- Per repo: retention by year, the largest-turnover years, and profile distance to the first snapshot.
- Extrinsic share against turnover (placebo direction unknown, so no claim).

## Priors

- SFS-H1 **leaning supported**: SIG's keyword fingerprint reached 95.9%.
- SFS-H2 **leaning supported**: renames are a small share of deaths.
- SFS-H3 **uncertain**: regressions follow activity (XC), but share-of-fixes is a noisy yearly quantity.
- SFS-H4 **uncertain**.
