# sensor-overhaul

Long-term workspace (branch `sensor-overhaul`, built on `turn/forecast`) for redesigning GitGalaxy's file-level gauges into **non-redundant sensors that give actionable information**. Start with [GUIDE.md](GUIDE.md): the goal, the evidence, what to keep, change or retire, the design rules and the acceptance checklist.

Research and prototypes live here; changes to the engine itself go to GitGalaxy as issues and pull requests, one sensor at a time.

## Sensor board
| Sensor | Replaces | Status | Design | Notes |
|---|---|---|---|---|
| Debt ledger | `risk_tech_debt` | v2 trial on 9 C projects (fossils repaid 6.9% vs 22.0%; file activity and owner are the ranking keys); **worklist v2 has stable IDs, triage and an empirical effort band**; counts validated (+0.84 to +0.97) | [sensors/tech_debt.md](sensors/tech_debt.md) | needs marker positions, age and author in the engine |
| Activity | `risk_churn`, `risk_stability` | design written, horizons tested (7 repos), **mock-up back-tested on curl, libxml2, libgit2** | [sensors/activity.md](sensors/activity.md) | engine: whole-history walk, persisted horizons, as-of by default; docs text to correct |
| Reach | `risk_api_exposure` | design written; validity tested (+0.91 function level, fails for headers); **migration scope report prototyped** on libgit2 | [sensors/reach.md](sensors/reach.md) | engine: external callee nodes, include counts |
| Mutation | `risk_state_flux`, `risk_safety_score` | merge decided | GUIDE section 3 | one family density; rename |
| Complexity drill-down | `risk_cognitive_load` | design next | GUIDE section 3 | list worst functions |
| Concurrency filter | `risk_concurrency` | design next | GUIDE section 3 | unguarded constructs, listed |
| Unreferenced functions | part of `risk_tech_debt`, `risk_dead_code` | design next | GUIDE section 3 | call graph; needs "not measured" for unresolved |
| Documented public functions | `risk_documentation` | design next | GUIDE section 3 | engine has `is_public`, `is_documented` |
| Secrets findings | `risk_secrets_risk` | decided: list, not score | GUIDE section 3 | |
| Mechanical share, settledness, role tag | new | idea, evidence in | GUIDE section 3 | from sweep, hazard and role-cluster studies |
| Comment sensors (commented-out code, header coverage, neglect, danger language) | new | evidence in (precision 93-95%) | [sensors/tech_debt.md](sensors/tech_debt.md) section 4 | |

## How to add a sensor
Copy [sensors/_template.md](sensors/_template.md), fill it in, run the acceptance checklist (GUIDE section 5) with the scripts in `tools/turn/surface_area/` and `tools/sensor/`, record the result on the board above.

## Tools
`tools/sensor/` (prototypes: `debt_ledger.py`, `debt_validity.py`, `debt_trial.py`, `debt_trial_report.py`, `debt_effort.py`, `debt_worklist.py`, `reach_validity.py`, `migration_scope.py`, `activity_horizons.py`, `activity_mockup.py`); `tools/turn/surface_area/` (descriptive and outcome tests, history-aware scans, ripple test); `tools/turn/` (earlier studies). Paths are hard-coded to the discovery machine.

## Conventions
* Exploratory until a sensor passes the checklist; no outcome claims on any sensor.
* Record the engine version a result came from (the installed `galaxyscope` loads a stale copy; see GUIDE section 2.6).
