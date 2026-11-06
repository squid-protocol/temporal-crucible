# NM — a screen of the engine's untested metrics against future fixes — registered 2026-11-06, before any NM × outcome statistic

**Question.** The 32619e4a5-era engine added metrics this program has never related to an outcome. Do any of them say
something about where fixes land **at equal size**?

**Which metrics count as untested.**
- The 76 columns the rescan added (`docs/rescan_32619e4a5/engine_drift.md`) plus the function-graph columns. Grepping
  `docs/` and `tools/` on `land/stack-51-53`, these appear only in schema lists and `export_dataset.py`.
- **Dropped as rank-equivalent within a snapshot:**
  - `pct_vec_*`: percentiles of the already-tested `risk_*` vectors.
  - `pct_fam_*`: percentiles of `fam_*`.
- **Dropped as never populated on C files in any DB (an engine finding in itself):** `token_mass`,
  `financial_read_cost`, `agentic_isolation_risk`, `requires_hitl`, `appsec_god_mode`, `hallucination_zone`,
  `silent_mutation_risk`, `ai_threat_confidence`, `ai_threat_score`.
- **Dropped as constant:** `arch_sys_config`, `fam_crypto`, `fam_regex`, `fam_serialization`, `fam_ui`.

**Honest exposure note.** `fam_*` are per-file sums of hit columns. Some of those hit columns were examined before: as
fix-commit deltas (signal_anatomy) and as function-grain danger density (D-H1, R2-H1). None was tested as a file-level
forward predictor at equal size. Treat `fam_danger` and `fam_memory` as *previously glimpsed*, not pristine.

## Metrics entering the screen

The rule is fixed now and computed by the tool from values alone, never from outcomes. A metric enters iff it is
non-zero on ≥ 5% of C-file rows **and** has ≥ 3 distinct values in **each** of the three repos' DBs below.

| family | candidates |
|---|---|
| file (NM-F) | `fam_*` (memory, cleanup, guards, danger, concurrency, connectivity, io, ipc, time, events, tests, docs, debt, mutation, dead_code, credential, threat, ml_ai); `rel_guard_balance`; `rel_alloc_cleanup`; `doc_umbrella`; `wrapped_debug_prints`, `wrapped_memory_alloc`, `wrapped_panics_and_aborts`; `threat_db_sinks`, `threat_api_near_db_sink`; the five `mitigation_telemetry` keys (`amplified_cascading_flux`, `amplified_exfiltration`, `amplified_race_conditions`, `mitigated_danger`, `mitigated_memory_allocs`) |
| function (NM-G) | `func_fan_in`, `func_fan_out`, `func_pagerank`, `is_public`, `is_documented` (entry rule applied to curl and nDPI only) |

## File screen (NM-F)

- **Data.** The ARCH-U quarterly snapshots and DBs: curl 105, nDPI 43, openssl 110. Outcome: on-master `security-fix`
  touches in (t, t + 180 d].
- **Statistic.** Per snapshot:
  - split the C files into 10 equal-count `total_loc` strata (rank-based);
  - compute the AUC of the raw metric using only pairs inside the same stratum, pooled by pair count (ties ½);
  - lift = AUC − 0.5.
  - Snapshots with ≥ 1 positive count.
- **Test.** 5,000 snapshot-bootstrap rounds, seed 2982. Two-sided percentile CI at level 1 − α, α = 0.01 / M_F, where
  M_F = the number of entering file metrics.
- **A metric is a SIGNAL iff its CI excludes 0 with the same sign on all three repos.** A sign-consistent exclusion on
  two of three repos is a LEAD. Anything else is NO SIGNAL.
- **Secondary, only for SIGNALs.** Effort-aware recall@20, ranking by the metric in its signal direction, against
  LOC-desc and LOC-asc (EA's rule). Descriptive.

## Function screen (NM-G)

- **Data.** FREC's event set and candidates (`tools/frec_eval.py`): curl `security-fix` + bug classes, nDPI
  `security-fix`; scored = events after the median date.
- **Statistic.** Per event:
  - split candidates into `loc` tertiles within the event;
  - compute the AUC of the metric on within-tertile pairs only, pooled by pair count;
  - lift = AUC − 0.5.
  - Events with ≥ 1 within-stratum positive–negative pair count.
- **Test.** 5,000 event-bootstrap rounds, seed 2982, two-sided at α = 0.01 / M_G.
- **SIGNAL iff** the CI excludes 0 with the same sign on curl and nDPI.

## Decision and priors

**Decision rule.** Any SIGNAL is a *lead*, not a result: the screen chose it. It gets its own registration on an
unseen repo (repo #4) before anyone calls it predictive. If there are no SIGNALs, the new metrics join "structure
describes, history predicts" in `EXPERIMENTS.md`.

**Priors.**
- Most `fam_*` metrics: **no signal at equal size**, the program's standing finding.
- `rel_guard_balance`: **uncertain**, perhaps negative: more guards per danger site may mean safer.
- `func_fan_in`: **leaning signal**. Widely-called functions get exercised, fuzzed and reported more.

---

## Results — 2026-11-06 (after registration commit `aa5973c`)

**One sentence.** As registered, the screen finds three file LEADs and one function SIGNAL. The labelled exploratory
size checks show all of them except one are size the strata failed to remove. The exception is
`amplified_cascading_flux`, state mutations inside branches, which carries information beyond size on nDPI and openssl
but not on curl.

### Registered verdicts

**File screen (NM-F, `nm_file_screen.md`).**
- Entry: 9 metrics entered; 22 failed the entry rule. Most families are near-empty in C:
  - io, ipc, time, events, tests, credential, threat, ml_ai;
  - the wrapper counts;
  - the DB-sink threats;
  - four of the five mitigation keys.
- **0 SIGNALs.**
- **LEADs** (CI excludes 0 on nDPI and openssl; positive but not significant on curl): `amplified_cascading_flux`
  (+0.045 / +0.204 / +0.144), `fam_mutation` (+0.055 / +0.186 / +0.112), `fam_dead_code` (+0.044 / +0.122 / +0.077).
- The other six: no signal.

**Function screen (NM-G, `nm_function_screen.md`).**
- `func_fan_out` is a **SIGNAL**: +0.132 on curl (408 events), +0.143 on nDPI (47).
- `func_fan_in` and `func_pagerank`: no signal (≈ 0).
- `is_public` and `is_documented` failed the entry rule only because they are binary (2 distinct values). That is a
  defect in the rule: they were not tested.

### Why the screen under-controlled size (exploratory, `nm_exploratory_size_checks.md`)

The size strata were too coarse. Run through the same screen, size "predicts" within its own strata:

| | curl | nDPI | openssl |
|---|---:|---:|---:|
| `total_loc` within 10 `total_loc` bins (files) | +0.114 | +0.197 | +0.125 |
| function `loc` within `loc` tertiles | +0.178 | +0.147 | — |

Any metric correlated with size inherits that. Compared head-to-head inside the same strata:

- **`fam_*` leads: residual size.** Every `fam_*` metric loses to `total_loc` (−0.01 to −0.16).
- **`func_fan_out`: residual size.** It loses to `loc` (−0.046 curl, −0.004 nDPI). Fan-out per line is ≈ 0.
  Exact-equal-length pairs: +0.06 on curl (139 events), −0.07 on nDPI (12 events). No usable signal.
- **`amplified_cascading_flux`: the one survivor, on two repos.**

  | | nDPI | openssl | curl |
  |---|---:|---:|---:|
  | vs `total_loc`, same 10 bins | +0.007 | +0.020 | −0.068 |
  | 50 finer bins, metric vs leftover size | +0.105 vs +0.089 | +0.113 vs +0.032 | −0.008 vs +0.061 |
  | per line, 10 bins | +0.102 | +0.109 | −0.029 |

  The engine counts a state mutation within 150 characters of a branch (`spatial_correlation.py`, #2546): writes inside
  conditional logic. That is the shape of parsers and protocol state machines, where fuzzer-found bugs cluster (nDPI
  fixes are OSS-Fuzz-bisected; openssl's include many parser CVEs). curl's human-reported CVEs do not follow it. This
  is the same repo split the fix-grammar finding showed in reverse.

### Engine findings (worth gitgalaxy issues)

- **Nine `file_data` columns are never populated on C files**, in any of the four engine builds' DBs:
  - `token_mass`, `financial_read_cost`;
  - `agentic_isolation_risk`, `requires_hitl`, `appsec_god_mode`;
  - `hallucination_zone`, `silent_mutation_risk`;
  - `ai_threat_confidence`, `ai_threat_score`.
- **Five more are constant on C files:** `arch_sys_config`, `fam_crypto`, `fam_regex`, `fam_serialization`, `fam_ui`.

### Next (registered before use)

- **AMP-H1.** Per-line `amplified_cascading_flux` beats `total_loc` in 50-bin size strata on an unseen fuzzer-era C repo
  (harfbuzz, the repo-#2 reserve). Size control: exact or 50-bin strata plus a head-to-head against `total_loc`.
- **Untested binaries.** Re-screen `is_public` and `is_documented` with a binary-aware entry rule.
