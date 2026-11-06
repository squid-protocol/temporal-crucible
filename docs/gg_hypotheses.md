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

---

## Results — 2026-11-06 (gate `gg_gate.md`; scorer `b930c1b` committed before running; report `gg.md`)

**Gate G-PY: PASS.** Engine vs tree-sitter-python on the head package: recall 99.71%, precision 100% (3,136 / 3,145
functions).

**Data.** 32 weekly snapshots. Functions born: Gemini era 366, Claude era 2,549, transition 35 (excluded).

| claim | result | verdict |
|---|---|---|
| **GG-H1** era distinguishable beyond within-era drift | cross-era AUC **0.877**; placebos: early vs late Gemini 0.725, early vs late Claude 0.669; margin **+0.152** (lo +0.086) | **SUPPORTED** |
| **GG-H2** drastic change point at the switch | both best breaks (keyword mix and `sfs` fingerprint) land on **2026-10-12**, not in 07-01 → 08-12 | **not supported** |
| **GG-H3** Gemini code rewritten faster after the switch | weekly death hazard of Gemini-born functions: before 0.026, after **0.0065**; ratio **0.25** | **not supported**: the opposite direction |

### What distinguishes the eras (descriptive)

Standardised mean differences, Claude − Gemini, at birth:
- **Shorter** (log loc −0.78).
- **Denser branching** (complexity/loc +0.76, branch hits +0.79).
- **More generics / type syntax** (+0.81).
- Higher keyword density (+0.81).
- **Fewer print statements** (−0.62).
- More encapsulation (+0.34).

Archetype mix of functions born in each era:

| archetype | Gemini | Claude |
|---|---:|---:|
| Many-Argument Workhorses | **29.5%** | 8.9% |
| I/O & Config Routines | **7.7%** | 0.4% |
| Generic / Templated Code | 9.8% | **22.4%** |
| Encapsulated Accessors | 4.9% | **11.7%** |
| Stateful Encapsulated Methods | 29.5% | 33.9% |

**The two eras in a sentence.** Gemini-era code is fewer, larger, many-argument "workhorse" functions with print-style
I/O. Claude-era code is many small, typed, branch-dense helpers and accessors.

### Why the claims came out as they did

- **H2.** The largest structural break is not the model switch but the **scale-up**. Between 2026-09-14 and 10-26 the
  package went from 413 to 2,769 functions, during the autonomous-fleet period (995 commits in the week of 10-19).
  The switch week itself shows only a small retention dip (0.85 on 07-27).
- **H3.** Gemini-era code died *more* while it was young (infant mortality, as NH found), not after Claude arrived.
  By July it had settled. Claude mostly **added around it** rather than rewriting it.

### Caveats (these bound GG-H1)

1. **The era is a whole regime, not only a model.** The Claude switch coincided with:
   - adopting mypy and ruff (the first Claude-era PRs are "clear all N mypy errors…" sessions, which plausibly drive
     the type-syntax difference);
   - PR-based workflow, CI gates and CLAUDE.md conventions;
   - a different phase of the product (mainframe/COBOL tooling).

   The placebos remove ordinary drift, but not a simultaneous process change. **GG-H1 shows the eras are
   structurally distinct, not that the model alone caused it.**
2. **One repo, one owner.**
3. **ChatGPT commits** (a few) count with their era.
4. Gemini-era sample: 366 functions.

**What would isolate the model.** Same task, same repo state, same rules, Claude vs Gemini side by side. That is the
design of the population-analyses `agent-habits` studies, whose results this entry did not read.
