# Rescan on engine 32619e4a5 (2026-11-04/05): robustness rerun

**What this is.** The exact commit set of the study-of-record DB (3,547 distinct curl
commits: CVE fix/introduced/control events, wave-1 reverts and follow-ups, the bug-label
set, and the 219-release walk) was rescanned on gitgalaxy `32619e4a5e83` (origin/main,
2026-11-04). The registered analyses were then rerun unchanged on the new DB.

**What this is not.** These are reruns on data that was already used, so they are
**engine-robustness checks, not new confirmatory results** (the HYPOTHESES.md rule).
The docs of record in `docs/` are unchanged; the regenerated reports are here.

## How it was run

- Scan: `tools/rescan_study_set.py --from-db <old master> --jobs 5 --workers-per-scan 2`,
  `SCAN_ENV` (`GITGALAXY_DISABLE_GIT_HISTORY=1`), and **`--spec-alignment`**:
  `spec_match` has been opt-in since gitgalaxy#3111 (PR #3145). Without the flag it is a
  constant 0, which silently redefines the 13-slot risk vector the tests were registered on.
  With the flag, `risk_spec_match` matches the old values on 99.6% of files.
  3,547/3,547 scanned, 0 failures, 3 h 50 min wall (3.89 s/commit). Metadata: `rescan_meta.json`.
- New DB: about 17 GB, kept out of git under `dbs/curl_out/` in the rescan worktree. An index on
  `file_data(commit_hash, file_path)` and `(file_path)` was added after the scan (speed only).
- Old DB: `/srv/storage_16tb/projects/temporal-crucible/dbs/curl_out/curl_galaxy_master.db`,
  2026-09-13, opened read-only throughout.

## Verdicts: old vs new engine

| test | 2026-09-13 | engine 32619e4a5 | verdict changed? |
|---|---|---|---|
| H1 fixes < controls (per-event) | p=0.773, not supported | p=0.332, not supported | no |
| H2 introduced > controls | p=0.023, not supported | p=0.042, not supported | no |
| H1 per-file pooled (secondary) | p=0.247 | p=0.090 | — |
| W1-H1 reverts shrink code | SUPPORTED (sign p=5.4e-5) | SUPPORTED (sign p=1.6e-4) | no |
| W1-H2 needs-follow-up < stuck | not supported (p=0.77) | not supported (p=0.80) | no |
| W1-H3 follow-ups near fixes | not supported (p=0.99) | not supported (p=0.98) | no |
| B-H1 small-band centrality | not supported | not supported (`<=22` band now UNDERPOWERED: 16 positives, was 28) | no |
| B-H2 monotone shape | not supported (0.0000) | not supported (0.0076) | no |
| B-H3 | SUPPORTED | SUPPORTED (lift 0.0345, lo 0.0207) | no |
| Walk panels (exploratory) | total_loc AUC 0.913 | 0.907; trajectory features still ~0.5 | n/a |

**No pre-registered verdict changed.** Event counts grew slightly (fix 182→185, introduced
118→132, control 168→172) because the new engine scores more files. The worst
untouched-file spillover dropped from 29.8 to 5.0: the engine removed the tail artifact
that issue #5's forensic audit chased.

## Instrument drift (`engine_drift.md`)

- Coverage: +88,694 file rows only in the new scan (yaml 41k, C 32k, perl 7.7k, markdown 5k);
  −33,443 only in the old scan (plaintext 26k, m4 3.6k, python 2.9k).
- Risk vector, share of matched files whose value moved: safety_score 63% (mean 51.9→40.6),
  cognitive_load 38%, tech_debt 26%, dead_code 20% (2.95→0.63), verification 13%. Temporal
  columns are unchanged, as they should be under ablation.
- Retired by the engine: `repo_z_score` (0 everywhere, #3089), `arch_feature_flags` (#4114).
  76 file columns were added (`fam_*`, `pct_vec_*`, threat sinks, composition archetypes).

## Caveats

- The reports' chart links (`charts/...`) are relative to `docs/` and do not resolve from
  this folder. The charts were not regenerated.
- `bh_eval.md` keeps its generated "do not commit" header line from the original
  unattended-run template; it is committed here only as the rerun record.
