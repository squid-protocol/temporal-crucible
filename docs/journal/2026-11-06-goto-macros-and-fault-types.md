---
date: 2026-11-06
title: goto, macros and specific fault types (KF, KF-R, KF-L)
type: confirmatory
status: scored
verdict: mixed
theme: defect-prediction
ids: KF-H1..H4; KF-R / KF-L
docs: docs/kf_hypotheses.md; docs/kf.md; docs/kf_construct_validation.md; docs/kfr_hypotheses.md; docs/kfr_gates.md; docs/kfr.md
links: temporal-crucible#68; temporal-crucible#69
takehome: Files containing goto get security fixes more often at equal size (1.59 on nDPI + openssl, 2.80 on five unseen repos), but the goto-to-lifetime-fault link (7.1×) did not replicate: goto is a general security-risk marker, not a fault-type fingerprint.
---

# goto, macros and specific fault types (KF, KF-R, KF-L)

## Question

DYN lumps two C constructs together: `goto` and function-like macros. Which one carries the effect? Does each go with its own kind of fault (`goto` with lifetime faults from cleanup paths, macros with bounds faults from byte-access arithmetic)? This was the first direct test of the engine's founding idea that specific keywords go with specific faults.

## Why we asked

DYN-H2 found about 2× the security-fix rate at equal size on nDPI and openssl. Fault types were available: OSS-Fuzz crash types for nDPI, CWE fields for openssl. Priors: H3 leaning supported (`goto fail` cleanup chains), H4 uncertain.

## What we did

- **KF.** 344 security-fix events pooled (nDPI 110, openssl 234), with DYN-H2's strata.
  - H1 and H2: `goto` and macros each, at equal size and evidence.
  - H3: the `goto` lifetime/bounds ratio.
  - H4: the macro bounds/lifetime ratio.
  - α = 0.01 / 4.
- **KF-R / KF-L**, registered before any new repo was cloned.
  - KF-R replicated H1 and H3 on five unseen libraries (libxml2, libtiff, libpng, libexif, file).
  - KF-L asked whether lifetime fixes land inside `goto`-containing functions, against same-size siblings.
  - Binding gates: engine function spans vs tree-sitter ≥ 95% (file failed at 94.0% and was dropped from KF-L), and the construct regex vs tree-sitter ≥ 98%.

## What we found

- **KF-H1 supported:** `goto` RR 1.59 (lo 1.23).
- **KF-H2 supported:** macros RR 1.34 (lo 1.05).
- **KF-H3 supported:** RR ratio 7.12 (lo 2.77) for lifetime vs bounds. It rests on only 26 lifetime events, and curl (context) did not show it.
- **KF-H4 not supported:** 1.42, inconclusive.
- **KFR-H1 supported on unseen repos:** `goto` RR 2.80 (lo 1.12, 78 events).
- **KFR-H3 not supported:** 0.54. On unseen repos `goto` goes with bounds faults at least as much as with lifetime faults.
- **KFL-H1 and KFL-H2 not supported.** Lifetime fixes land in `goto` functions about 2× as often as in siblings (90% CI 1.2–3.4), but the one-sided lower bound is 0.77, and the effect is not lifetime-specific.

## Take-home

"Keyword marks security-prone code" replicates for `goto`. "Keyword marks a specific fault type" does not: the one candidate failed on unseen data.

## What it changed

The engine's dynamism signal is described as a general security-risk marker, not a fault fingerprint. KF-H3 stands in the register as a two-repo result that did not travel.
