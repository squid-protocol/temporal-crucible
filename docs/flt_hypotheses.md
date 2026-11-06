# FLT-H1..H3 — does the autonomous fleet write structurally different code from interactive Claude sessions? — registered 2026-11-06, before any attribution statistic

**Why.** GG found that the GitGalaxy repo's biggest structural break (the 2026-10-12 snapshot) coincides with the
autonomous churn fleet going unattended. Exploratory figures: births doubled, new functions were smaller and more
typed, and 59% of them landed in `gitgalaxy/tools/`. Both sides are Claude. This asks whether **fleet-written code has
its own fingerprint** compared with the owner's interactive Claude sessions in the same period.

## Labels, fixed from PR metadata (before any structural number)

**Source.** `events/sources/gitgalaxy_merged_prs_2026-11-06.tsv`: 5,823 merged PRs (number, head branch, merged at,
user), from the GitHub API.

| label | head branch | notes |
|---|---|---|
| **fleet** | `churn/…` (2,237 PRs, from 2026-10-11) or `fleet/…` (15, from 2026-09-27) | the autonomous worker lanes |
| **excluded** | `auto/…` (1,516: generated reports from `github-actions` / `squid-shepherd`), `dependabot/…` | bots, not authors |
| **interactive** | everything else (`fix/`, `feat/`, `feature/`, `docs/`, `ci/`, `chore/`, `claude/`, …) | owner-driven Claude sessions |

**Period.** Functions first seen in weekly snapshots dated **≥ 2026-10-05**, i.e. born on or after the first fleet PR
(2026-09-27), through 2026-11-02. Both groups come from the same weeks.

## Attribution

- For each function born in that period (GG's identity and move rule, the `gitgalaxy/` package, the same 32 weekly
  scans in `temporal-crucible-pool/gg_weekly_scans/`):
  `git blame --first-parent -L <start_line>,<start_line> <birth snapshot sha> -- <path>` gives the first-parent commit
  that last touched its `def` line.
- That commit's PR number comes from its subject: `(#N)`, or `Merge pull request #N`. The PR's head branch gives the
  label.
- Functions whose commit has no PR, or whose PR is excluded, are dropped.
- **Features:** GG's, at the birth snapshot (log loc, complexity/loc, args, keyword density, 32 per-line signal
  densities).

## Claims

| id | claim | supported iff |
|---|---|---|
| **FLT-H1** | fleet-born functions are structurally distinguishable from interactive-born ones in the same weeks, beyond drift within each group | 5-fold cross-validated AUC(fleet vs interactive) − max(AUC early-vs-late fleet, AUC early-vs-late interactive; split at each group's median birth date) > 0, bootstrap lower bound > 0 |
| **FLT-H2** | …**even in the same place**: within `gitgalaxy/tools/` only | the same test, restricted to functions in `gitgalaxy/tools/` |
| **FLT-H3** | the fleet writes more of its code in `gitgalaxy/tools/` | share in tools/ (fleet) − share (interactive) > 0, bootstrap lower bound > 0 |

- α = 0.01 / 3 one-sided.
- Each group needs ≥ 100 functions for H1 and H3, and ≥ 50 inside tools/ for H2. Otherwise not evaluable.
- GG's classifier: L2 logistic regression, standardised features.

**Descriptive.** Standardised mean differences of the features; archetype mix; median size; top directories.

## Priors

- **FLT-H1 leaning supported.** Fleet workers run under issue-scoped prompts, plan-first and CI gates, with a
  different task mix.
- **FLT-H2 uncertain.** Within the same directory, task type may dominate.
- **FLT-H3 leaning supported.**
- **The main confound** is task mix (fleet tasks are ladder, census and validation tooling). H2 is the partial control.

---

## Results — 2026-11-06 (scorer `7659c86` committed before running; report `flt.md`)

**Data.** 1,538 functions born from 2026-10-05: **fleet 636, interactive 899** attributed, 3 dropped (no PR in the
first-parent subject).

| claim | result | verdict |
|---|---|---|
| **FLT-H1** fleet vs interactive distinguishable beyond drift | AUC **0.640**; placebos: fleet early-vs-late 0.709, interactive 0.678; margin **−0.069** (lo −0.136) | **not supported** |
| **FLT-H2** …inside `gitgalaxy/tools/` | AUC 0.624 (343 vs 639); placebos 0.713 / 0.681; margin −0.089 | **not supported** |
| **FLT-H3** fleet concentrates in tools/ | share in tools/: fleet **54%**, interactive **71%**; difference **−0.17** (lo −0.24) | **not supported**: the opposite direction |

**Headline → the fleet writes Claude code.**
- Functions written by the autonomous fleet are **no more different from the owner's interactive Claude sessions than
  either group is from itself a few weeks later.** AUC 0.64 sits below both within-group drift placebos.
- Compare GG-H1: Gemini-era vs Claude-era AUC 0.877, with a +0.15 margin over the placebos.
- So the structural signature tracks the **model and its working regime**, not whether a person is in the loop.

**Corrects GG's exploratory note.** GG said post-break code went 59% into `gitgalaxy/tools/`, and attributed that to
the fleet. The attribution shows the reverse:
- **interactive** sessions wrote most of the new tooling (71% of their functions);
- the **fleet** worked relatively more in `gitgalaxy/core` (211 of 636 functions vs 133 of 899).

The October break is a **volume** step (both modes writing at once). It is not a fleet style.

**Small descriptive differences.**
- The fleet writes more Stateful Encapsulated Methods (38.8% vs 24.5%) and fewer Defensive Guards (5.0% vs 9.7%) and
  Generic/Templated code (20.6% vs 26.9%).
- Signal differences are small (|SMD| ≤ 0.22).
- Median size is the same (12 vs 11 lines).

**Caveats.**
- "Interactive" means non-fleet branches. Some of those sessions ran unattended too (`claude/…` worktree sessions).
- The labels rest on the PR that last touched each function's `def` line at its birth week.
- One repo.
