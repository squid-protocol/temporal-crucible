---
date: 2026-11-11
title: Does AI-assisted code get fixed more often?
type: exploratory
status: scored
verdict: inconclusive
theme: defect-prediction
ids:
docs: docs/aiadopt.md
links: temporal-crucible#157; temporal-crucible#159
takehome: Code in declared-AI commits is followed by a fix no more often than the same author's own code of the same size (0.984×, CI 0.87–1.11, 339 events); the striking crude gap (58% vs 46%) is composition — one maintainer supplies 387 of 583 AI-marked commits — and the regression-fix share nearly doubled since 2018 but the rise predates AI entirely.
---

## Question

The owner asked it in plain words: **did latent fixes increase over time once AI agents came into use?** Behind
it sits the ceiling result from the same day — the unexplained headroom in fix prediction is either unused
covariates or the discovery process, and if AI changed who writes code and how, the record should show it.

## What we did

Exposure: a commit whose message carries an AI trailer (`Co-authored-by: Claude`, Copilot, `Generated with
Claude Code`). Outcome: a classed fix commit touches one of the same files within 90 days, with every commit
required to have a full 90 days of follow-up so recency cannot decide it. Thirteen repos, `tools/aiadopt_eval.py`.

Three contrasts, each answering the objection to the one before it:

1. **Time trend** — fix-class mix by year, 2018–2026.
2. **Within-repo matching** — repo × commit size × top-level area × breadth, Mantel-Haenszel.
3. **Within-author matching** — repo × author × size, so a person is compared with themselves.

## What we found

**The trend does not implicate AI.** Regression fixes nearly doubled as a share of all fixes, 9.98% (2018) to
19.90% (2026). But the rise was well under way in 2020, 2022 and 2024, when AI-marked commits were exactly
zero; trailers appear only in 2025 (0.17%) and 2026 (4.29%). Latent fixes are flat-to-noisy on counts of
16–102, and latent is CVE-linked, so recent years are censored by disclosure lag.

**The crude per-commit gap is large and worthless.** AI-marked commits are followed by a fix 58.1% of the time
against 46.2% — but per-project ratios run from 0.38× (nDPI) to 1.95× (curl). That spread is confounding, not
a weak effect.

**Within repo, most of it dissolves.** openssl's crude 0.43× becomes 1.15×; pooled, 1.26× becomes **1.114×,
95% CI [0.99, 1.26]**.

**Within author, all of it dissolves.** **0.984×, 95% CI [0.87, 1.11]**, z = −0.27, on 339 events in the AI
arm — a powered null, stable under a tighter stratification (1.054×) and a doubled follow-up window (0.955×).
The sign test lands where no effect lands: of 10 authors with ≥5 commits in both arms, 5 up and 5 down.

The mechanism is visible per author: harfbuzz's maintainer supplies **387 of the 583** AI-marked commits in
the corpus, at 63.0% against his own 59.3%. The pooled residual was **composition** — which authors adopt AI,
not what AI does.

## Take-home

Code in declared-AI commits is followed by a fix **no more often than the same author's own code of the same
size** (0.984×, CI 0.87–1.11, 339 events). The striking crude gap — 58% against 46% — is composition, and the
regression-fix share nearly doubled since 2018 but the rise predates AI entirely.

## What it changed

It converts a question people answer with the crude number into a measured null, and it demonstrates on this
program's own data that the AI-vs-human comparison is dominated by *who* rather than *what*. It sits beside
the same day's structural work (`ai-structure`, `ai-comments`, AIC) as the defect-outcome arm, and beside ARG,
which registers the prospective version this entry cannot supply.

**What it does not establish.** The exposure is declared-only — a floor and a project convention (harfbuzz
marks 11.6% of commits, curl 0.3%). Confounding by indication survives a within-author contrast: a person may
still reach for a tool on their hairier tasks. Six cuts were taken to reach the null, which is exactly why it
is exploratory and why ARG's prospective looks matter.
