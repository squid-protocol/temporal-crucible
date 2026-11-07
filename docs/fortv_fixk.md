# FORT-V and FIXK (SCORED)

- touches: already-guarded functions where the fix adds a new guard: 11,119 — latent 436, regression 373, other-fix 9682, extrinsic 628

| claim | result | verdict |
|---|---|---|
| **FORTV-H1** new guard checks an already-guarded variable: latent vs other-fix | P(extends): latent 84.2%, other-fix 80.3%; MH RR **1.04** [0.97, 1.12] | **inconclusive** |
- regression (descriptive): P(extends) 83.1%; MH RR vs other-fix 1.02

- FIXK commits with kept C/C++ files: 23,110 — latent 613, regression 644, other-fix 19,984, extrinsic 1,869

| claim | result | verdict |
|---|---|---|
| **FIXK-H1** CVE signature beyond known defensive rules | 4 signature rules; beyond ['branch', 'cleanup', 'panics_and_aborts', 'safety']: [('pointers', 'gain'), ('reflection_metaprogramming', 'gain'), ('structural_boundaries', 'gain')] | **SUPPORTED** |
| **FIXK-H2** regression signature exists | [('args', 'gain'), ('branch', 'gain'), ('calls_out', 'loss'), ('encapsulation', 'gain'), ('events', 'gain'), ('explicit_casts', 'gain'), ('explicit_casts', 'loss'), ('func_start', 'gain'), ('globals', 'gain'), ('immutability_locks', 'gain'), ('import', 'gain'), ('macros', 'loss'), ('memory_alloc', 'gain'), ('pointers', 'gain'), ('pointers', 'loss'), ('reflection_metaprogramming', 'gain'), ('safety', 'gain'), ('safety_bypasses', 'loss'), ('state_mutation', 'gain'), ('state_mutation', 'loss'), ('structural_boundaries', 'gain'), ('structural_boundaries', 'loss'), ('sync_locks', 'gain')] | **SUPPORTED** |
| **FIXK-H3** CVE and regression signatures differ | Jaccard 0.17 | **SUPPORTED** |

### latent vs other-fix (signature rules first; then the rest sorted by RR)

| rule | change | class rate | other-fix rate | MH RR | BH q |
|---|---|---:|---:|---:|---:|
| reflection_metaprogramming | gain | 15.7% | 8.8% | 1.65 | 4.6e-07 |
| pointers | gain | 49.9% | 33.5% | 1.42 | 4e-14 |
| branch | gain | 62.3% | 42.4% | 1.40 | 8.4e-19 |
| structural_boundaries | gain | 36.1% | 27.0% | 1.28 | 3.5e-05 |
| dead_code | loss | 0.0% | 0.6% | 0.00 | 0.24 |
| scientific | loss | 0.0% | 0.2% | 0.00 | 0.47 |
| test | gain | 0.0% | 0.1% | 0.00 | 0.76 |
| thread_sleeps | gain | 0.0% | 0.1% | 0.00 | 0.81 |
| time_date_logic | gain | 0.0% | 0.4% | 0.00 | 0.47 |
| time_date_logic | loss | 0.0% | 0.1% | 0.00 | 0.72 |
| high_risk_execution | gain | 0.8% | 0.3% | 3.06 | 0.098 |
| generics | loss | 0.2% | 0.1% | 2.53 | 0.73 |
| ipc_rpc_bridges | gain | 0.5% | 1.1% | 0.40 | 0.36 |
| io | loss | 0.5% | 0.2% | 2.40 | 0.47 |
| fragile_debt | loss | 0.3% | 0.6% | 0.51 | 0.73 |
| planned_debt | gain | 0.7% | 1.2% | 0.51 | 0.47 |
| scientific | gain | 0.8% | 0.4% | 1.97 | 0.45 |
| doc | gain | 0.5% | 0.9% | 0.52 | 0.61 |
| cleanup | loss | 1.6% | 0.8% | 1.88 | 0.29 |
| memory_alloc | loss | 1.8% | 0.9% | 1.82 | 0.29 |
| listeners | loss | 0.7% | 0.3% | 1.77 | 0.65 |
| panics_and_aborts | gain | 3.8% | 1.9% | 1.75 | 0.053 |
| debug_prints | loss | 0.5% | 0.6% | 0.63 | 0.73 |
| bitwise_ops | gain | 4.9% | 3.1% | 1.53 | 0.13 |

### regression vs other-fix (signature rules first; then the rest sorted by RR)

| rule | change | class rate | other-fix rate | MH RR | BH q |
|---|---|---:|---:|---:|---:|
| sync_locks | gain | 1.2% | 0.0% | 12.94 | 6.1e-07 |
| safety_bypasses | loss | 0.3% | 1.5% | 0.16 | 0.0089 |
| explicit_casts | loss | 1.2% | 2.7% | 0.33 | 0.0027 |
| events | gain | 1.6% | 0.4% | 3.00 | 0.0066 |
| macros | loss | 1.7% | 3.8% | 0.37 | 0.0016 |
| globals | gain | 23.8% | 4.3% | 2.52 | 8.5e-34 |
| func_start | gain | 39.9% | 10.9% | 1.97 | 3.9e-41 |
| calls_out | loss | 6.2% | 10.4% | 0.52 | 3.5e-05 |
| state_mutation | loss | 4.7% | 7.2% | 0.53 | 0.00071 |
| memory_alloc | gain | 6.7% | 2.2% | 1.85 | 0.00071 |
| structural_boundaries | loss | 5.0% | 7.0% | 0.57 | 0.0024 |
| encapsulation | gain | 16.0% | 7.5% | 1.72 | 8.4e-10 |
| reflection_metaprogramming | gain | 17.4% | 8.8% | 1.66 | 5.4e-09 |
| immutability_locks | gain | 27.3% | 9.8% | 1.58 | 1.1e-11 |
| pointers | loss | 7.0% | 8.7% | 0.64 | 0.0043 |
| safety | gain | 14.3% | 6.6% | 1.52 | 6.8e-05 |
| args | gain | 43.3% | 19.9% | 1.49 | 7.5e-17 |
| explicit_casts | gain | 14.0% | 6.1% | 1.46 | 0.0012 |
| state_mutation | gain | 52.0% | 27.6% | 1.42 | 6.8e-16 |
| import | gain | 13.2% | 6.4% | 1.41 | 0.0029 |
| pointers | gain | 59.9% | 33.5% | 1.39 | 8.2e-18 |
| structural_boundaries | gain | 50.9% | 27.0% | 1.37 | 2.5e-13 |
| branch | gain | 64.1% | 42.4% | 1.28 | 2.1e-12 |
| doc | loss | 0.0% | 0.3% | 0.00 | 0.24 |

### extrinsic vs other-fix (signature rules first; then the rest sorted by RR)

| rule | change | class rate | other-fix rate | MH RR | BH q |
|---|---|---:|---:|---:|---:|
| inline_asm | gain | 0.3% | 0.0% | 33.36 | 6.8e-13 |
| thread_sleeps | gain | 0.3% | 0.1% | 6.27 | 6.8e-05 |
| import | loss | 2.2% | 0.8% | 3.03 | 1.7e-09 |
| io | loss | 0.9% | 0.2% | 3.00 | 0.0031 |
| events | gain | 0.8% | 0.4% | 2.58 | 0.0025 |
| macros | gain | 38.3% | 14.3% | 2.57 | 9.1e-148 |
| io | gain | 2.4% | 0.6% | 2.43 | 1.8e-06 |
| scientific | gain | 1.4% | 0.4% | 2.14 | 0.0027 |
| import | gain | 14.3% | 6.4% | 2.05 | 1.9e-31 |
| fragile_debt | gain | 1.8% | 0.8% | 2.05 | 0.0013 |
| safety_bypasses | gain | 4.7% | 3.0% | 1.79 | 1.8e-06 |
| args | gain | 33.0% | 19.9% | 1.63 | 9.4e-44 |
| bitwise_ops | gain | 5.5% | 3.1% | 1.62 | 4.2e-05 |
| api | gain | 8.5% | 5.5% | 1.52 | 3.6e-07 |
| macros | loss | 5.6% | 3.8% | 1.46 | 0.0012 |
| explicit_casts | gain | 9.1% | 6.1% | 1.45 | 2e-05 |
| structural_boundaries | loss | 4.9% | 7.0% | 0.72 | 0.0046 |
| state_mutation | loss | 5.1% | 7.2% | 0.72 | 0.0053 |
| calls_out | loss | 7.7% | 10.4% | 0.76 | 0.0031 |
| pointers | gain | 27.1% | 33.5% | 0.76 | 2.9e-13 |
| listeners | loss | 0.1% | 0.3% | 0.20 | 0.17 |
| sync_locks | gain | 0.1% | 0.0% | 4.75 | 0.096 |
| concurrency | gain | 0.1% | 0.0% | 4.05 | 0.15 |
| generics | loss | 0.1% | 0.1% | 3.25 | 0.17 |

Runtime 158s · seed 2982.
