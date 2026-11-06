# GG — the GitGalaxy repo's own history: does the Gemini → Claude switch leave a structural mark? — registered 2026-11-06, before any scan

**Why.** The owner built GitGalaxy first with Gemini, then with Claude (small ChatGPT share). Two questions:
- **Model fingerprint:** is code written in each era structurally distinguishable, the way projects are (SFS-H1 99%)?
- **Change point:** does the codebase show a drastic structural change at the switch?

## The switch, fixed from commit metadata only (before any structural number)

**Source.** `git log --first-parent` of `squid-protocol/gitgalaxy` @ `601af3e57`: 6,056 first-parent commits,
2026-03-21 → 2026-11-06.

**Markers by week.**
- No commit before the week of 2026-07-20 carries a Claude marker: a `Co-Authored-By: Claude` trailer, a
  "Generated with Claude Code" footer, or `noreply@anthropic.com`.
- The **first Claude-trailer commit is `67c1fd6f1` on 2026-07-22** (#302). Marked shares then run ~25–30% in August
  and 95%+ by late October.

**Style.**

| period | PR number in subject | conventional-commit subjects | committing identity |
|---|---:|---:|---|
| ≤ 07-05 | 1% | 29% | mostly `squid-protocol` |
| 07-06 → 07-21 (transition) | 45% | 82% | mixed, bots |
| 07-22 → 08-31 | 99% | 81% | `Joe Esquibel` |

**Eras (binding).**
- **Gemini** = before 2026-07-06.
- **Transition** = 2026-07-06 → 2026-07-21, excluded from era comparisons.
- **Claude** = from 2026-07-22.

The owner reports small ChatGPT mixes. They cannot be separated and count with their era.

## Data

- **Snapshots:** weekly. The last first-parent commit before each Monday 00:00 UTC, from 2026-03-23 to 2026-11-02.
- **Scope:** Python files of the **`gitgalaxy/` package** only, the engine code (16 → 314 files over the history),
  exported per snapshot with `git archive`. `tests/` is reported descriptively only.
- **Scans:** engine `32619e4a5` (the study's pinned build), ablated history, `--spec-alignment`.
- **Function identity:** NH's (file, name) plus the move rule. A function's **birth week** is its first snapshot, and
  its era is that of its birth week's interval.
- **Features per function** at its birth snapshot:
  - log₁₀(loc), complexity / loc, args, keyword_density;
  - the 32 per-function signal counts `sfs` reads, each as log1p(count / loc).

## Gate (binding, before any claim)

**G-PY.** The engine's Python function extraction against tree-sitter-python (`function_definition`, methods
included) on the head snapshot of `gitgalaxy/`. Recall and precision of (file, name, start line) must be ≥ 95%.
Otherwise the study stops.

## Claims

| id | claim | measure | supported iff |
|---|---|---|---|
| **GG-H1** | **functions written in the Claude era are structurally distinguishable from Gemini-era ones, beyond ordinary drift over time** | L2-logistic classifier, 5-fold cross-validated AUC, Gemini-born vs Claude-born. **Placebos:** the same classifier separating early vs late *within* each era (split at that era's median birth date) | AUC(cross-era) − max(AUC placebo-Gemini, AUC placebo-Claude) > 0, with bootstrap (over functions, on out-of-fold scores) lower bound > 0 at α = 0.01 |
| **GG-H2** | **the codebase changes drastically at the switch** | best single change point of two weekly series: (a) the package's `fam_*` keyword mix, the break maximising JSD between segment means; (b) the `sfs` fingerprint, the break maximising the mean between-segment profile distance | **both** best breaks fall within 2026-07-01 → 2026-08-12 |
| **GG-H3** | **Gemini-era code was rewritten faster after the switch** | weekly hazard that a Gemini-born function dies (deleted or renamed away), 8 weeks after 07-22 vs 8 weeks before 07-06 | ratio > 1, bootstrap (over weeks) lower bound > 1 |

**Descriptive.**
- The features that separate the eras most, as standardised mean differences.
- Archetype mix of functions born in each era.
- Function size and complexity over time.
- Weekly `sfs` twin retention.
- Growth of package vs tests.

## Priors

- **GG-H1 leaning supported.** Agents have habits, and the population-analyses agent-habits work exists, though its
  results were not read for this entry.
- **GG-H2 uncertain.** The transition was gradual: Claude-marked shares rose over months.
- **GG-H3 uncertain.**
