> **Status: design and prototype, not shipped.** Draft for GitGalaxy's `docs/wiki/`, written 2026-11-19 against the evolution-report prototype (`tools/report/evolution_report.py`). Exploratory unless a line says otherwise.

# Evolution report: comments

Three series from the scanner's comment counts at each quarterly scan.

| Chart | Definition |
|---|---|
| Comment lines per line of code | all comment lines (including licence banners and commented-out code) divided by code lines |
| Functions with a comment above them | share of functions with a comment block directly above; and share with a doc-style comment |
| Debt and fragility markers per 1,000 code lines | planned (TODO-type) and fragile (HACK, FIXME-type) markers |

## Measured behavior (exploratory, nine C projects; not computed for the repository shown)
- About three quarters of TODO, FIXME and XXX comments are eventually removed; projects range from 38% to 98%, and from months to decades. About half are cleared by their own author, and debt is repaid in clean-ups more than in fixes.
- A file keeps its commenting style for years; projects differ several-fold in comment density and header coverage.
- Danger wording ("careful", "do not", "hack") grew in most projects. In one test, danger comments at a function's birth went with later security fixes at 1.55 times the base rate, even in files with no security-fix history (mixed result, replication inconclusive).
- A file's comment profile adds nothing to predicting its next-year fixes beyond size, churn and history (replicated nulls).

## Limits
- Counts include licence banners, so a licence change shows as a step in the density line (in our research OpenSSL's per-file banner fell from about 53 lines in 2013 to about 10 in 2016).
- Older scans may not carry every field; a missing share is left blank.

## What to do about it
Use the comment trend to see when documentation habits changed, and the marker trend to see whether TODO debt is growing or being paid. Do not read comment density as a quality score.

## Not in the report yet
The research has more: commented-out code (about 93% precise), danger-word share, banner length, who wrote the comment, and AI-assisted commit comment patterns. They are candidates for a later version.
