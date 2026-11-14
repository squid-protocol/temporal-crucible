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

---

# Round 2 — FIXLIKE v3c on the pilot repos (2026-11-13)

v3c run with `tools/fixlike_v2.py --repos curl,ndpi,openssl --rules v3c`. Across the three it drops **49.1%**
of `other-fix` events (15,422 → 7,844): curl 6,417 → 2,781, nDPI 1,301 → 961, openssl 7,704 → 4,102.

Fresh confirmatory sample: seed **2984**, 25 per repo, drawn from the v3c survivors only, with all 90
round-1 commits excluded. Same judging rule.

| repo | raw (round 1) | **v3c** | change | verdict |
|---|---|---|---|---|
| **openssl** | 15/30 = 0.50 | **20/25 = 0.80** | **+0.30** | **PASS** |
| **curl** | 19/30 = 0.63 | **20/25 = 0.80** | **+0.17** | **PASS** |
| **nDPI** | 20/30 = 0.67 | **17/25 = 0.68** | +0.01 | marginal FAIL |

Pooled v3c: **57/75 = 0.76**, against 0.60 raw — and in line with the 0.761 the CGR eight returned on their
own confirmatory round.

## Reading

**Two of the three repos carrying the programme's founding claims now have a label over the gate**, and
openssl moves furthest: from the worst label in the bank (0.50) to 0.80. What v3c removes from these repos is
what it removed from the others — compiler warnings (`Fix warnings about mismatched prototypes`), build
fixes, licence notes, and type-sweep refactors.

**nDPI barely moves, and that is informative rather than disappointing.** Its raw label was already the best
of the three (0.67), so there was less cosmetic noise to remove; what survives and still fails are genuine
judgement calls — platform fixes (`Fix armhf`), fuzzing infrastructure, a dissector added under
`Fixes #1223`. At n=25 the 95% interval is roughly ±0.18, so 0.68 is not distinguishable from the 0.70 gate;
it is marginal, not refuted. **nDPI needs a larger sample or a better rule, not another cleaning pass.**

## What this does for the standing claims

"Recidivism replicated on curl + nDPI, p<1e-4" rested on a dependent variable now measured at 0.63 and 0.67
raw. Under v3c, curl's is 0.80 and nDPI's is 0.68. **The curl half of that claim can be re-grounded on a
label over the gate; the nDPI half cannot yet.** Re-running the claim on the v3c label is the obvious next
step, and it is exactly the re-run that reversed the CGR result — so it should be done before the claim is
repeated, not after.
