# SC — does structure predict specific fix classes? A two-stage screen — protocol registered 2026-11-06, before the discovery run

**Why.** XC split fixes into latent, extrinsic, regression and other-fix. Nearly every GitGalaxy metric was only ever
tested against security fixes or pooled fixes, where it reduced to size. One measure, platform-conditional density,
turned out to be class-specific (ENV). This screen asks the same question of every metric: does it help find **one
class** at equal size?

**Design: discover on seen repos, confirm on unseen ones.**

## Stage 1 — discovery (exploratory by construction; this protocol fixes its selection rule)

- **Repos and DBs.** The XC/EA quarterly as-of DBs:
  - curl, 105 snapshots (`e246915aa`);
  - nDPI, 43 (`e246915aa`);
  - openssl, 110 (`da852aa54`).
- **Labels.** `events/*_xc.json` (rules v2). Outcome: touched by a class-K commit in (t, t + 180 d].
- **Candidates.** Every numeric `file_data` column on C files, in two forms: **raw** and **per line** (÷ `total_loc`).
  - Excluded: identifiers, `total_loc` itself, and columns failing the entry rule (≥ 5% non-zero and ≥ 3 distinct values
    in every repo).
  - Added: P per line (ENV) and `amplified_cascading_flux` (from the `mitigation_telemetry` JSON).
- **References, not candidates** (they show the screen recovers known results): prior same-class history; P per line
  for extrinsic.
- **Statistics, per (candidate, class, repo), averaged over scored snapshots:**
  - **D (size-matched).** Split C files into 50 equal-count `total_loc` bins. Compute the stratified AUC of the
    candidate on within-bin pairs only, minus the stratified AUC of `total_loc` in the same bins. D > 0 means the
    candidate beats leftover size.
  - **R (effort-aware).** recall@20 lift over the stronger of LOC-desc / LOC-asc (EA's rule), ranking by the candidate
    in the direction given by the sign of its pooled D.
- **Selection rule (binding).** Per class:
  1. Keep candidates whose D and R are both > 0, in the same direction, on all three repos.
  2. Rank by the minimum R across repos.
  3. Walk down the ranking and drop any candidate whose pooled Spearman |ρ| with an already-kept one exceeds 0.8.
  4. Keep the **top 5** per class, with their direction and form (raw / per line) **frozen**.
- **Instrument check.** The screen must recover P per line for extrinsic (it passed ENV on these repos). If it does
  not, the screen is broken and stage 2 is not registered.

## Stage 2 — confirmation (registered separately, before any holdout join)

- **Holdout.** harfbuzz and libarchive, never scanned by GitGalaxy before this study. Engine `da852aa54`,
  `--spec-alignment`, as-of history. The scans were started before this protocol and join no outcome.
- **Labels.** Their XC labels: extrinsic both repos, regression harfbuzz only (libarchive's were withheld at 0.43),
  other-fix both. A latent class needs a CVE harvest, whose rules would be registered with stage 2.
- **Claims.** Each frozen candidate × its class × each holdout repo: R > 0 with a one-sided snapshot-bootstrap lower
  bound > 0 at α = 0.01 / (number of frozen candidate–class pairs). 5,000 rounds, seed 2982.
- **A candidate is CONFIRMED iff SUPPORTED on every evaluable holdout repo.**

**Caveat, stated now.** Regressions are not a property of files (XC-H5). A file-level screen is expected to find little
for them. The commit-level study is the right instrument there, and this screen does not replace it.

## Run log

- **Run 1 (tool `0a62405`): invalid.** 0 candidates passed for any class, and the **instrument check FAILED**: P per
  line was not recovered for extrinsic. Diagnosis: in `strat_auc_all` the positives series had a fresh 0…n index while
  the size bins carried each snapshot's row index, so `groupby(bins)` misaligned the per-bin counts for every snapshot
  after the first. Fixed and verified to match `nm_screen.strat_auc` exactly on 200 random frames. The instrument check
  did its job. No stage-2 decision was taken on run 1.
