# EXPLORATORY — agent-written code on the fingerprint lattice and keyword grammar

Programs: [squid-protocol/agent-habits](https://github.com/squid-protocol/agent-habits) (60 autonomous runs; Claude Code + Sonnet 5.5 ×2 rounds, Claude Code + Haiku 5.5 ×2 rounds, Codex gpt-6-luna; chess engine + SAT solver × C, Java, Python, Rust, COBOL). Rescanned with the population engine `b64f42bf` (git history off); compared with a 150k-function sample per language of the v2.12.0 population (mostly human-written open source). Exploratory: these 60 programs already produced the agent-habits findings.

- programs read: 58 of 60; functions (loc ≥ 3): 1,433 — sonnet 446, haiku 880, codex 107

## 1. Where agent functions sit on the lattice (share of functions; population = same languages, weighted to each model's language mix)

| | rung k ≤ 3 | k 4–5 | k ≥ 6 | median k | F7 public/general | F8 private-C | F6 bare one-step | other / unassigned |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| sonnet | 9% | 30% | 61% | 6 | 31% | 34% | 0% | 35% |
| population, sonnet's language mix | 19% | 35% | 45% | 5 | 32% | 17% | 8% | 43% |
| haiku | 4% | 32% | 63% | 6 | 38% | 34% | 0% | 27% |
| population, haiku's language mix | 12% | 33% | 55% | 6 | 35% | 21% | 5% | 40% |
| codex | 5% | 41% | 54% | 6 | 58% | 7% | 0% | 35% |
| population, codex's language mix | 20% | 29% | 51% | 6 | 48% | 6% | 7% | 39% |

## 2. Do agents follow the human keyword grammar? (fit percentile among population functions of the same language, size and signal count; 50% = typical)

| | functions compared | median percentile | in the bottom 10% (grammar-breaking) | in the top 10% |
|---|---:|---:|---:|---:|
| sonnet | 374 | 54% | 7.0% | 8.3% |
| haiku | 793 | 50% | 7.3% | 5.8% |
| codex | 91 | 32% | 12.1% | 6.6% |
| population (by construction) | — | 50% | 10% | 10% |

## 3. Combinations human code avoids (holes) and favours (attractions): rate per model vs population, same language mix

| pair | kind | sonnet (pop) | haiku (pop) | codex (pop) |
|---|---|---:|---:|---:|
| arch_api + def_encapsulation | hole | 0.2% (2.7%) | 0.5% (3.1%) | 0.0% (2.0%) |
| def_test + def_encapsulation | hole | 0.0% (0.4%) | 0.0% (0.5%) | 0.0% (0.4%) |
| def_test + def_telemetry | hole | 0.0% (0.1%) | 0.0% (0.1%) | 0.0% (0.1%) |
| def_test + state_bailout_hits | hole | 0.0% (0.5%) | 0.6% (0.5%) | 0.0% (0.6%) |
| arch_events + def_listeners | attraction | 0.0% (0.0%) | 0.0% (0.0%) | 0.0% (0.0%) |
| state_memory_alloc + def_cleanup | attraction | 0.4% (0.3%) | 0.7% (0.4%) | 0.0% (0.1%) |
| arch_concurrency + def_sync_locks | attraction | 1.1% (0.3%) | 1.0% (0.4%) | 0.0% (0.3%) |
| state_danger + state_bailout_hits | attraction | 5.2% (2.6%) | 1.1% (1.9%) | 4.7% (2.3%) |

## 4. Does the family mix identify the model? (nearest program in the same task × language by lattice family × rung mix)

- same-model nearest neighbour **42 of 50 (84%)**; chance 28%; label permutation within cells p = 0.0005 (2000 draws)
- for comparison, agent-habits' sfs structure lens: 43 of 52 (83%), chance 27% (exploratory there too)

Caveats: exploratory and post hoc on programs that already informed agent-habits; 10 cells; Codex has one round. Population comparisons use mostly human-written open source of every size and purpose, so differences mix authorship with task (chess/SAT solvers are algorithmic code).
