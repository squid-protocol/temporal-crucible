# CEIL — how good could a file-year error-prediction model get?

**Exploratory, 2026-11-11.** Not registered. Run on the CGR replication data, deliberately **not** on the
LAWS confirmatory frame or its draw — item 2 below previews LAWS's defect arm, and running it on the
registered frame would burn it.

Two questions the owner asked after the CGR/M1 result:

1. **THETA** — what is the ceiling? A negative-binomial rate model with `log(code size)` as an
   **exposure offset** (so the outcome is a rate per line and the size wall is handled by design rather
   than by a covariate), then an oracle ladder that turns its own dispersion into a *measured* ceiling.
2. **M1REFIT** — does CGR-M1 survive the two controls its own write-up flags as missing (author count,
   change coupling) and cluster-robust SEs by file, which M1 lacked.

Regenerate: `SFS_SRC=... OMP_NUM_THREADS=1 <laws-venv>/bin/python tools/ceil_eval.py --data
/srv/storage_16tb/projects/gitgalaxy/cgr-study --out docs/ceil.json --draws 200` · results `docs/ceil.json`
· seed 2982.

## Frame

M1's frame, rebuilt from the cached CGR build output (`dbs/` + `scratch/`) with no rescan: 8 repos
(libgit2, postgres, libxml2, redis — C; prometheus Go, commons-lang Java, sphinx Python, ripgrep Rust),
every 4th quarterly snapshot, covariates from `(t−1y, t]`, outcome in `(t, t+1y]`,
**57,057 file-years over 7,188 files**.

Author count and co-change partners come fresh from one `git log <sha> --since --until --no-merges
--name-only` walk per sampled snapshot, **walking ancestors of that snapshot only**, so nothing at or
after the outcome window can enter a covariate — the leakage discipline `tools/incremental_value.py`
used. Co-change ignores commits touching more than 50 files (the chronometer prototype's gate).
Exposure is `sum(function loc)` at the snapshot, from the scan DB, using the same `named, loc>=3`
filter `snapshot_networks` applies — so it counts exactly the code mass whose call network M1 measured.

**Frame check — M1 reproduces exactly** (same hand-rolled IRLS, naive SEs, before anything is added):

| term | published CGR-M1 | this rebuild |
|---|---|---|
| prior fix | 2.10 | **2.100** |
| coupled | 1.60 | **1.604** |
| size (log functions) | 1.53 | **1.532** |
| rewired | 1.42 | **1.415** |
| in a cycle | 1.38 | **1.382** |
| churn | 1.22 | **1.220** |
| file-years | 57,057 | **57,057** |

Anything that moves below is the controls and the clustering, not a different dataset.

## 1 · THETA — the measured ceiling

The ladder, per configuration. `obs` = fitted model against the real labels. `oracle-mu` = rank by the
fitted rate, score against `y ~ Poisson(mu)` — **the ceiling given the rate variation these covariates
do see**. `oracle-lam` = draw the NB latent rate `lam = mu · Gamma(1/alpha, alpha)`, rank by `lam`,
score against `y ~ Poisson(lam)` — **the ceiling if a model recovered all rate heterogeneity**.
`oracle-lam < 1.0` is irreducible discovery noise.

For a binary "did this file-year get a fix", the Bayes-optimal ranker is the expected count (`P(y>0) =
1 − exp(−lam)` is monotone in `lam`), so ranking by `lam` is optimal for AUC; under a line budget the
fractional-knapsack optimum is `lam / lines`, so that is optimal for recall@budget. Both oracles are
therefore genuine bounds. `auc_density` (AUC of the rate per line) is **not** bounded by the oracle —
the oracle is not optimal for it — so it is reported descriptively and never as a share.

### AUC (which file-year gets a fix)

| config | events | alpha | obs | oracle-mu | oracle-lam |
|---|---|---|---|---|---|
| all repos · all classes | 56,766 | 1.281 | 0.8046 | 0.8904 | **0.9181** |
| all repos · regression | 8,332 | 1.589 | 0.8413 | 0.9034 | **0.9332** |
| all repos · other-fix | 46,570 | 1.217 | 0.8074 | 0.8875 | **0.9151** |
| C only · all classes | 45,070 | 1.182 | 0.8100 | 0.8892 | **0.9152** |
| non-C · all classes | 11,696 | 1.556 | 0.7891 | 0.8930 | **0.9243** |
| C only · regression | 7,966 | 1.572 | 0.8254 | 0.8930 | **0.9265** |

### Recall at a 20%-of-lines review budget (the effort-aware metric; chance = 0.20)

| config | obs | oracle-mu | oracle-lam |
|---|---|---|---|
| all repos · all classes | 0.3663 | 0.4508 | **0.6611** |
| all repos · regression | 0.3710 | 0.4341 | **0.7107** |
| all repos · other-fix | 0.4052 | 0.4745 | **0.6645** |
| C only · all classes | 0.3024 | 0.3868 | **0.6221** |
| non-C · all classes | 0.4325 | 0.4776 | **0.7355** |
| C only · regression | 0.3510 | 0.4140 | **0.6954** |

Leave-one-repo-out, primary config: recall@20% **0.2731**, `auc_density` 0.7351 — the honest
out-of-repo number, well below the in-sample 0.3663.

### Where the gap lives

| config | realized share of attainable AUC | realized share of attainable recall@20% | headroom mu→lam (recall@20%) |
|---|---|---|---|
| all repos · all classes | 0.780 | 0.663 | **+0.2103** |
| all repos · regression | 0.846 | 0.730 | **+0.2766** |
| all repos · other-fix | 0.793 | 0.748 | **+0.1901** |
| C only · all classes | 0.797 | 0.548 | **+0.2353** |
| non-C · all classes | 0.736 | 0.837 | **+0.2580** |
| C only · regression | 0.828 | 0.706 | **+0.2814** |

**Overdispersion is large and consistent: alpha 1.18–1.59** (theta 0.63–0.85) in every configuration.
The headroom from rate heterogeneity the covariates cannot see is **+0.19 to +0.28 recall@20% in all six
configurations** — far larger and far more consistent than any difference between label sets.

### Within-exposure-quartile AUC (Q1 = smallest files)

| config | observed | oracle-mu |
|---|---|---|
| all repos · all classes | 0.654 / 0.708 / 0.709 / 0.773 | 0.775 / 0.741 / 0.732 / 0.849 |
| all repos · regression | 0.759 / 0.759 / 0.726 / 0.779 | 0.790 / 0.751 / 0.735 / 0.821 |
| all repos · other-fix | 0.657 / 0.709 / 0.710 / 0.765 | 0.787 / 0.752 / 0.730 / 0.834 |
| C only · all classes | 0.605 / 0.681 / 0.702 / 0.778 | 0.711 / 0.675 / 0.709 / 0.859 |
| non-C · all classes | 0.687 / 0.686 / 0.730 / 0.753 | 0.779 / 0.757 / 0.801 / 0.877 |

These do **not** collapse the way repowise-bench's bands do (0.525 / 0.572 / 0.593 / 0.718), and that is
**not** a win over the size wall: the outcome here is "any fix", positive in a third of all file-years,
a far commoner and easier event than a CVE or a bug-labelled defect. Read these bands as a property of
this outcome, not as a refutation of the wall.

### Does label quality bind?

The discriminating test the owner asked for. Because arms differ in event rate, raw ceilings are not
comparable — rarer outcomes have lower attainable AUC whatever the label quality — so the comparison is
the **realized share of attainable signal**, whose numerator and denominator face the same event rate.

- `regression` (audited rule, precision **0.73–0.87** in `xc_label_audit.md`) vs `other-fix` (**never
  audited**): realized AUC share **0.846 vs 0.793** (regression better, as a label-noise story predicts),
  but realized recall@20% share **0.730 vs 0.748** (regression *worse*).
- C only (rules developed and audited on C) vs non-C (**unaudited**): realized AUC share **0.797 vs
  0.736** (C better), realized recall@20% share **0.548 vs 0.837** (C much worse).

**Inconsistent in sign across metrics in both comparisons. This test does not show label quality as the
binding constraint.** `alpha` is also *higher* on the cleaner class (1.589 regression vs 1.217
other-fix), the opposite of what pure label noise would do — most likely because `regression` is a
rarer, burstier, postgres-concentrated outcome, which is itself a reminder that alpha confounds event
rate with heterogeneity.

What does bind, consistently, is the headroom above: **the rate variation no covariate in this panel
sees.** That is where the ceiling is set, not in the labels.

**The label finding worth recording anyway.** `other-fix` carries **85–97% of the outcome mass in every
one of the 8 repos** (46,570 of 56,766 events) and is **absent from `xc_label_audit.md` entirely** — the
audit covers latent, regression and extrinsic. So the class that effectively *is* M1's dependent
variable has never had its precision measured, on any repo. `latent` is nearly absent from this panel
(41 events, libxml2 only), which is why the clean-label arm had to use `regression` rather than curl's
30/30 `latent`.

## 2 · M1REFIT — does M1 survive its missing controls?

Outcome, frame and terms exactly as published, plus `log_authors` and `log_cochange`, with SEs clustered
on **file** (7,188 clusters; the headline) and on **repo** (8 clusters — too few for reliable
cluster-robust inference, shown only as a conservative bound).

### All 8 repos — 57,057 file-years, 19,092 positives

| term | M1 OR | M1 z | re-fit OR | z (file) | 95% CI | z (repo) |
|---|---|---|---|---|---|---|
| rewired | 1.415 | 14.4 | **1.294** | 10.1 | [1.23, 1.36] | 8.6 |
| coupled | 1.604 | 16.1 | **1.493** | 10.9 | [1.39, 1.61] | 8.4 |
| in a cycle | 1.382 | 12.9 | **1.313** | 8.8 | [1.24, 1.39] | 5.1 |
| size (log functions) | 1.532 | 32.3 | 1.517 | 24.5 | [1.47, 1.57] | 13.5 |
| churn | 1.220 | 30.7 | **1.103** | 11.8 | [1.08, 1.12] | 3.5 |
| prior fix | 2.100 | 29.8 | **1.651** | 16.7 | [1.56, 1.75] | 6.0 |
| **authors (new)** | — | — | **2.062** | 19.2 | [1.92, 2.22] | 5.6 |
| **co-change (new)** | — | — | 1.055 | 5.5 | [1.04, 1.08] | 1.9 |

Network terms beyond the baseline: chi2 = 575.3 on 3 df, p = 2.2e-124; pseudo-R² 0.2498 → 0.2577.

### C only — 43,415 file-years, 14,905 positives

| term | M1 OR | re-fit OR | z (file) | 95% CI |
|---|---|---|---|---|
| rewired | 1.393 | 1.264 | 7.8 | [1.19, 1.34] |
| coupled | 1.587 | 1.458 | 8.6 | [1.34, 1.59] |
| in a cycle | 1.408 | 1.314 | 8.0 | [1.23, 1.41] |
| prior fix | 2.231 | 1.674 | 14.6 | [1.56, 1.79] |
| authors | — | 2.037 | 15.8 | [1.87, 2.22] |
| co-change | — | 1.099 | 8.4 | [1.08, 1.12] |

Network beyond baseline: chi2 = 400.1, df 3, p = 2.1e-86; pseudo-R² 0.2619 → 0.2691.

### non-C — 13,642 file-years, 4,187 positives (unaudited labels)

| term | M1 OR | re-fit OR | z (file) | 95% CI |
|---|---|---|---|---|
| rewired | 1.436 | 1.361 | 6.3 | [1.24, 1.50] |
| coupled | 1.706 | 1.633 | 7.8 | [1.44, 1.85] |
| in a cycle | 1.213 | **1.218** | **2.9** | [1.07, 1.39] |
| prior fix | 1.740 | 1.503 | 7.1 | [1.34, 1.68] |
| authors | — | 2.206 | 11.7 | [1.93, 2.52] |
| co-change | — | **0.930** | **−4.0** | [0.90, 0.96] |

Network beyond baseline: chi2 = 161.2, df 3, p = 9.9e-35; pseudo-R² 0.2154 → 0.2250.

### What the re-fit changes

- **All three network terms survive** both controls and file-clustering, shrinking 8–12%: rewired
  1.42→1.29, coupled 1.60→1.49, cycle 1.38→1.31, every CI clear of 1 and every z ≥ 8.8 on 7,188
  clusters. The worry that call-graph coupling was largely a structural proxy for change coupling is
  **not supported** — co-change is the weakest term in the model (1.055) and *inverts* on non-C (0.930).
- **Author count is the big omitted variable: OR 2.06 [1.92, 2.22], now the strongest single term in the
  model**, ahead of prior fixes. Adding it takes prior fix from 2.10 to 1.65 and churn from 1.22 to
  1.10 — so part of what recidivism and churn were credited with is "how many different people touched
  this file last year".
- **M1's significance was badly overstated, as its own caveat said.** Treating 57,057 file-years as
  independent gave p < 1e-37; file-clustered z values are 8.8–10.9, and with 8 repo clusters 5.1–8.6.
  The effects hold; the inflated certainty does not.
- **Statistically solid, practically small.** Network adds chi2 575 on 3 df but only +0.008 pseudo-R².
- `cycle` weakens (z 2.9) and co-change inverts on the non-C half, which carries unaudited labels —
  LAWS Amendment 0's audit is the right fix.

## Caveats

- **Exploratory, no registration, no multiplicity control.** None of this is a confirmatory verdict.
- The outcome is "any harvested fix event", dominated by the **unaudited `other-fix`** class; it is not
  a CVE or a bug-labelled defect. Nothing here transfers to CVE prediction.
- Family 4 (expressed human judgment) is barely represented: the CGR DBs predate comment extraction, so
  the only proxy available was `state_safety_neg` density. Danger comments live in the curl/DCS data,
  not this panel. The ceiling measured here is therefore a ceiling **for this covariate set**, and
  `oracle-lam` is exactly the estimate of what such a missing family could in principle be worth.
- `alpha` absorbs missing covariates, label noise and attention heterogeneity in one number; the ladder
  measures total headroom and cannot attribute it. The label arms above were the attempt to split it and
  came back inconsistent.
- Exposure is function loc, not whole-file LOC (the CGR DBs carry no file LOC), so headers, globals and
  out-of-function comments are outside the offset.
- Repo-clustered SEs rest on 8 clusters and should be read as a direction, not an interval.

---

## 5 · Re-run on v3c labels — does label quality move the ceiling?

**2026-11-11.** The sections above used the v1 keyword gate, whose `other-fix` precision
`docs/otherfix_audit.md` measured at 0.558 pooled (0.383 outside C). This section re-runs the whole
ladder on the **FIXLIKE v3c** event sets (0.761 pooled, 0.773 outside C) and changes nothing else.
Results: `docs/ceil_v3c.json` · regenerate with `--events _xc2`.

The frame is identical — **57,057 file-years in both runs**, because snapshots and files come from the
call networks, not from the labels. Only the outcome counts and the prior-fix counts change, so this
is a clean apples-to-apples comparison.

### The ladder, v1 → v3c

| config | fix events | alpha | obs R20 | oracle-mu R20 | oracle-lam R20 | obs AUC |
|---|---|---|---|---|---|---|
| all repos · all | 56,766 → 32,796 | 1.281 → **1.378** | 0.366 → 0.383 | 0.451 → 0.466 | 0.661 → **0.684** | 0.805 → 0.821 |
| all repos · other-fix | 46,570 → 22,600 | 1.217 → **1.436** | 0.405 → 0.463 | 0.474 → 0.532 | 0.665 → **0.718** | 0.807 → 0.830 |
| C only · all | 45,070 → 26,750 | 1.182 → 1.250 | 0.302 → 0.331 | 0.387 → 0.410 | 0.622 → 0.642 | 0.810 → 0.820 |
| non-C · all | 11,696 → 6,046 | 1.556 → **1.871** | 0.432 → 0.554 | 0.478 → 0.605 | 0.736 → **0.817** | 0.789 → 0.822 |
| all repos · regression | 8,332 → 8,332 | 1.589 → 1.589 | 0.371 → 0.371 | 0.434 → 0.434 | 0.711 → 0.711 | 0.841 → 0.841 |
| C only · regression | 7,966 → 7,966 | 1.572 → 1.572 | 0.351 → 0.351 | 0.414 → 0.414 | 0.695 → 0.695 | 0.825 → 0.825 |

The two `regression` arms are **identical in both runs**, which is the built-in control: amendment 2
is scoped to `other-fix`, so a class the rule does not touch did not move. The pipeline is doing what
it claims.

### Realized share of attainable signal, v1 → v3c

| config | AUC | recall@20% lines |
|---|---|---|
| all repos · all | 0.780 → **0.823** | 0.663 → 0.689 |
| all repos · other-fix | 0.793 → **0.847** | 0.748 → 0.792 |
| C only · all | 0.797 → 0.827 | 0.548 → 0.627 |
| non-C · all | 0.736 → **0.808** | 0.837 → 0.873 |

Leave-one-repo-out, primary config: recall@20% **0.273 → 0.299**.

### What it shows

1. **Cleaner labels help, and the effect is small.** Every arm the rule touched improved, in the
   expected direction: the realized share of attainable AUC rose 0.780 → 0.823 and out-of-repo
   recall@20% rose 0.273 → 0.299. **About three to four points of realized performance** was being
   eaten by label noise.
2. **The wall did not move.** The headroom from rate variation no covariate sees — `oracle-mu` to
   `oracle-lam` on recall@20% — was **+0.210 on v1 labels and +0.218 on v3c**. Essentially unchanged.
   So the earlier conclusion now has numbers behind it rather than an inconsistent-signs argument:
   **labels cost about 3-4 points; the unmeasured-rate wall is worth about 22.** A tax, not the wall.
3. **The language gap closed, as the label audit predicted it would.** Realized AUC was 0.797 (C) vs
   0.736 (non-C) on v1 labels, a gap of 0.061; on v3c it is 0.827 vs 0.808, a gap of 0.019. The label
   fix closed exactly the gap the label *precision* predicted — which is the strongest confirmation in
   this document that the audit was measuring something real.
4. **`alpha` went UP, not down — the prediction registered before the run was wrong.** The
   expectation on record was that cleaning the labels would *lower* dispersion, on the reasoning that
   some of `alpha` was label noise. It rose instead: 1.281 → 1.378 overall, 1.217 → 1.436 on
   `other-fix`, 1.556 → 1.871 outside C.

   The reason is worth keeping. The commits rule C removed — lint sweeps, javadoc passes, formatting,
   dependency bumps — are spread **broadly and evenly** across a codebase, far more evenly than real
   bug fixes, which concentrate. Mixing them into the outcome therefore *diluted* the concentration
   and made file-year risk look more uniform than it is. **Label noise was masking rate heterogeneity,
   not manufacturing it.**

   This cuts against the convenient reading. One might have hoped most of the ceiling gap was
   measurement error that better labels would dissolve; instead, better labels reveal *more* genuine
   rate variation to explain, and raise the perfect-knowledge ceiling with it (recall@20% 0.661 →
   0.684, and 0.736 → 0.817 outside C). The headroom is real signal nobody is capturing, not noise.
5. **Consequence for what comes next.** Since the dispersion is not label noise, the remaining
   headroom is either covariates that exist and are unused, or the discovery/attention process. That
   is now the only live explanation, and it is the one this panel cannot test — it needs a measurement
   of attention, or an intervention that holds attention constant across files.
