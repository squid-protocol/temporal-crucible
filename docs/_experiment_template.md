<!--
Template for a temporal-crucible experiment write-up. Copy to docs/<name>.md, fill in,
delete this comment. A confirmatory doc MUST cite its pre-registration and report every
registered verdict either way; an exploratory doc claims no p-values and says so up top.
Add the experiment's row(s) to docs/EXPERIMENTS.md and (for confirmatory) docs/HYPOTHESES.md
in the same PR. See CONTRIBUTING.md — registration and verdict never ship together.
-->

# <Experiment title>

**Type:** confirmatory | exploratory
**Registered:** <date> — epic gitgalaxy#2982 comment <id> · tc#<n>   *(confirmatory only)*
**Predictor(s):** <what GitGalaxy measures>  **Outcome:** <label family>  **Repo:** <curl | nDPI | openssl | ...>
**Tool:** `tools/<script>.py`   **Data:** `events/<repo>.json` (pool_head `<sha>`)

## Registered claim (verbatim)

> <the direction + test + α, quoted exactly as registered — before any statistic ran>

## Guards (all required; say which apply and how)

- [ ] Temporal ablation (`GITGALAXY_DISABLE_GIT_HISTORY=1`, via `SCAN_ENV`)
- [ ] Size-matched controls / length-matched pairs at the grain being tested
- [ ] Rename tracking (`git diff --name-status -M`)
- [ ] ≥20-positive power rule per evaluated cell
- [ ] Multiple-comparison correction (Bonferroni) on any table wider than one claim
- [ ] Defect-lift-over-LOC bar (not raw correlation) — the gitgalaxy#2987 gate

## Result

| id | verdict | statistic | evidence |
|---|---|---|---|
| <ID> | ✓ / ✗ / ⚠ | <p, effect, n> | <cell> |

For any null claimed as a *replicated null* (not merely underpowered): report the
equivalence (TOST) CI and the δ it must fall within.

## Reading

<what it means; what it changes about program standing; what it does NOT establish>

## Follow-ups registered (for unseen data only)

<any exploratory observation graduating to a registration — names the data it will be
tested on, never the data that suggested it>
