---
date: 2026-11-11
title: How good could error prediction get, and does M1 survive its missing controls? (CEIL)
type: exploratory
status: scored
verdict: n/a
theme: defect-prediction
ids:
docs: docs/ceil.md
links: temporal-crucible#92; temporal-crucible#96
takehome: With a measured ceiling, a file-year fix model reaches recall@20%-of-lines 0.37 in sample and 0.27 out of repo against an attainable 0.45 and a perfect-rate ceiling of 0.66; CGR-M1's three network terms all survive author and change-coupling controls and file-clustered SEs (1.29/1.49/1.31), author count is the strongest term in the model at 2.06, and label quality does not look like the binding constraint.
---

# How good could error prediction get, and does M1 survive its missing controls? (CEIL)

## Question

Two questions the owner asked after CGR: what is the ceiling on file-year error prediction, and does
CGR-M1's network result survive the controls its own write-up flagged as missing?

## Why we asked

The programme keeps reporting that structure adds nothing beyond size and churn, and M1 was the one
joint model where network terms beat churn. M1 lacked author-count and change-coupling controls and did
not cluster by file, so its p < 1e-37 was not credible. Separately, nobody had put a number on how much
of the outcome is predictable at all.

## What we did

Rebuilt M1's exact file-year frame from the cached CGR build with no rescan (8 repos, 5 languages,
57,057 file-years, 7,188 files) and verified it reproduces the published ORs to three decimals. Then:

1. A negative-binomial rate model with `log(function loc)` as an **exposure offset**, so the outcome is
   a rate per line and the model carries no size covariate at all. Its dispersion drives an oracle
   ladder: rank by the fitted rate and score against `y ~ Poisson(mu)` for the ceiling given the
   covariates we have, then draw the NB latent rate `lam = mu · Gamma(1/alpha, alpha)` and score against
   `y ~ Poisson(lam)` for the ceiling if all rate heterogeneity were recovered. Scored pooled, within
   exposure quartiles, and at a 20%-of-lines review budget, with leave-one-repo-out.
2. M1 re-fit with author count and co-change partners added (both from ancestors-only `git log` walks)
   and SEs clustered on file, plus a C-only / non-C split.

Also ran the ladder on label arms — `regression` (audited, precision 0.73–0.87) against `other-fix`
(never audited) — comparing the *realized share of attainable signal*, since arms differ in event rate
and raw ceilings are not comparable.

## What we found

- **Ceiling (all repos, all classes):** recall@20%-of-lines observed **0.366** in sample, **0.273**
  leave-one-repo-out, attainable with these covariates **0.451**, perfect-rate ceiling **0.661**. Pooled
  AUC 0.805 / 0.890 / 0.918. Overdispersion `alpha` **1.18–1.59** in all six configurations.
- **The headroom is in unmeasured rate variation, not labels:** +0.19 to +0.28 recall@20% from
  `oracle-mu` to `oracle-lam` in every configuration.
- **Label arms came back inconsistent in sign.** Audited `regression` realized more of the attainable
  AUC than unaudited `other-fix` (0.846 vs 0.793) but *less* of the attainable recall (0.730 vs 0.748);
  C-only vs non-C likewise (0.797 vs 0.736 on AUC, 0.548 vs 0.837 on recall). No clear evidence that
  label quality is the binding constraint.
- **But the dominant label class is unaudited:** `other-fix` is 85–97% of the outcome mass in every repo
  (46,570 of 56,766 events) and is absent from `xc_label_audit.md` entirely.
- **M1 survives.** Rewired 1.42→**1.29**, coupled 1.60→**1.49**, cycle 1.38→**1.31**, all CIs clear of 1
  at z 8.8–10.9 on 7,188 file clusters. The fear that call-graph coupling just proxied change coupling is
  not supported: co-change is the weakest term (1.055) and inverts on non-C (0.930).
- **Author count is the strongest term in the model: OR 2.06 [1.92, 2.22]**, ahead of prior fixes. Adding
  it drops prior fix 2.10→1.65 and churn 1.22→1.10.
- Network's contribution is statistically solid but practically small: chi2 575 on 3 df, +0.008
  pseudo-R².

## Take-home

A file-year fix model reaches recall@20%-of-lines 0.37 in sample and 0.27 out of repo against an
attainable 0.45 and a perfect-rate ceiling of 0.66; M1's three network terms all survive author and
change-coupling controls with file-clustered SEs, author count is the strongest predictor in the model,
and the ceiling is set by rate variation no covariate sees rather than by label quality.

## What it changed

- M1's effect sizes stand; its significance does not — quote the file-clustered z values (8.8–10.9), not
  p < 1e-37.
- Author count joins the baseline any future defect model has to beat. Part of what recidivism and churn
  were credited with is how many different people touched the file.
- Change coupling is demoted as a confound for network coupling on this outcome.
- The unaudited `other-fix` class should be added to the label audit; it is the de facto outcome of every
  file-year model in this programme.
- The oracle ladder is reusable: it gives any future study a measured ceiling instead of an argument.
