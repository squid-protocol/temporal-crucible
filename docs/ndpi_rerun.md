# nDPI: the founding claim's second half (2026-11-13)

"Recidivism replicated on curl + nDPI, p<1e-4" is the programme's one cross-repo claim. curl's half was
re-run and defended. This is nDPI's.

Built for it: a 43-snapshot quarterly walk (2015–2025) and a 5,428-commit history (1,206 keyword fixes).
Design is HR-1's, unchanged. **Neither of nDPI's labels clears the 0.70 gate** — raw 0.67, v3c 0.68 — so both
runs are `--allow-unfit` and everything below carries that.

## Result

| label | precision | positives | AUC(LOC) | AUC(recidivism) | lift | 95% CI |
|---|---|---|---|---|---|---|
| raw | 0.67 | 268 | 0.773 | 0.838 | **+0.065** | [+0.024, +0.106] |
| v3c | 0.68 | 57 | 0.806 | 0.771 | **−0.035** | [−0.100, +0.034] |

Under cleaning the effect **reverses and loses significance** — the CGR pattern, not curl's.

## Against its own null

Announcement spread for nDPI: **τ_author = 0.77, τ_file = 0.00, combined 0.77** (a 7.2× spread). The
file-level component is zero, which is unusual in this bank and means essentially all of nDPI's announcement
heterogeneity is between *people*.

| τ | null median | null 95th | null max |
|---|---|---|---|
| 0.00 | +0.030 | +0.092 | +0.124 |
| 0.40 | +0.068 | +0.129 | +0.167 |
| **0.77 (measured)** | **+0.132** | +0.188 | +0.215 |
| 1.00 | +0.173 | +0.222 | +0.242 |

**Observed raw lift: +0.065.**

It is **inside the null at every τ, including τ = 0.** At nDPI's measured spread the null *median* is +0.132
— more than double the observed lift. Even with no announcement heterogeneity at all, this measurement
manufactures lifts up to +0.12 on nDPI's file set.

## Verdict

**The nDPI half of the founding claim does not survive.** It fails on the cleaned label (reverses to −0.035)
and it fails on the raw label too (inside its own null, below the null median at the measured spread).

So the claim "replicated on curl + nDPI" now reads: **curl holds; nDPI does not.** The programme's one
cross-repo replicated predictor rests on **one repository**.

## Caveats, stated

- **Both nDPI labels are under the gate** (0.67 / 0.68). This is the repo where cleaning barely helped,
  because its raw label was already the best of the three pilot repos — there was less cosmetic noise to take
  out, and what remains are judgement calls (platform fixes, fuzzing infrastructure, a dissector added under
  `Fixes #1223`).
- **The outcome window is truncated.** The cut falls at 2024-09-25 and the registered window runs 24 months,
  but the history ends in 2025, so roughly the last nine months of the window do not exist. Positives are
  therefore undercounted (268 raw, 57 cleaned). This makes the estimate noisier and, if anything, works in
  nDPI's favour — it is not the reason the effect fails.
- **τ_file = 0.00** is worth noting rather than trusting blindly: with 195 files over a short history, the
  delta-method correction can absorb the whole observed spread. The author component (0.77) is the solid part.
