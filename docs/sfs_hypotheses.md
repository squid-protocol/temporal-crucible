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

---

## Results — 2026-11-06 (scorer `401d08a` committed before running; report `sfs.md`)

103 yearly snapshots over 5 repos; `sfs` at population-analyses `5685ec2`.

| claim | result | verdict |
|---|---|---|
| **SFS-H1** fingerprints are stable identities | nearest-neighbour identification across eras ≥ 5 y apart: **99.0%** (chance 20%) | **SUPPORTED** |
| **SFS-H2** name-free retention agrees with name-based survival | Spearman **+0.49** over 98 repo-years (bar 0.50) | **not supported** (by 0.01) |
| **SFS-H3** structural turnover goes with regression share | mean within-repo ρ +0.16, permutation p 0.107 | **not supported** |
| **SFS-H4** …more than with CVE share | mean Δρ +0.15, p 0.194 | **not supported** |

Per repo, ρ(turnover, regression share): curl −0.27, nDPI +0.66, openssl +0.31, harfbuzz −0.06. Not consistent.

**What it means.**
1. **sfs fingerprints are even more stable than SIG's keyword mix** (99.0% vs 95.9%). A project's function-level design,
   placed in the 37-dimensional reference frame, identifies it across decades.
2. **Names persist; measured structure turns over.**
   - Year to year, 95–100% of functions keep their (file, name) (NH's notion of survival).
   - Only **59–72% keep a structural twin**, a function measured almost identically.
   - So about a third of the functions that keep their names change their measurements enough in a year to stop being
     twins.
   - The two series correlate only moderately (ρ 0.49). This refines NH: **identity is stable, the body is not.**
     NH's infant-mortality result is about names. A name-free lifecycle would show much faster turnover.
   - The lowest-retention years are founding or rewrite years: curl 2000, openssl 1999, harfbuzz 2011 and 2018,
     libarchive 2009, nDPI 2017.
3. **Yearly turnover does not track the regression share of fixes.** "Change brings regressions" is not visible at
   yearly grain as a *share* of fixes. That fits XC and REG: regressions scale with activity overall (commit size),
   not with how much the design moved.
