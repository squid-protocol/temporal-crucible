# Experiment E1: does a mechanical tick-side merge of main clear "conflicts with main" PRs cheaper and sooner than a send-back worker?

**Type:** confirmatory (agent utility, scope `AG-`)
**Registered:** 2026-10-27 — tc#46 · registration PR: this one   **Tracking:** gitgalaxy#6643
**Status:** registered; no arm has run. No result, no verdict (the result PR is separate, per CONTRIBUTING.md).
**What the answer would change:** whether a conflict send-back stays a worker item or becomes a tick step, and the
worker brief line "Before the final report" (`.claude/agents/gitgalaxy-pr-worker.md:82`). Per outcome:
- AG-H1 ✓, AG-H2 ✓, AG-H3 ✓: the gate does a mechanical merge for PRs whose conflicts are all in generated files, and
  queues a worker only for the rest. The brief line keeps its `merge-tree` check but drops "(generated files: take
  main's, regenerate)": the worker resolves hand-written conflicts only.
- AG-H4 ✓ (any outcome above): the tick's file list must be narrower than churn's `GENERATED_RE`. It may include only
  paths that a `tests/tools` script writes and can regenerate in under 10 minutes; `^docs/` as a blanket is out.
- AG-H3 ✗: conflicts stay a worker item and the brief line is unchanged.
- AG-H1 ✗ (the tick could clear 15% or less of conflicts): no tick step, whatever else holds.
- AG-H2 ✗ with AG-H3 ✓: the tick step is optional. It saves about $0.1-0.3 per conflict and no measurable time.
**Mode:** replay   **Budget:** $20.40 arms (2 × 6 × 2 × $0.85) + scoring $5 + log $3 (design $8 already spent).

**Why replay:** every task has ground truth. The PR's own conflict-resolving merge commit `M` exists, its first parent
is the PR head that conflicted, and its second parent is the main commit it conflicted with. An arm starts at `M^1`,
merges `M^2`, and is scored against `M` and the PR's tests. No open work is needed, and a live arm on a real
conflicting PR would race the real churn worker for that PR.

**Seen during design (exploratory, never re-tested here):** PRs merged 2026-10-18..24 (1006 PRs) contain 122
conflicting main-merges in 99 PRs. In 34 of them (28%) every conflicted path matches churn's `GENERATED_RE`. In 33 of
those 34 the worker's resolution differs from main's copy of the file, so "take main's" alone would not reproduce it.
The 6 replay tasks come from this window. The census claims (AG-H1, AG-H2) are tested on a window the designer did not
look at.

## Arms

| label | condition (the instruction its worker gets) |
|---|---|
| `sendback` | status quo: churn's PR-fix item, as a worker resolves it today |
| `tick` | a mechanical procedure, emulating a gate step with no judgement and no hand edits |

The exact arm texts are in `design.json` `arms` (same text, verbatim). Arms differ in ONE thing, how the conflict is
resolved. Everything else is identical: model (`sonnet`, churn's `arm_model`), base commit, task brief, $0.85 cap,
and the full gates at the end.

**Cost as it falls in real use.** The `tick` arm is a model emulating a script. In real use the gate runs those
commands and spends $0 on a model, so the arm's own token cost is reported separately as emulation overhead and never
counted as the policy's cost. Real-use cost per task:
- **send-back policy:** the `sendback` run's `cost_usd`.
- **tick policy:** $0 when the `tick` run is a correct clear. When it escalates, or clears but is not a correct clear,
  the conflict goes back to a worker, so the cost is the mean `sendback` `cost_usd` on that task.

These two are reported as a per-task table with totals. They are not a claim: with $0 for a correct clear, the
comparison follows from AG-H3. Historical send-backs (resumed sessions, 10-18..24) cost $0.10-$0.24, which bounds
what a tick step can save per conflict. Latency is the claim (AG-H2).

## Tasks (listed before any run; no earlier experiment used them)

Strata, declared mechanically:
- **G (tool-written):** every conflicted path is written by a script under `tests/tools`; the path or its basename
  appears there as an output. The tick is expected to be safe here.
- **T (trap):** the conflicted path matches `GENERATED_RE` (through `^docs/`) but no tool writes it. The tick's
  "take main's" is expected to drop the PR's change here.

Hand-conflict PRs, where some path fails `GENERATED_RE`, are not replayed. The tick escalates on them by rule, and the
outcome is the send-back by construction. They enter only the census.

| # | issue | stratum | base (= M^1, the conflicting PR head) | main to merge (= M^2) | reference M (the merged resolution) |
|---|---|---|---|---|---|
| 1 | 3799 | G, cheap regen (chart) | f57b50d72db3e44b7440a4495fea2c2cee53f343 | 2cf3b18a3f3ea4b01fe390f36487ed4d17884032 | 72e7257a9a3f3f9667529bea60f0f2ebf9b8c9db |
| 2 | 5401 | G, cheap regen (table from a committed results file) | b98bace7e027bed2c79e96002bc53299030040e9 | 148e7f5202d0a059cd85ac30cd835a5895899ca6 | c4323819f6cc7ac6585b964911c0b0ab79f33923 |
| 3 | 3798 | G, heavy regen (comparison ledger) | 9988123d9cddd14399edceb689348dd531e71010 | 5a65d81618c2825608ba9476dc5cb17773949b21 | 2658129528e8d8e14d171bb185ea6f811ada8fa3 |
| 4 | 5278 | G, heavy regen (sweep coverage ledger) | 5e7e0d7002a4a3b63b1af435d5cd69d59ae73092 | 362dcf113df80e31e0ccc72cbbe5ced6e9375f50 | 13dee003969b5c9bf647899522aa70b5bc7ae122 |
| 5 | 5543 | T (hand doc; the PR's only file) | 4bfb7f084d0e84470294fa59ba6035fcbb5db69b | 5c659544db348311613c1dae8449204d423979cb | 97ffff359afb39415ebfc121341fe7bdd8a4357d |
| 6 | 3189 | T (hand doc beside code) | 63866f890dd9b6cc9a4d3956f806d98efe9ce56d | 0c45dc645fc2fcc0f0f6dc9c5161ff075b34da03 | f1f563123089e0de81085765f361c64da1e5872e |

The scorer checked every sha in this table:
- every sha is present in the v6 object store;
- `git merge-tree --write-tree M^1 M^2` exits 1 for each task;
- each `M^2` is an ancestor of `main`.

The stratum notes in the table are for the scorer only. The arm briefs name no file: the arm learns the conflicted
paths from `git merge` itself, as a real worker does. Every brief names the issue, its title and the main sha to
merge. It gives no PR number, no commit message after the base and no file name.

**Replicates:** 2 per arm per task, 24 runs. The `tick` arm should be close to deterministic, so its replicate spread
measures how faithfully a model follows a script. The `sendback` spread measures worker variance. Both spreads are
reported. There is no cost-equivalence band: cost is not a claim.

## Rubric (scored per run, after the full gates ran on that run)

Notation: `mb` = merge-base(base, main), `P` = the paths the PR changed (`git diff --name-only mb base`), `C` = the
conflicted paths (`git merge-tree --write-tree --name-only base main`, lines after the tree id). "Added lines" means
the non-blank `+` lines of a diff.

| item | what is scored | how (mechanical) |
|---|---|---|
| R1 PR kept | the PR's change survives the merge | Over `P`: the share of the PR's added lines (`git diff mb base -- <p>`) present in the run's copy of `<p>`. A path that a tool writes counts 1 if the tool's check or freshness mode passes on the run's tree. Fraction; 1 = kept. |
| R2 main kept | main's change survives on the conflicted paths | The same, over `C`, with main's added lines (`git diff mb main -- <c>`). Fraction. |
| R3 PR tests | the PR's own tests pass on the merged tree | `python -m pytest <the tests/**/test_*.py paths in git diff --name-only mb M>` run in the run's worktree. The fraction that pass, or 1 when the list is empty. |
| R4 gates | the full gates are green | From `gates.txt` (full `pr_gates`, not `--fast`, plus the golden check the gates name). If a gate is red in a run, the scorer runs that gate once on `M`; a gate red on `M` too is excluded as pre-existing red. 0/1. |
| R5 reference agreement | the run reproduces the merged resolution | The share of paths in `C` whose run copy is byte-identical to `M`'s. Descriptive only: a regenerated file can legitimately differ. |
| R6 cleared | the conflict is gone without a worker | 1 when the run committed a merge commit with `main` as a parent, `git grep -nE '^(<<<<<<<\|>>>>>>>)'` over tracked files finds nothing, and the run did not escalate. An escalated run scores R6 = 0 and R1-R5 = n/a; its outcome is the send-back. |

**Correct clear** = R6 = 1 ∧ R1 = 1 ∧ R2 = 1 ∧ R3 = 1 ∧ R4 = 1.

Cost (`cost_usd`) and wall-clock (`started`..`finished`) come from churn's run meta, never from the run's notes. The
`Commands` section of `notes.md` gives each merge and resolution command with its seconds; it is used only for the
tick latency estimate in AG-H2.

The rubric defines "No worse". Better quality at a higher cost is reported as a result, not counted as a loss.

### Census (scored by the same session; no model runs)

Run this for the windows named in the claims. For each PR merged in the window:
1. Fetch `refs/pull/<n>/head`.
2. For every merge commit `M` reachable from it but not from `main`, with parents `M^1`, `M^2`: keep it when
   `git merge-tree --write-tree --name-only --no-messages M^1 M^2` exits 1.
3. Record `C`, and whether every path in `C` matches churn's `GENERATED_RE`, copied verbatim from
   `~/.local/src/churn/churn`:
   `(^docs/|det_sweep_coverage/|baseline[^/]*\.json$|ledger|_report\b|\.test_durations$|^tests/fixtures/evidence_report/|CHANGELOG)`.
4. **Onset** is the first commit `c` on main's first-parent chain from `merge-base(M^1, M^2)` to `M^2` for which
   `merge-tree M^1 c` exits 1; its committer time is the onset time.
5. **Status-quo latency** `L_sb` = committer time of `M` − onset time.
6. **Projected tick latency** `L_tick` = 10 min (the `churn-tick.timer` cadence, `*:00/10`, taken as the worst case)
   + the largest `tick`-run `Commands` total on any replay task.

The design window's numbers above count as seen data and are reported descriptively only.

## Blinding

- Runs carry churn's random blind ids. The label map stays in `.labels.json` until every score is recorded.
- The scorer never opens the map, the runs' prompts or churn's state.
- Notes and commits never name the condition.
- **Known leak:** a `tick` run's notes can reveal the procedure, for example an `ESCALATE:` line. This is why every
  rubric item above is a command or a line count, with no judgement call left to the scorer.
- The task brief asks both arms for the same `Commands` section, so its presence does not reveal the arm.

## Registered claims (verbatim; ids AG-H<n>)

> **AG-H1 (coverage):** Among conflicting main-merges on PR branches of PRs merged 2026-10-11..2026-10-17 (census
> above), the share whose conflicted paths all match `GENERATED_RE` is greater than 0.15. Test: one-sided exact
> binomial against p0 = 0.15, α = 0.05 / 4 = 0.0125 (Bonferroni over AG-H1..AG-H4). Power floor: at least 50
> conflicting merges in the window; below it, **not evaluable**.

> **AG-H2 (latency):** For the generated-only conflicting merges in the same window, the status-quo latency `L_sb`
> exceeds the projected tick latency `L_tick` (paired per merge, `L_sb − L_tick`, one-sided Wilcoxon signed-rank,
> H1: median > 0), α = 0.0125. The median difference is reported in minutes with a 95% Hodges-Lehmann CI. Power
> floor: at least 20 generated-only merges; below it, **not evaluable**.

> **AG-H3 (safety where tool-written):** Every `tick` run on stratum G (tasks 1-4, 8 runs) is a correct clear
> (rubric R1 ∧ R2 ∧ R3 ∧ R4 ∧ R6). There is no p-value: ✓ at 8/8, ✗ at any failure or escalation. The report gives
> the exact one-sided 95% lower bound on the correct-clear rate (0.688 at 8/8) and the `sendback` arm's correct-clear
> count on the same 8 task-replicates.

> **AG-H4 (the pattern is too broad):** At least one `tick` run on stratum T (tasks 5-6, 4 runs) drops the PR's change
> (R1 < 1). There is no p-value: ✓ at one or more such runs, ✗ at none.

Power floor for the replay claims: n is fixed at 8 (AG-H3) and 4 (AG-H4) runs. They are exact-count criteria, not
tests, and say so. Not evaluable when fewer than 6 G runs or 3 T runs finished with a scoreable tree.

## Stop rule and cleanup

- Stop when all 24 planned runs finished, or when the next run would push spend past the budget (churn's check:
  spent + $0.85 + scoring + log > $40). Score what ran and say which runs were skipped.
- A run that hits its $0.85 cap is scored on the tree it left: an unfinished merge scores R6 = 0.
- A run whose worktree failed is not relaunched; it is reported as missing.
- The census claims are scored whatever happens to the replay.
- Replay arms open no PRs and never push. Churn removes their worktrees and `exp/E1-*` branches. The tracking issue
  gitgalaxy#6643 closes with a link to the result PR.

## Result (in the result PR only)

| id | verdict | statistic | evidence |
|---|---|---|---|
| AG-H1..AG-H4 | ✓ / ✗ / ⚠ / not evaluable | ... | ... |

The result PR adds:
- a per-run table: blind id, condition, task, replicate, R1..R6, correct clear, `cost_usd`, minutes, command seconds;
- the real-use cost table per task (both policies);
- the census rows for the claim window.

It also states what the result does NOT establish. A replay task is a resolution someone already made under that
day's main. A fresh `sendback` worker lacks the resumed session's context, so it is a lower bound on a real send-back's
quality and an upper bound on its cost. Six tasks cannot cover every generated-file family.
