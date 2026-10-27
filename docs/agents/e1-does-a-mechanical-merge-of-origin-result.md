# E1 result: does a mechanical tick-side merge clear "conflicts with main" PRs?

**Type:** confirmatory (agent utility, scope `AG-`). **Registered:** the registration is a separate PR
(temporal-crucible#47, `docs/agents/e1-does-a-mechanical-merge-of-origin.md`), which was still open when this was written.
This document ships the verdicts only; the claims are those registered there.
**Predictor:** conflict resolved by a mechanical tick procedure (`tick`) vs a send-back worker (`sendback`).
**Outcome:** rubric R1..R6 per run, cost, wall-clock. **Repo:** gitgalaxy (replay of 6 historical conflict merges).
**Tracking:** gitgalaxy#6643. **Data:** 24 runs (6 tasks x 2 arms x 2 replicates), all finished and scored; none skipped.

## Verdicts

| id | verdict | statistic | evidence |
|---|---|---|---|
| AG-H1 (coverage) | **not scored** | census not run | The 2026-10-11..17 census (every conflicting main-merge on a merged PR, `merge-tree` exit 1, all-paths-match `GENERATED_RE`) is a no-model step and is absent from the E1 results; nothing here estimates the share. No p-value is claimed. |
| AG-H2 (latency) | **not scored** | census not run | Needs the same census (`L_sb` per generated-only merge, `L_tick` = 10 min + largest tick `Commands` total). Not run. |
| AG-H3 (safety where tool-written) | **✗** | 2/8 correct clears; exact one-sided 95% lower bound 0.046 | `tick` on tasks 1-4: task 1 2/2; tasks 2, 3, 4 0/2 each. `sendback` on the same 8 task-replicates: 8/8 correct clears. |
| AG-H4 (pattern too broad) | **✓** | 4/4 runs with R1 < 1 (threshold: at least 1) | Task 5 (docs/ci.md) R1 = 0 in both runs, all 9 PR lines dropped; task 6 R1 = 0.8165 in both, 20 PR lines dropped. |

The power floor for the replay claims was met (8 G runs and 4 T runs all finished with a scoreable tree).
AG-H1 and AG-H2 are **not** counted as nulls or as failures. They are unanswered.

### Consequences, per the registration's own table
- **AG-H3 ✗:** conflicts stay a worker item; the worker-brief line "Before the final report" is unchanged.
- **AG-H4 ✓:** any future tick file list must be narrower than `GENERATED_RE`; `^docs/` as a blanket is out. (Moot while
  AG-H3 stands, but it is the finding about the pattern.)
- The "AG-H1 ✗ means no tick step" and "AG-H2 ✗ with AG-H3 ✓" branches do not apply, because AG-H3 did not hold and AG-H1/H2 were not scored.

## Guards

- [x] Temporal ablation: n/a, no GitGalaxy scan was run; the arms are agent merges scored by git/pytest/gates.
- [x] Same model (`sonnet`), base commit, brief, $0.85 cap and full gates in both arms. Blind ids were used; scoring was by command or line count.
- [x] Multiple comparison: AG-H3 and AG-H4 are exact-count criteria with no p-value, so there was no correction to apply.
- [ ] Census power rule (at least 50 conflicting merges, at least 20 generated-only): not applicable, the census did not run.
- n/a: size-matched controls, rename tracking, defect-lift-over-LOC (this is not a defect-prediction test).

## Per-run table

R1 PR kept, R2 main kept, R3 PR tests, R4 gates, R5 agreement with the merged resolution (descriptive), R6 cleared.
Correct clear = R6 ∧ R1 = 1 ∧ R2 = 1 ∧ R3 = 1 ∧ R4 = 1. `cost_usd` and minutes are churn's run meta.
Command seconds from `notes.md` were not tabulated here (they only feed the AG-H2 latency estimate, which was not scored).

| blind | cond | task (issue) | stratum | rep | status | R1 | R2 | R3 | R4 | R5 | R6 | correct clear | cost_usd | min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| df2ebb | sendback | 1 (3799) | G | 0 | done | 1 | 1 | 1 | 1 | 1 | 1 | yes | 0.33 | 19 |
| cfb273 | sendback | 1 (3799) | G | 1 | done | 1 | 1 | 1 | 1 | 1 | 1 | yes | 0.41 | 21 |
| 4f07cc | tick | 1 (3799) | G | 0 | done | 1 | 1 | 1 | 1 | 1 | 1 | yes | 0.30 | 31 |
| a599ce | tick | 1 (3799) | G | 1 | done | 1 | 1 | 1 | 1 | 1 | 1 | yes | 0.27 | 20 |
| 69f2af | sendback | 2 (5401) | G | 0 | done | 1 | 1 | 1 | 1 | 0 | 1 | yes | 0.37 | 31 |
| d8e8bf | sendback | 2 (5401) | G | 1 | done | 1 | 1 | 1 | 1 | 0 | 1 | yes | 0.36 | 31 |
| 8b4c21 | tick | 2 (5401) | G | 0 | done | 1 | 1 | 0.9977 | 0 | 1 | 1 | **no** | 0.33 | 61 |
| 0fa710 | tick | 2 (5401) | G | 1 | denied | 1 | 1 | 0.9977 | 0 | 1 | 1 | **no** | 0.28 | 6 |
| 3112e0 | sendback | 3 (3798) | G | 0 | done | 1 | 1 | 1 | 1 | 0 | 1 | yes | 0.51 | 23 |
| 0d912b | sendback | 3 (3798) | G | 1 | done | 1 | 1 | 1 | 1 | 0 | 1 | yes | 0.36 | 20 |
| 9d034d | tick | 3 (3798) | G | 0 | done | 0.9484 | 1 | 1 | 1 | 0 | 1 | **no** | 0.28 | 26 |
| 3ffa00 | tick | 3 (3798) | G | 1 | done | 0.9484 | 1 | 1 | 1 | 0 | 1 | **no** | 0.29 | 26 |
| d38d8e | sendback | 4 (5278) | G | 0 | denied | 1 | 1 | 1 | 1 | 1 | 1 | yes | 0.30 | 21 |
| cba1e4 | sendback | 4 (5278) | G | 1 | done | 1 | 1 | 1 | 1 | 1 | 1 | yes | 0.39 | 27 |
| 211027 | tick | 4 (5278) | G | 0 | done | 0.9504 | 1 | 1 | 1 | 0 | 1 | **no** | 0.28 | 26 |
| edc9cd | tick | 4 (5278) | G | 1 | done | 0.9504 | 1 | 1 | 1 | 0 | 1 | **no** | 0.48 | 37 |
| 3ea7a0 | sendback | 5 (5543) | T | 0 | done | 1 | 1 | 1 | 1 | 0 | 1 | yes | 0.24 | 19 |
| afd4ec | sendback | 5 (5543) | T | 1 | done | 1 | 1 | 1 | 1 | 0 | 1 | yes | 0.29 | 27 |
| 5da32b | tick | 5 (5543) | T | 0 | done | 0 | 1 | 1 | 1 | 0 | 1 | **no** | 0.28 | 60 |
| 708b43 | tick | 5 (5543) | T | 1 | done | 0 | 1 | 1 | 1 | 0 | 1 | **no** | 0.26 | 31 |
| 853419 | sendback | 6 (3189) | T | 0 | done | 1 | 1 | 1 | 1 | 1 | 1 | yes | 0.43 | 45 |
| b5e645 | sendback | 6 (3189) | T | 1 | done | 1 | 1 | 1 | 1 | 1 | 1 | yes | 0.35 | 44 |
| 060b0e | tick | 6 (3189) | T | 0 | done | 0.8165 | 1 | 1 | 1 | 0 | 1 | **no** | 0.35 | 44 |
| a3a18b | tick | 6 (3189) | T | 1 | done | 0.8165 | 1 | 1 | 0 | 0 | 1 | **no** | 0.25 | 31 |

Two runs carry status `denied` (`0fa710` tick, `d38d8e` sendback). In both the merge was committed and scored on its tree;
neither escalated.

## Real-use cost per task (as registered)

Policy cost: send-back = the `sendback` runs' `cost_usd`; tick = $0 for a correct clear, else the task's mean `sendback`
cost (the conflict goes back to a worker). The `tick` arm's own spend is emulation overhead, not policy cost.

| task | stratum | sendback policy (2 runs) | tick policy (2 runs) | tick correct clears | tick arm's own spend (overhead) |
|---|---|---|---|---|---|
| 1 (3799) | G | 0.74 | 0.00 | 2/2 | 0.57 |
| 2 (5401) | G | 0.73 | 0.73 | 0/2 | 0.61 |
| 3 (3798) | G | 0.87 | 0.87 | 0/2 | 0.57 |
| 4 (5278) | G | 0.69 | 0.69 | 0/2 | 0.76 |
| 5 (5543) | T | 0.53 | 0.53 | 0/2 | 0.54 |
| 6 (3189) | T | 0.78 | 0.78 | 0/2 | 0.60 |
| **total** | | **4.34** | **3.60** | 2/12 | 3.65 |

This is not a claim (cost was not registered as a test). The $0.74 difference comes entirely from task 1. It also
treats a bad clear as costing only a re-do, and a bad clear that is not caught would cost more. The `tick` runs never
escalated (R6 = 1 on all 12), including on the two trap tasks, so the gate's safety here would rest on a post-merge check.

## Reading

- **What happened.** The mechanical "take main's, regenerate only if a tool names the path" procedure reproduced the
  merged resolution only where the regenerator rebuilds the file from the tree (task 1, a chart). Where the conflicted
  file is a ledger or table holding entries from both sides (tasks 3, 4) it took main's copy and dropped the PR's entry
  (R1 0.948 and 0.950, in all four runs). On task 2 R1/R2 were 1 but the tick left `docs_read_by_tests.txt` stale, so one
  PR test and the gates failed (both runs, R4 = 0). The send-back worker kept the PR's change and passed in all 12 of its runs.
- **Stratum G was not a safe set.** The registration expected the tick to be safe wherever a tool writes the path. It was safe on 1 of 4 tasks.
- **Latency per run** was not better: `tick` runs took 399 min in total against 328 for `sendback`, but that is a model
  emulating a script and running the full gates (a 15-minute suite), so it is not the AG-H2 quantity. Do not read it as evidence on AG-H2.

## What this does NOT establish

- Nothing about AG-H1 (how common generated-only conflicts are) or AG-H2 (latency): the census did not run. The design's
  own window figure (34 of 122 conflicting merges, 28%, 2026-10-18..24) is seen data, descriptive only.
- That no mechanical merge could work. This tested one fixed procedure, emulated by a model. A script that regenerated
  every tool-written path, or merged ledger entries by key, was not tested.
- Anything about hand-conflict PRs (not replayed; the tick escalates on them by rule).
- A rate with precision: 2/8 has a wide interval (exact 95% lower bound 0.046), and 6 tasks cannot cover every generated-file family.
- Real send-back quality or cost. A fresh `sendback` worker lacks the resumed session's context, so it is a lower bound on a
  real send-back's quality and an upper bound on its cost. On task 2, `sendback` regenerated the classifier doc after the
  gate run, and R4 was scored 1 on that basis; tasks 1 and 6 gate failures were attributed to `pin_requirements`, red on `M`,
  without being itemised. These are scorer judgments, and they only favour `sendback`, whose margin is already 8/8 vs 2/8.

## Follow-ups registered (for unseen data only)

None. If a regenerate-everything or key-wise ledger-merge tick is proposed, it needs a new registration on tasks this
experiment has not used. The census (AG-H1, AG-H2) remains registered and unscored; running it needs no model.
