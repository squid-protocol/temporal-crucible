# `other-fix` precision audit — the three PILOT repos (curl, nDPI, openssl)

**2026-11-13.** `docs/otherfix_audit.md` audited the residual `other-fix` class on the eight CGR repos and
never covered the three repos that carry the programme's foundational claims. `docs/xc_label_audit.md` covers
curl, nDPI and openssl **by class** — regression, extrinsic, latent — but not the residual.

That residual is **77–86% of the outcome mass** in all three: curl 6,417 of 8,352 events (77%), nDPI 1,301 of
1,519 (86%), openssl 7,704 of 8,996 (86%). It is the de facto dependent variable, and its precision had never
been measured for any of them.

Method, identical to the 11-11 audit: seeded random sample (seed 2982), 30 per repo, drawn by
`tools/otherfix_sample.py` from `other-fix` only, judged from the commit subject. A commit counts iff it
**repairs behaviour that was wrong**. It does not count if it is a feature or refactor whose message carries a
fix word, a docs / tests / build-only change, or a cosmetic or warning-only change.

## Result — all three fail the 0.70 gate

| repo | precision | `other-fix` events | share of outcome mass | verdict |
|---|---|---|---|---|
| **nDPI** | **20/30 = 0.67** | 1,301 | 86% | **FAIL** |
| **curl** | **19/30 = 0.63** | 6,417 | 77% | **FAIL** |
| **openssl** | **15/30 = 0.50** | 7,704 | 86% | **FAIL** |

Pooled: **54/90 = 0.60**.

For comparison, the same gate on the named classes (`xc_label_audit.md`): curl regression 0.87, latent 1.00;
nDPI regression 0.77, latent 0.70; openssl regression 0.73, latent 0.90. **The audited classes pass and the
unaudited majority class does not.**

## What the misses are

The failures are not random noise; they cluster, and differently per repo.

- **openssl (0.50)** — the worst, and the most mixed: build-breaks (`Fix build-break`, `Fix test builds`),
  compiler and format warnings (`Use proper printf format for size_t`, `fix all the warnings in our demos`),
  renames (`Rename EVP_PKEY_get0_first_alg_name`), tooling (`check-format.pl: fix false positive`), typos, and
  outright features (`Implement known-IV countermeasure`, `riscv: sha256: Provide a Zvknha-based
  implementation`).
- **curl (0.63)** — dominated by compiler-warning commits (`minor fixes for compiler warnings`,
  `Fixed compilation warning`, `Fixed compilation warnings from features being disabled`), test-only ASan
  fixes, example-program changes, build fixes, and prose tooling (`badwords: add more contractions`).
- **nDPI (0.67)** — the cleanest of the three: build/compile fixes, `-Wunused-variable`, a typo, a new fuzzer,
  and feature work labelled as improvement (`Domain Classification Improvements`, `Add sub-classification for
  GQUIC`, `Jabber: remove support for UDP`).

## Why this matters more than the CGR result

The CGR eight are a replication cohort. **curl, nDPI and openssl are where the programme's cross-repo claims
were established** — recidivism "replicated on curl + nDPI, p<1e-4" among them. The class carrying most of
that outcome mass is now measured at 0.50–0.67, under the gate the programme set for itself.

This does **not** retract those findings. It says their dependent variable has a measured precision that was
previously unknown, and that precision is below the programme's own bar. Two things follow:

1. Any claim resting on `other-fix` in these repos should carry this number, as the LABEL CARD now requires.
2. **FIXLIKE v3c should be run on these three.** On the CGR eight it lifted pooled precision 0.38 → 0.77 and
   took 7 of 8 repos over the gate. If it does the same here, the claims can be re-grounded rather than
   caveated. That is the obvious next measurement and it is cheap.

## Limits

Judged from the subject alone, like the audits it extends, so a commit whose subject understates a real
behavioural fix is scored against the label. n = 30 per repo gives a 95% interval of roughly ±0.17, so
"fails the gate" is firm for openssl and marginal for nDPI.
