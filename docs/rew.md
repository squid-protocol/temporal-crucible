# REW-H1..H4 — rewiring, nesting depth and the kind of fix (SCORED)

Registration: [`rew_hypotheses.md`](rew_hypotheses.md), approved 2026-11-11 before any statistic; Amendment 1 (function-grain power, split replication, regression = the union of both sub-classes) applies. Tool `tools/rew_eval.py`. Window **180 days**, budget **20% of lines**, α = 0.01 per claim (0.0025 within REW-H2), 5000 snapshot bootstrap rounds, seed 2982. Cells under 20 positives are printed UNDERPOWERED and not read.

Unit: a function at a quarterly snapshot **that was also present at the preceding snapshot** — rewiring is a between-snapshot measure, so a function's first appearance has none.

## Result

**All three substantive claims fail, in the same direction and in both repos: at function grain, under a 20%-of-lines review budget, nothing here beats ranking by size.**

| claim | what was registered | verdict |
|---|---|---|
| REW-H1 | rewiring predicts extrinsic fixes beyond every baseline | **not supported** (curl), **not supported** (libarchive) |
| REW-H2 | that lift is larger for extrinsic than for the other classes | **not larger** — extrinsic is the *worst* of the four classes, so there is no class specificity to explain |
| REW-H3 | nesting depth predicts latent fixes beyond size and branch count | **not supported** (curl), **not supported** (openssl) |
| REW-H4 | the guard: report an equivalence test rather than 'inconclusive' | fired; see below |

The guard earns its place. Rewiring is **not** churn in disguise — it beats the edit-count baseline by a wide margin — but it loses to the stronger size order, and so does nesting depth, and so does every other predictor tried here. The registration's reading that 'structure describes, history predicts' is not rescued by a class split: the class split was measured and the predicted class came last.

A note on what the bar is. The baseline is `max(big-files-first, small-files-first)` and at function grain small-first is strong, because a 20% line budget buys many small functions and fixes are not rare enough to be concentrated in the big ones. That is the bar the registration set, deliberately, before any of this was computed.

## Positives per cell (function-snapshots with a fix of the class in the window)

| repo | scored snapshots | extrinsic | latent | regression | other-fix |
|---|---:|---:|---:|---:|---:|
| curl | 104 | 1,762 | 788 | 2,823 | 17,383 |
| libarchive | 69 | 1,630 | 0 | 171 | 4,371 |
| openssl | 109 | 1,502 | 796 | 1,175 | 28,224 |

## REW-H1 (primary) — rewiring predicts extrinsic fixes beyond every baseline

Lift = recall@20% of lines for rewiring **minus the strongest of** {stronger size order, branch count, edit count, fan-in level, fan-out level}. The registration requires it to beat all of them, so the single strongest baseline per snapshot is subtracted.

| repo | snaps | positives | rewire | strongest baseline | lift | lo (α=0.01) | 90% CI | verdict |
|---|---:|---:|---:|---:|---:|---:|---|---|
| curl | 100 | 1,762 | 0.234 | 0.428 | -0.194 | -0.256 | [-0.237, -0.152] | **not supported** |
| libarchive | 65 | 1,630 | 0.301 | 0.486 | -0.185 | -0.275 | [-0.248, -0.124] | **not supported** |

Baselines separately (mean recall@20 over scored snapshots):

| repo | rewire | stronger size | branch | edit count | fan-in | fan-out |
|---|---:|---:|---:|---:|---:|---:|
| curl | 0.234 | 0.364 | 0.109 | 0.119 | 0.248 | 0.115 |
| libarchive | 0.301 | 0.351 | 0.199 | 0.216 | 0.214 | 0.082 |

## REW-H2 (class specificity) — the lift must be larger for extrinsic than for the rest

Paired by snapshot within the primary repo. A lift that is flat across classes is reported as **churn in disguise**, not as support for REW-H1.

| comparison | snaps | lift(extrinsic) − lift(class) | lo (α=0.0025) | 90% CI | verdict |
|---|---:|---:|---:|---|---|
| extrinsic − latent | 56 | -0.005 | -0.169 | [-0.100, +0.087] | **not larger** |
| extrinsic − regression | 72 | -0.116 | -0.211 | [-0.173, -0.059] | **not larger** |
| extrinsic − other-fix | 100 | -0.088 | -0.166 | [-0.130, -0.047] | **not larger** |

Per-class lift over the strongest baseline, curl (descriptive):

| class | snaps | positives | rewire | strongest baseline | lift |
|---|---:|---:|---:|---:|---:|
| extrinsic | 100 | 1,762 | 0.234 | 0.428 | -0.194 |
| latent | 58 | 788 | 0.255 | 0.493 | -0.238 |
| regression | 73 | 2,823 | 0.252 | 0.379 | -0.127 |
| other-fix | 104 | 17,383 | 0.226 | 0.335 | -0.108 |

## REW-H3 — maximum nesting depth predicts latent fixes beyond size and branch count

Depth is measured with tree-sitter at each snapshot (`kwnest_eval.keyword_profile`), the first time this program has measured it: `complexity` in the walk database equals `struct_branch`, the branch count. Lift = recall@20 for max depth minus the stronger of {stronger size order, branch count}.

| repo | snaps | positives | depth coverage | max depth | stronger baseline | lift | lo (α=0.01) | 90% CI | verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| curl | 58 | 788 | 99% | 0.169 | 0.387 | -0.218 | -0.327 | [-0.292, -0.144] | **not supported** |
| openssl | 75 | 796 | 98% | 0.292 | 0.338 | -0.046 | -0.146 | [-0.117, +0.021] | **not supported** |

## REW-H4 (guard) — if REW-H1 fails, an equivalence test, not 'inconclusive'

REW-H1 did not pass, so the registered TOST applies. Rewiring **minus the churn baseline (edit count)** on curl extrinsic: mean **+0.115**, 90% CI [+0.076, +0.157], δ = ±0.02.

**Not equivalent within δ: the interval lies entirely above the margin.** Rewiring is **better** than the churn baseline by +0.115, so it is not churn in disguise — it is a better-than-churn predictor that still loses to size.

## What this cannot establish

Carried from the registration §7, unchanged by the result: rewiring is chosen by developers, not assigned. A function gets rewired because someone decided to change it, possibly because they already suspected it. Confounding by indication is not closed by any control here, so a positive REW-H1 says rewiring **marks** extrinsic risk, never that it causes it. curl plus libarchive is two C projects: a pass is a replicated development-set result, not a panel result.

Measurement limits specific to this run:

- A function's **first** snapshot has no rewiring value and is excluded, so short-lived functions are under-represented.
- Identity is `(canonical file path, function name)` with the registered `-M` rename map applied and chg_eval's single-name move rescue; a function renamed in place still reads as a death and a birth.
- An **edit** is a change in the function's `(loc, struct_branch, struct_linear, call set, references)` fingerprint between snapshots — a proxy for a source edit, not a diff.
- The walk is quarterly, so rewiring that happened and reverted inside a quarter is invisible, which pushes the measured rewiring rate **down**.

Runtime 79s.
