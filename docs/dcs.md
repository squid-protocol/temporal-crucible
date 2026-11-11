# DCS — danger comments that stayed safe vs ones that got CVEs: a code signature at birth? (SCORED)

Registration `docs/dcs_hypotheses.md`. Frozen models `docs/dcs_models.json` (sha256 `f4b2642d0c37`, committed d4a65d6 2026-11-11); discovery report `docs/dcs_discovery.md` (exploratory). Aggregates only.

## Confirmation set

- **502** danger-commented functions born on or after each repo's split date (curl 2013-06-30, openssl 2017-06-30, ndpi 2019-11-09, harfbuzz 2017-03-27), **30** cases (6.0%); early deaths excluded 192; birth rows missing 0
- per repo (cases / functions): curl 13 / 132, openssl 8 / 320, ndpi 2 / 15, harfbuzz 7 / 35
- power rule (≥ 20 cases): **met**
- Stage 1 models reproduce their discovery in-sample AUCs within 0.0e+00.

## Registered claims (lift = AUC(B + family) − AUC(B); file-cluster bootstrap 2000, seed 2982; one-sided α = 0.01/4)

AUC(B) = **0.675**.

| id | model | AUC | lift | one-sided lower bound (α = 0.0025) | two-sided 99% CI | call |
|---|---|---:|---:|---:|---|---|
| **DCS-T** | B + T | 0.686 | **+0.011** | -0.016 | [-0.014, +0.031] | **not supported — inconclusive** |
| **DCS-F** | B + F | 0.642 | **-0.033** | -0.089 | [-0.086, +0.025] | **not supported — inconclusive** |
| **DCS-C** | B + C | 0.641 | **-0.034** | -0.115 | [-0.102, +0.017] | **not supported — inconclusive** |
| **DCS-ALL** | B + ALL | 0.656 | **-0.019** | -0.079 | [-0.070, +0.028] | **not supported — inconclusive** |

Supported iff lift > 0 and the one-sided lower bound > 0. A failed claim is a replicated null iff its 99% CI lies inside ±0.02; otherwise inconclusive.

## Descriptive (no verdicts)

- Shrinkage control: lift of each family model over B refitted at that model's C (same data, same penalty, no family features): T +0.011 (B@T AUC 0.675), F -0.033 (B@F AUC 0.675), C -0.033 (B@C AUC 0.674), ALL -0.015 (B@ALL AUC 0.671)
- Recall of cases at the top 20% of lines reviewed (effort-aware, score ÷ loc as in EA/CHG-2): B 63.3%, T 43.3%, F 23.3%, C 46.7%, ALL 36.7%
- Same frozen models on **plain-commented** confirmation functions (3,702, 101 cases): AUC B 0.697; lifts T -0.030, F -0.010, C +0.010, ALL -0.017
- Sensitivity, early deaths counted as controls (694 functions, 30 cases): AUC B 0.670; lifts T +0.009 (lower -0.016), F -0.027 (lower -0.083), C -0.028 (lower -0.100), ALL -0.014 (lower -0.062)
- Discovery screen's top 15 features in confirmation (MH OR, same exposure thresholds): kept sign 6, flipped 8, not estimable 1
  - kept: `T:state_safety_neg/loc` 3.66→1.04, `T:struct_class_start/loc` 0.06→0.56, `T:state_memory_alloc/loc` 5.01→1.42, `T:state_pointers/loc` 2.20→1.83, `T:struct_linear/loc` 2.02→1.18, `T:struct_args/loc` 0.41→0.24
  - flipped: `F:lat_family=F7` 0.16→1.46, `T:arch_api/loc` 0.30→1.45, `C:is_public` 0.30→1.30, `T:complexity/loc` 0.38→1.62, `T:struct_branch/loc` 0.38→1.62, `T:def_freeze_hits/loc` 0.45→6.92, `T:def_encapsulation/loc` 2.37→0.79, `T:args/loc` 3.46→0.27

Runtime 38s · engine `14e70005484d` · seed 2982.

## Reading (hand-written, not generated)

- **No family beats the baseline.** All four claims are not supported. None is a replicated null, because each 99%
  CI reaches past ±0.02. With 30 confirmation cases, the data cannot rule out a small lift of up to about +0.03 for
  telemetry.
- **Shrinkage is not the explanation.** B + C chose a strong penalty (C = 0.001), which also shrinks B. The frozen
  control, B refitted at the same C, scores the same AUC as B (0.674 vs 0.675), so the negative C lift is not a
  shrinkage artefact.
- **The discovery signature overfit.** B + C had the best discovery CV AUC and the worst confirmation lift. 8 of the
  15 strongest screen features reversed. The confirmation case rate is also about twice discovery's (6.0% vs 2.8%),
  in a younger era.
- **Prior work** (checked 2026-11-11 against the published records):
  - Shin et al., TSE 37(6):772–787, 2011, doi 10.1109/TSE.2010.81. 24 of 28 complexity, churn and developer metrics
    were discriminative in Firefox and the RHEL kernel. Combined models flagged > 80% of vulnerable files with
    < 25% false positives. The registration's "complexity alone was weak" is not checked here; read the paper's
    per-category tables before citing it that way.
  - Zimmermann, Nagappan and Williams, ICST 2010, doi 10.1109/ICST.2010.32. Classical metrics gave high precision
    and low recall; dependency metrics gave lower precision and higher recall. Confirmed.
  - Neuhaus, Zimmermann, Holler and Zeller, CCS 2007. Vulture predicted vulnerable Mozilla components mainly from
    their imports (about two thirds of vulnerable components found). The registration's "imports and function
    calls" is broader than the headline result.
  - Here, at function grain, inside the danger-comment cohort and against a size + repo + prior-CVE baseline, the
    call-graph family did not extend the dependency results.
