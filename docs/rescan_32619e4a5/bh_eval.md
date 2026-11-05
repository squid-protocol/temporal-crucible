# B-H1..B-H3 — bug-label expansion (power for the small-file bands)

Generated 2026-11-05 00:52 · repo `curl` · pool HEAD `04bfe8fbbf55` · DB `curl_galaxy_master.db` (opened read-only, WAL-aware) · pre-registered gitgalaxy#2982 comment 5651082895; implemented verbatim; verdicts publish either way. **Do not commit** per operator instruction; this doc is a local artifact of an unattended run.

## Leakage-free design

Centrality columns and `total_loc` are read from the existing scan DB at each event's **parent** commit (T0) — no rescan. HCM1_LD_30 is computed fresh from the pool clone via `git log <parent> --since=<parent_date-365d> -n 4000 --no-merges`, ancestors of parent ONLY (`hcm_variants.raw_commit_walk`, called directly, not reimplemented) — no information from the fix commit or anything after it can enter any feature. Walk cache (`/tmp/claude-1000/-home-joe-Projects/7026d7a1-a379-4dda-a4df-b5859b206664/scratchpad/hcmwalk_cache`) is the SAME directory `hcm_variants.py` uses, reused verbatim per the pre-registration.

Coverage: **984** events usable (of **1107** class-matching in the event set); skipped — {'no touched file present in parent snapshot': 123}. Pooled candidate files: **804542**, pooled positives: **1949**. Event-file class counts in `curl_bugs.json`: {'regression': 307, 'bugfix-fixes': 500, 'bugfix-bug': 300}. HCM walk wall-time: 125.0s (cached per parent sha, shared with hcm_variants.py's own cache).

Band sizes (absolute NLOC scheme): `<=22` n=25400 n_pos=16 (UNDERPOWERED), `23-48` n=117896 n_pos=43 (powered), `49-108` n=238608 n_pos=118 (powered), `>108` n=422638 n_pos=1772 (powered). Powered small bands: 1/2 -> B-H1 Bonferroni alpha = 0.01/(5 x 1) = 0.002000.

**Parallel execution**: fork pool, 10 workers. B-H1's 20 (measure,band) cells each ran their own full serial bootstrap in one worker, seeded `base_seed + feat_idx*4 + band` (distinct per cell). B-H2/B-H3 each split `--iters` into 10 chunks (sizes [500, 500, 500, 500, 500, 500, 500, 500, 500, 500]), seeded `base_seed + 1000*chunk_id`, concatenated in the parent before computing percentiles/the monotonicity fraction.

## B-H1 — powered small-file centrality test

Per measure x band: AUC(measure), AUC(total_loc), lift, one-sided event-bootstrap (5000 iters) lower bound on the lift. Bonferroni family = 5 measures x powered SMALL bands only (<=22, 23-48) — large bands shown for context, not part of the family or the verdict.

### `pagerank_score` vs `total_loc`

| band | n | n pos | AUC(measure) | AUC(total_loc) | lift | boot lower bound | 95% CI (lift) | powered | verdict |
|---|---|---|---|---|---|---|---|---|---|
| <=22 | 25400 | 16 | 0.3647 | 0.2567 | 0.1080 | -0.7142 | [-0.6981, 0.1796] | no | UNDERPOWERED |
| 23-48 | 117896 | 43 | 0.5833 | 0.5778 | 0.0055 | -0.1461 | [-0.0978, 0.1138] | yes | not supported |
| 49-108 (context) | 238608 | 118 | 0.6493 | 0.4983 | 0.1510 | 0.0422 | [0.0727, 0.2251] | yes | **SUPPORTED** |
| >108 (context) | 422638 | 1772 | 0.6024 | 0.7975 | -0.1951 | -0.2252 | [-0.2139, -0.1758] | yes | not supported |

### `betweenness_score` vs `total_loc`

| band | n | n pos | AUC(measure) | AUC(total_loc) | lift | boot lower bound | 95% CI (lift) | powered | verdict |
|---|---|---|---|---|---|---|---|---|---|
| <=22 | 25400 | 16 | 0.4998 | 0.2567 | 0.2431 | -0.3550 | [-0.3527, 0.3134] | no | UNDERPOWERED |
| 23-48 | 117896 | 43 | 0.4809 | 0.5778 | -0.0969 | -0.2214 | [-0.1811, -0.0137] | yes | not supported |
| 49-108 (context) | 238608 | 118 | 0.5874 | 0.4983 | 0.0891 | -0.0111 | [0.0244, 0.1526] | yes | not supported |
| >108 (context) | 422638 | 1772 | 0.6806 | 0.7975 | -0.1169 | -0.1431 | [-0.1343, -0.1003] | yes | not supported |

### `popularity` vs `total_loc`

| band | n | n pos | AUC(measure) | AUC(total_loc) | lift | boot lower bound | 95% CI (lift) | powered | verdict |
|---|---|---|---|---|---|---|---|---|---|
| <=22 | 25400 | 16 | 0.4986 | 0.2567 | 0.2419 | -0.3561 | [-0.3539, 0.3123] | no | UNDERPOWERED |
| 23-48 | 117896 | 43 | 0.3975 | 0.5778 | -0.1803 | -0.3817 | [-0.3108, -0.0427] | yes | not supported |
| 49-108 (context) | 238608 | 118 | 0.6394 | 0.4983 | 0.1411 | 0.0440 | [0.0748, 0.2042] | yes | **SUPPORTED** |
| >108 (context) | 422638 | 1772 | 0.6358 | 0.7975 | -0.1617 | -0.1879 | [-0.1789, -0.1452] | yes | not supported |

### `import_count` vs `total_loc`

| band | n | n pos | AUC(measure) | AUC(total_loc) | lift | boot lower bound | 95% CI (lift) | powered | verdict |
|---|---|---|---|---|---|---|---|---|---|
| <=22 | 25400 | 16 | 0.4796 | 0.2567 | 0.2229 | -0.3751 | [-0.3731, 0.2936] | no | UNDERPOWERED |
| 23-48 | 117896 | 43 | 0.4112 | 0.5778 | -0.1665 | -0.3569 | [-0.2953, -0.0423] | yes | not supported |
| 49-108 (context) | 238608 | 118 | 0.4170 | 0.4983 | -0.0813 | -0.1866 | [-0.1558, -0.0066] | yes | not supported |
| >108 (context) | 422638 | 1772 | 0.7199 | 0.7975 | -0.0776 | -0.1050 | [-0.0962, -0.0589] | yes | not supported |

### `internal_dependency_links` vs `total_loc`

| band | n | n pos | AUC(measure) | AUC(total_loc) | lift | boot lower bound | 95% CI (lift) | powered | verdict |
|---|---|---|---|---|---|---|---|---|---|
| <=22 | 25400 | 16 | 0.4998 | 0.2567 | 0.2431 | -0.3550 | [-0.3526, 0.3135] | no | UNDERPOWERED |
| 23-48 | 117896 | 43 | 0.4414 | 0.5778 | -0.1363 | -0.3256 | [-0.2641, -0.0197] | yes | not supported |
| 49-108 (context) | 238608 | 118 | 0.3518 | 0.4983 | -0.1464 | -0.2484 | [-0.2157, -0.0754] | yes | not supported |
| >108 (context) | 422638 | 1772 | 0.7066 | 0.7975 | -0.0909 | -0.1218 | [-0.1114, -0.0716] | yes | not supported |

**B-H1 per-small-band status:** `<=22`=UNDERPOWERED, `23-48`=not supported

**B-H1: not supported.** SUPPORTED iff >=1 measure clears AUC>0.5 and lift lower bound>0 in EACH powered small band.

## B-H2 — the monotone shape (confirmatory)

PageRank only, all 4 absolute bands, ONE joint bootstrap (5000 iters) — each resample draws one shared set of resampled events and computes all 4 bands' lifts from it, so the ordering claim is evaluated on correlated draws, not 4 independent per-band bounds. SUPPORTED iff lift band0>band1>band2>band3 holds in >=99% of resamples.

| band | observed lift (PageRank − total_loc) |
|---|---|
| `<=22` | 0.1080 |
| `23-48` | 0.0055 |
| `49-108` | 0.1510 |
| `>108` | -0.1951 |

**Fraction of 4764/5000 valid resamples with strict monotone decrease: 0.0076** (threshold >=0.99). **B-H2: not supported.**

## B-H3 — HCM1_LD_30 out-of-selection validation

Pooled over all 804542 candidate files across all 984 parent snapshots (n_pos=1949), no banding. One-sided event-bootstrap (5000 iters, alpha=0.01, single comparison, no Bonferroni).

| n | n pos | AUC(HCM1_LD_30) | AUC(total_loc) | lift | boot lower bound (α) | 95% CI | verdict |
|---|---|---|---|---|---|---|---|
| 804542 | 1949 | 0.8696 | 0.8350 | 0.0345 | 0.0207 | [0.0227, 0.0476] | **SUPPORTED** |

**B-H3: **SUPPORTED**.**

## Design notes / ambiguity resolutions

- **B-H1's Bonferroni family is scoped to the 2 small bands only** (5 measures x n_powered_small_bands), per the pre-registration's literal text — unlike `centrality_bands.py`'s C-H1, which scopes its family to all 4 bands as a stated ambiguity resolution; no such ambiguity exists here.
- **The two large bands are reported at the same small-band alpha**, for at-a-glance comparability and because B-H2 reuses their point estimates — they carry no verdict of their own and are excluded from B-H1's SUPPORTED determination.
- **B-H1's SUPPORTED rule reads as AND-across-bands, OR-across-measures**: each powered small band needs its OWN qualifying measure — both powered bands must clear it independently for the overall claim.
- **B-H2 uses ONE shared resampled-event draw per iteration across all 4 bands** — a joint bootstrap, deliberately NOT four independent per-band streams (B-H1's design): the claim is about simultaneous ordering within one resample.
- **Multiprocessing seeding is fixed but NOT a serial-stream-equivalence claim.** B-H1 cells use `base_seed + feat_idx*4 + band`; B-H2/B-H3 chunk seeds use `base_seed + 1000*chunk_id`. Both are deterministic and rerunnable, but a serial single-process run at the same `--seed` will NOT reproduce bit-identical draws — what the pre-registration's seed=2982 buys here is reproducibility of THIS (parallel) procedure, not cross-procedure identity.
- **The numpy AUC engine (`auc_numpy`) replaces `rw_analyses.pooled_auc`** (pure-Python, does not finish at ~2.5M pooled rows) with an identical-formula, vectorized reimplementation — verified against the original on 20 randomized tie-heavy trials (exact match) before this file was written.
- **HCM1_LD_30 is never reimplemented** — `hcm_variants.raw_commit_walk` and `compute_all_variants` are called directly and the `HCM1_LD_30` key is read out, so this test is byte-for-byte frozen to its CVE-label definition by construction.

---
*Regenerate: `python tools/bh_eval.py --events events/curl_bugs.json` — stdlib+numpy only; HCM walks cached under `/tmp/claude-1000/-home-joe-Projects/7026d7a1-a379-4dda-a4df-b5859b206664/scratchpad/hcmwalk_cache` (shared with hcm_variants.py) keyed by parent sha; bootstrap cells checkpointed to `/tmp/claude-1000/-home-joe-Projects/7026d7a1-a379-4dda-a4df-b5859b206664/scratchpad/bh_eval_cache_curl_bugs_i5000_s2982.json`. Bootstrap compute time this run: 3698.5s wall-clock summed across workers (cells loaded from cache report 0s).*
