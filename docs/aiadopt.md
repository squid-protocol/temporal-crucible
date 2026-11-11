# AIADOPT — is code written with AI help followed by fixes more often? (EXPLORATORY)

**Type: exploratory.** No registration, no hypothesis fixed in advance, **no p-value is claimed** and no
number here is a program result. It exists to find out whether the owner's question — *did latent fixes
increase once AI agents came into use?* — is answerable from data already on disk, and what a real study
would need. Tool: `tools/aiadopt_eval.py` (`trend` / `repos` / `pooled`). Run 2026-11-11.

## The question, and what the data can carry

The exposure is a commit whose message carries an AI trailer (`Co-authored-by: Claude`, Copilot,
`Generated with Claude Code`). **This is a floor, not an adoption rate.** Most AI use leaves no trace, and
whether a trace is left is a project convention: harfbuzz marks 11.6% of its commits since 2025, curl 0.3%.
Any cross-repo comparison of the raw share measures conventions, not adoption, so every ratio below
stratifies by repo.

The outcome is: a classed fix commit (`tools/xc_harvest.py`) touches one of the same files within 90 days.
Every commit is required to have a full 90 days of follow-up, so recency cannot decide the comparison.

## 1 · The time trend does not support an AI cause

| year | fixes | latent % | regression % | other-fix % | AI-marked share of commits |
|---|---|---|---|---|---|
| 2018 | 3,506 | 0.46% | 9.98% | 84.6% | 0.00% |
| 2020 | 3,324 | 1.65% | 11.49% | 84.2% | 0.00% |
| 2022 | 3,095 | 1.74% | 13.38% | 80.8% | 0.00% |
| 2024 | 2,934 | 1.16% | 15.47% | 78.6% | 0.00% |
| 2025 | 3,551 | 0.82% | 16.02% | 79.4% | 0.17% |
| 2026 | 4,844 | 2.11% | 19.90% | 75.0% | 4.29% |

**Regression fixes have nearly doubled as a share of all fixes since 2018** — but the rise was well under
way through 2020, 2022 and 2024, when AI-marked commits were exactly zero. A trend that predates the
exposure is not caused by it. **Latent** fixes are flat-to-noisy on counts of 16–102, and latent is the
CVE-linked class, so recent years are censored by disclosure lag; the 2026 figure should not be read as a
rise. On this evidence the answer to the original question is **no, not visibly, and not from the trend**.

## 2 · The crude per-commit comparison is confounded

Crude rates disagree violently between projects — curl 1.95×, harfbuzz 1.25×, redis 0.73×, openssl 0.43×,
nDPI 0.38×. That is the signature of confounding, not of a weak effect. AI-marked commits are not the same
*kind* of commit from project to project: different sizes, different subsystems.

## 3 · Matched on size, area and breadth, the disagreement collapses

Strata: repo × commit size (lines changed) × top-level area × breadth (>3 files), Mantel-Haenszel.
This program's bar is lift over size, never a raw rate.

| repo | AI commits | AI events | plain | crude | **matched RR** | 95% CI |
|---|---|---|---|---|---|---|
| harfbuzz | 425 | 274 | 3,539 | 1.25× | **1.14×** | [0.99, 1.31] |
| prometheus | 41 | 23 | 3,677 | 1.29× | **0.96×** | [0.63, 1.48] |
| openssl | 44 | 7 | 5,211 | 0.43× | 1.15× | [0.55, 2.41] *underpowered* |
| curl | 18 | 16 | 6,867 | 1.95× | 1.59× | [0.95, 2.64] *underpowered* |
| redis | 23 | 10 | 1,049 | 0.73× | 0.81× | [0.43, 1.52] *underpowered* |
| nDPI | 29 | 7 | 1,072 | 0.38× | 0.72× | [0.33, 1.57] *underpowered* |

**openssl's crude 0.43× becomes 1.15× under matching** — the apparent "AI is safer" result there was
entirely confounding. Only harfbuzz and prometheus clear the program's ≥20-events-per-arm rule, and they
disagree in direction while both span 1.0.

**Pooled over 13 repos:** 583 AI-marked commits (339 followed by a fix) against 34,204 plain (15,816).
Crude **1.26×**; matched **1.114×, 95% CI [0.99, 1.26], z = +1.75**, 124 contributing cells.

## 4 · Reading

**Most of the crude gap is confounding, and what survives is consistent with no effect.** The pooled
interval touches 1.0 from above: a small positive association that does not clear significance and would
not survive any correction for the several cuts taken here.

What it does establish is that **the question is answerable** — 583 exposed commits with full follow-up and
a matched design is a real study, not a fishing trip — and that the crude framing people usually quote
(58% vs 46%) is worthless.

## 5 · Sibling studies in this program, and what they settle

Three AI studies landed the same day from another lane, all on the same trailer-declared exposure:
`docs/ai_comments_exploratory.md` (#153), `docs/ai_structure_exploratory.md` (#154) and the prospective
registration `docs/aic_hypotheses.md` (#155). They measure **structure** — AI-declared commits add more new
callees than the same author's other changes of the same size, median +0.28 per modified function, 11 of 13
authors — not whether the code is later fixed. This study is the defect-outcome arm and does not duplicate
them.

Two things they do better, and that a real version of this study should adopt:

- **A within-author contrast**, not a within-repo one. It compares an author's AI-marked commits against
  *that same author's* unmarked commits. That absorbs the selection this study cannot touch — who reaches
  for a tool, and how good they are — where matching on size and area absorbs only the commit's shape.
- **Prospective scoring.** AIC scores only commits made after its registration date, so no commit that
  suggested the pattern can confirm it. This study has the same hazard and no such protection, which is
  another reason nothing here is a verdict.

## 6 · What a real version needs

1. **A better exposure than the trailer.** It is a floor and a convention. The cleanest design is
   **harfbuzz alone, before and after its adoption date** — one project, one convention, no cross-project
   mixing, and the largest exposed set in the corpus by far — combined with the within-author contrast above.
2. **Confounding by indication is unfixed and unfixable here.** If people reach for a tool on code they
   already find hairy, matching on size does not help. A before/after design within one project narrows
   it; nothing in observational data closes it.
3. **A prior-work check before any registration**, which this exploratory pass deliberately skips; AIC's
   check is the place to start, since it covers the same exposure.
4. **Pre-registration** of one outcome, one window and one stratification. Six cuts were taken to get here
   and that is exactly why none of these numbers is a result.
